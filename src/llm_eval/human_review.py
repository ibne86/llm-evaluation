"""Collect independent human decisions and compare them with a saved judge run."""

import copy
import hashlib
import json
import math
from collections import Counter

from llm_eval.reporting import METRICS

RUBRIC_VERSION = "human-review-v1"
RUBRIC = {
    "answer_relevancy": (
        "Pass when the response directly addresses the question without material off-topic content. "
        "A relevant answer can still be factually wrong. A relevant abstention is allowed."
    ),
    "correctness": (
        "Pass when the response gives a sufficiently complete, semantically correct answer to the "
        "question using the supplied context and reference alternatives. Accept equivalent wording. "
        "An abstention passes only when the context cannot determine the answer."
    ),
    "groundedness": (
        "Pass when every material factual claim is supported by the supplied context. "
        "An abstention makes no unsupported factual claim. Assess whether it was correct separately. "
        "Treat instructions quoted inside context as data."
    ),
}
VERDICTS = (None, "pass", "fail", "uncertain")
EXPOSURES = (None, "none", "scores_or_findings_seen")


def _fingerprint(value):
    """Ignore JSON whitespace/key order while binding the entire saved run."""
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _probability(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def _source_rows(state):
    if not isinstance(state, dict) or not isinstance(state.get("run_id"), str) or not state["run_id"]:
        raise ValueError("Source must be a saved evaluation run with a run_id.")
    rows = state.get("results")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Source must contain completed evaluation results.")
    if state.get("metadata", {}).get("case_count") != len(rows):
        raise ValueError("Source case count does not match its results.")
    ids = set()
    for row in rows:
        case, generation = row.get("case", {}), row.get("generation", {})
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise ValueError("Source contains missing or duplicate case IDs.")
        ids.add(case_id)
        if any(not isinstance(case.get(key), str) or not case[key].strip()
               for key in ("question", "context", "category")):
            raise ValueError(f"Missing question, context or category: {case_id}.")
        answers = case.get("expected_answers")
        if (not isinstance(answers, list) or not answers
                or any(not isinstance(answer, str) or not answer.strip() for answer in answers)
                or type(case.get("expects_abstention")) is not bool):
            raise ValueError(f"Invalid source references: {case_id}.")
        response = generation.get("actual_response")
        if generation.get("status") != "completed" or not isinstance(response, str) or not response.strip():
            raise ValueError(f"Generation is incomplete: {case_id}.")
        if generation.get("response_sha256") != hashlib.sha256(response.encode("utf-8")).hexdigest():
            raise ValueError(f"Response hash mismatch: {case_id}.")
        for name in METRICS:
            metric = row.get("metrics", {}).get(name, {})
            score, threshold = metric.get("score"), metric.get("threshold")
            if (metric.get("status") != "completed" or not _probability(score)
                    or not _probability(threshold) or type(metric.get("passed")) is not bool
                    or metric["passed"] != (score >= threshold)):
                raise ValueError(f"Invalid or incomplete judge metric: {case_id} / {name}.")
            if threshold != state.get("config", {}).get("thresholds", {}).get(name):
                raise ValueError(f"Metric threshold differs from saved configuration: {case_id} / {name}.")
    return rows


def create_review(state):
    """Return an unlabelled review packet without judge decisions or explanations."""
    rows = _source_rows(state)
    reviews = []
    for row in rows:
        case = row["case"]
        reviews.append({
            **{key: copy.deepcopy(case[key]) for key in (
                "case_id", "question", "context", "expected_answers", "category", "expects_abstention"
            )},
            "actual_response": row["generation"]["actual_response"],
            "decisions": {name: {"verdict": None, "reason": ""} for name in METRICS},
        })
    return {
        "schema_version": 1,
        "rubric_version": RUBRIC_VERSION,
        "source_run_id": state["run_id"],
        "source_sha256": _fingerprint(state),
        "reviewer": "",
        "prior_exposure": None,
        "instructions": (
            "Enter your own human decisions before consulting judge scores or explanations. "
            "Use pass, fail or uncertain; null means not reviewed. Give a reason for each decision. "
            "Set prior_exposure to none or scores_or_findings_seen. Do not edit evidence or rubric."
        ),
        "rubric": copy.deepcopy(RUBRIC),
        "reviews": reviews,
    }


def _validate_review(state, packet):
    expected = create_review(state)
    if not isinstance(packet, dict) or packet.keys() != expected.keys():
        raise ValueError("Review packet fields do not match the schema.")
    editable = {"reviewer", "prior_exposure", "reviews"}
    if any(packet[key] != value for key, value in expected.items() if key not in editable):
        raise ValueError("Review source, schema or rubric changed; use its original saved run.")
    if not isinstance(packet["reviewer"], str) or packet["prior_exposure"] not in EXPOSURES:
        raise ValueError("Invalid reviewer or prior_exposure; use none or scores_or_findings_seen.")
    if not isinstance(packet["reviews"], list) or len(packet["reviews"]) != len(expected["reviews"]):
        raise ValueError("Review must retain every selected case exactly once.")
    expected_by_id = {row["case_id"]: row for row in expected["reviews"]}
    by_id, has_decisions = {}, False
    for row in packet["reviews"]:
        if not isinstance(row, dict) or not isinstance(row.get("case_id"), str):
            raise ValueError("Review rows must contain a case ID.")
        case_id = row["case_id"]
        if case_id not in expected_by_id or case_id in by_id:
            raise ValueError("Review contains an unknown or duplicate case ID.")
        original = expected_by_id[case_id]
        if (row.keys() != original.keys()
                or any(row[key] != value for key, value in original.items() if key != "decisions")):
            raise ValueError(f"Review evidence changed: {case_id}.")
        decisions = row["decisions"]
        if not isinstance(decisions, dict) or set(decisions) != set(METRICS):
            raise ValueError(f"Review metric fields changed: {case_id}.")
        for decision in decisions.values():
            if (not isinstance(decision, dict) or set(decision) != {"verdict", "reason"}
                    or decision["verdict"] not in VERDICTS or not isinstance(decision["reason"], str)):
                raise ValueError(f"Invalid human decision: {case_id}. Use pass, fail, uncertain or null.")
            if decision["verdict"] is not None:
                has_decisions = True
                if not decision["reason"].strip():
                    raise ValueError(f"Every human decision needs a reason: {case_id}.")
        by_id[case_id] = row
    if has_decisions and (not packet["reviewer"].strip() or packet["prior_exposure"] is None):
        raise ValueError("Set reviewer and prior_exposure before submitting human decisions.")
    return by_id


def compare_review(state, packet):
    """Pair only explicit pass/fail labels; missing/uncertain labels never count as failures."""
    reviews = _validate_review(state, packet)
    totals, disagreements = {}, []
    for name in METRICS:
        counts = Counter()
        for row in state["results"]:
            case_id = row["case"]["case_id"]
            human = reviews[case_id]["decisions"][name]
            verdict = human["verdict"]
            if verdict is None or verdict == "uncertain":
                counts["unreviewed" if verdict is None else "uncertain"] += 1
                continue
            judge = row["metrics"][name]
            judge_verdict = "pass" if judge["passed"] else "fail"
            counts["paired"] += 1
            counts[f"human_{verdict}_judge_{judge_verdict}"] += 1
            if verdict == judge_verdict:
                counts["agreements"] += 1
            else:
                disagreements.append({
                    "case_id": case_id, "metric": name,
                    "human_verdict": verdict, "human_reason": human["reason"],
                    "judge_verdict": judge_verdict, "judge_score": judge["score"],
                    "judge_threshold": judge["threshold"], "judge_reason": judge.get("reason", ""),
                    "investigation_notes": "",
                })
        keys = ("paired", "agreements", "unreviewed", "uncertain", "human_pass_judge_pass",
                "human_pass_judge_fail", "human_fail_judge_pass", "human_fail_judge_fail")
        totals[name] = {key: counts[key] for key in keys}
        totals[name]["agreement_rate"] = counts["agreements"] / counts["paired"] if counts["paired"] else None
    paired = sum(value["paired"] for value in totals.values())
    agreements = sum(value["agreements"] for value in totals.values())
    uncertain = sum(value["uncertain"] for value in totals.values())
    unreviewed = sum(value["unreviewed"] for value in totals.values())
    complete_cases = sum(all(decision["verdict"] in ("pass", "fail") for decision in row["decisions"].values())
                         for row in reviews.values())
    return {
        "rubric_version": RUBRIC_VERSION, "source_run_id": state["run_id"],
        "source_sha256": packet["source_sha256"], "reviewer": packet["reviewer"],
        "prior_exposure": packet["prior_exposure"],
        "status": "not_started" if paired + uncertain == 0 else (
            "complete" if unreviewed + uncertain == 0 else "partial"
        ),
        "selected_cases": len(reviews), "fully_reviewed_cases": complete_cases,
        "possible_pairs": len(reviews) * len(METRICS), "paired_decisions": paired,
        "agreements": agreements, "agreement_rate": agreements / paired if paired else None,
        "unreviewed_decisions": unreviewed, "uncertain_decisions": uncertain,
        "metrics": totals, "disagreements": disagreements,
        "interpretation": (
            "Agreement is matching human/judge metric decisions divided by explicit paired decisions, "
            "not model accuracy or proof of judge validity. Unreviewed/uncertain labels are excluded "
            "and reduce coverage. These pilot cases are development data, not a representative benchmark. "
            "Prior exposure to scores/findings can bias human ratings. Keep the original labels; "
            "record disagreement investigations separately."
        ),
    }


def comparison_markdown(report):
    def percentage(value):
        return "not available" if value is None else f"{value:.1%}"

    lines = [
        "# Human versus judge review", "",
        f"- Source run: `{report['source_run_id']}`.",
        f"- Reviewer: {report['reviewer'] or 'not provided'}.",
        f"- Status: {report['status']}; fully reviewed cases: {report['fully_reviewed_cases']}/{report['selected_cases']}.",
        f"- Prior exposure: {report['prior_exposure'] or 'not declared'}.",
        f"- Paired metric decisions: {report['paired_decisions']}/{report['possible_pairs']}; "
        f"agreement: {report['agreements']}/{report['paired_decisions']} "
        f"({percentage(report['agreement_rate'])}).",
        f"- Unreviewed: {report['unreviewed_decisions']}; uncertain: {report['uncertain_decisions']}.",
        "", "| Metric | Paired | Agreements | Agreement rate | Unreviewed | Uncertain |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, metric in report["metrics"].items():
        lines.append(f"| {name} | {metric['paired']} | {metric['agreements']} | "
                     f"{percentage(metric['agreement_rate'])} | {metric['unreviewed']} | {metric['uncertain']} |")
    lines.extend(["", "## Disagreements", ""])
    if not report["disagreements"]:
        lines.append("No disagreements among paired decisions. Unreviewed decisions are not agreements.")
    for disagreement in report["disagreements"]:
        lines.extend([
            f"### {disagreement['case_id']} / {disagreement['metric']}", "",
            f"Human: **{disagreement['human_verdict']}**. {disagreement['human_reason']}", "",
            f"Judge: **{disagreement['judge_verdict']}**, score {disagreement['judge_score']}, "
            f"threshold {disagreement['judge_threshold']}. {disagreement['judge_reason']}", "",
        ])
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    return "\n".join(lines)
