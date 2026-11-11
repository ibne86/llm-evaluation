"""Compare recorded human decisions with saved local judge evidence."""

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
REASON_POLICIES = ("required", "optional")


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


def create_review(state, *, reason_policy="required"):
    """Return an unlabelled review packet without judge decisions or explanations."""
    if reason_policy not in REASON_POLICIES:
        raise ValueError("reason_policy must be required or optional.")
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
    packet = {
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
    if reason_policy == "optional":
        packet["reason_policy"] = "optional"
        packet["instructions"] = (
            "Enter your own human decisions and declare actual prior exposure. "
            "Use pass, fail or uncertain; null means not reviewed. Written reasons are optional; "
            "leave reason empty when no explanation was collected. Do not invent explanations. "
            "Set prior_exposure to none or scores_or_findings_seen. Do not edit evidence or rubric."
        )
    return packet


def _validate_review(state, packet):
    if not isinstance(packet, dict):
        raise ValueError("Review packet fields do not match the schema.")
    policy = packet.get("reason_policy", "required")
    expected = create_review(state, reason_policy=policy)
    allowed = expected.keys() | {"reviewer_type", "review_status", "reason_policy"}
    if not expected.keys() <= packet.keys() or packet.keys() - allowed:
        raise ValueError("Review packet fields do not match the schema.")
    editable = {"reviewer", "prior_exposure", "reviews"}
    if any(packet[key] != value for key, value in expected.items() if key not in editable):
        raise ValueError("Review source, schema or rubric changed; use its original saved run.")
    if not isinstance(packet["reviewer"], str) or packet["prior_exposure"] not in EXPOSURES:
        raise ValueError("Invalid reviewer or prior_exposure; use none or scores_or_findings_seen.")
    if packet.get("reviewer_type", "human") != "human":
        raise ValueError("Human review reviewer_type must be human.")
    by_id, has_decisions = _validate_rows(
        state, packet["reviews"], require_reasons=policy == "required"
    )
    if has_decisions and (not packet["reviewer"].strip() or packet["prior_exposure"] is None):
        raise ValueError("Set reviewer and prior_exposure before submitting human decisions.")
    if "review_status" in packet and packet["review_status"] != _review_status(by_id):
        raise ValueError("Declared review_status differs from the recorded decisions.")
    return by_id


def _review_status(reviews):
    verdicts = [decision["verdict"] for row in reviews.values() for decision in row["decisions"].values()]
    if all(verdict is None for verdict in verdicts):
        return "not_started"
    return "complete" if all(verdict in ("pass", "fail") for verdict in verdicts) else "partial"


def _validate_rows(state, rows, *, require_reasons):
    expected_rows = create_review(state)["reviews"]
    if not isinstance(rows, list) or len(rows) != len(expected_rows):
        raise ValueError("Review must retain every selected case exactly once.")
    expected_by_id = {row["case_id"]: row for row in expected_rows}
    by_id, has_decisions = {}, False
    for row in rows:
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
                if require_reasons and not decision["reason"].strip():
                    raise ValueError(f"Every human decision needs a reason: {case_id}.")
        by_id[case_id] = row
    return by_id, has_decisions


def _validate_assistant_review(state, packet):
    if not isinstance(packet, dict) or packet.get("review_type") != "assistant_generated":
        raise ValueError("Secondary reference must be an assistant_generated review.")
    expected = create_review(state)
    for key in ("source_run_id", "source_sha256", "rubric_version", "rubric"):
        if packet.get(key) != expected[key]:
            raise ValueError("Assistant reference source or rubric differs from the human review.")
    if not isinstance(packet.get("reviewer"), str) or not packet["reviewer"].strip():
        raise ValueError("Assistant reference must identify its AI reviewer.")
    if packet.get("reviewer_type", "ai_assistant") not in ("ai", "ai_assistant"):
        raise ValueError("Secondary reference reviewer_type must identify AI authorship.")
    return _validate_rows(state, packet.get("reviews"), require_reasons=True)[0]


def _assistant_agreement(reviews, assistant):
    metrics = {}
    for name in METRICS:
        paired = matching = 0
        for case_id, row in reviews.items():
            human = row["decisions"][name]["verdict"]
            other = assistant[case_id]["decisions"][name]["verdict"]
            if human in ("pass", "fail") and other in ("pass", "fail"):
                paired += 1
                matching += human == other
        metrics[name] = {
            "paired_decisions": paired, "matching_decisions": matching,
            "agreement_rate": matching / paired if paired else None,
            "excluded_decisions": len(reviews) - paired,
        }
    paired = sum(metric["paired_decisions"] for metric in metrics.values())
    matching = sum(metric["matching_decisions"] for metric in metrics.values())
    return {
        "paired_decisions": paired, "matching_decisions": matching,
        "agreement_rate": matching / paired if paired else None,
        "excluded_decisions": len(reviews) * len(METRICS) - paired,
        "metrics": metrics,
    }


def compare_review(state, packet, *, assistant_review=None):
    """Pair only explicit pass/fail labels; missing/uncertain labels never count as failures."""
    reviews = _validate_review(state, packet)
    assistant = _validate_assistant_review(state, assistant_review) if assistant_review is not None else None
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
                    **{key: copy.deepcopy(row["case"][key]) for key in (
                        "question", "context", "expected_answers"
                    )},
                    "actual_response": row["generation"]["actual_response"],
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
    rated = [decision for row in reviews.values() for decision in row["decisions"].values()
             if decision["verdict"] is not None]
    written_reasons = sum(bool(decision["reason"].strip()) for decision in rated)
    comparisons = []
    for number, row in enumerate(state["results"], 1):
        case_id = row["case"]["case_id"]
        for name in METRICS:
            human = reviews[case_id]["decisions"][name]
            judge = row["metrics"][name]
            judge_verdict = "pass" if judge["passed"] else "fail"
            comparison = {
                "case_number": number, "case_id": case_id, "question": row["case"]["question"],
                "metric": name, "human_verdict": human["verdict"], "human_reason": human["reason"],
                "judge_verdict": judge_verdict, "judge_score": judge["score"],
                "judge_threshold": judge["threshold"], "judge_reason": judge.get("reason", ""),
                "human_matches_judge": (
                    human["verdict"] == judge_verdict if human["verdict"] in ("pass", "fail") else None
                ),
            }
            if assistant is not None:
                other = assistant[case_id]["decisions"][name]
                comparison.update({
                    "assistant_verdict": other["verdict"], "assistant_reason": other["reason"],
                    "human_matches_assistant": (
                        human["verdict"] == other["verdict"]
                        if human["verdict"] in ("pass", "fail") and other["verdict"] in ("pass", "fail")
                        else None
                    ),
                })
            comparisons.append(comparison)
    report = {
        "schema_version": 1, "evaluation_type": "human_vs_local_judge",
        "rubric_version": RUBRIC_VERSION, "source_run_id": state["run_id"],
        "source_sha256": packet["source_sha256"], "reviewer": packet["reviewer"],
        "human_review_sha256": _fingerprint(packet), "reviewer_type": "human",
        "reason_policy": packet.get("reason_policy", "required"),
        "reason_coverage": {
            "rated_decisions": len(rated), "written_reasons": written_reasons,
            "missing_written_reasons": len(rated) - written_reasons,
        },
        "prior_exposure": packet["prior_exposure"],
        "status": "not_started" if paired + uncertain == 0 else (
            "complete" if unreviewed + uncertain == 0 else "partial"
        ),
        "selected_cases": len(reviews), "fully_reviewed_cases": complete_cases,
        "possible_pairs": len(reviews) * len(METRICS), "paired_decisions": paired,
        "agreements": agreements, "agreement_rate": agreements / paired if paired else None,
        "unreviewed_decisions": unreviewed, "uncertain_decisions": uncertain,
        "metrics": totals, "comparisons": comparisons, "disagreements": disagreements,
        "interpretation": (
            "Agreement is matching human/judge metric decisions divided by explicit paired decisions, "
            "not model accuracy or proof of judge validity. Unreviewed/uncertain labels are excluded "
            "and reduce coverage. These pilot cases are development data, not a representative benchmark. "
            "Prior exposure to scores/findings can bias human ratings. Keep the original labels; "
            "record disagreement investigations separately."
        ),
    }
    if assistant is not None:
        report["assistant_reviewer"] = assistant_review["reviewer"]
        report["assistant_review_sha256"] = _fingerprint(assistant_review)
        report["assistant_comparison"] = _assistant_agreement(reviews, assistant)
    return report


def comparison_markdown(report):
    def percentage(value):
        return "not available" if value is None else f"{value:.1%}"

    lines = [
        "# Human versus local LLM judge review", "",
        f"- Source run: `{report['source_run_id']}`.",
        f"- Reviewer: {report['reviewer'] or 'not provided'}.",
        f"- Status: {report['status']}; fully reviewed cases: {report['fully_reviewed_cases']}/{report['selected_cases']}.",
        f"- Prior exposure: {report['prior_exposure'] or 'not declared'}.",
        f"- Paired metric decisions: {report['paired_decisions']}/{report['possible_pairs']}; "
        f"agreement: {report['agreements']}/{report['paired_decisions']} "
        f"({percentage(report['agreement_rate'])}).",
        f"- Unreviewed: {report['unreviewed_decisions']}; uncertain: {report['uncertain_decisions']}.",
        f"- Written reasons: {report['reason_coverage']['written_reasons']}/"
        f"{report['reason_coverage']['rated_decisions']}; reason policy: {report['reason_policy']}.",
        "", "| Metric | Paired | Agreements | Agreement rate | Unreviewed | Uncertain |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, metric in report["metrics"].items():
        lines.append(f"| {name} | {metric['paired']} | {metric['agreements']} | "
                     f"{percentage(metric['agreement_rate'])} | {metric['unreviewed']} | {metric['uncertain']} |")
    secondary = report.get("assistant_comparison")
    if secondary is not None:
        lines.extend([
            "", "## Earlier AI assistant reference", "",
            f"Human/assistant agreement: {secondary['matching_decisions']}/"
            f"{secondary['paired_decisions']} ({percentage(secondary['agreement_rate'])}). "
            "The assistant ratings retain AI authorship and are secondary to the human/local-judge comparison.",
            "",
        ])
    lines.extend(["", "## Individual decisions", ""])
    if secondary is not None:
        lines.extend(["| Case | Metric | Human | Local judge | AI assistant |",
                      "| ---: | --- | --- | --- | --- |"])
    else:
        lines.extend(["| Case | Metric | Human | Local judge |",
                      "| ---: | --- | --- | --- |"])
    for row in report["comparisons"]:
        cells = [str(row["case_number"]), row["metric"], row["human_verdict"] or "not reviewed",
                 row["judge_verdict"]]
        if secondary is not None:
            cells.append(row["assistant_verdict"] or "not reviewed")
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(["", "## Disagreements", ""])
    if not report["disagreements"]:
        lines.append("No disagreements among paired decisions. Unreviewed decisions are not agreements.")
    for disagreement in report["disagreements"]:
        lines.extend([
            f"### {disagreement['case_id']} / {disagreement['metric']}", "",
            f"Question: {disagreement['question']}", "",
            f"Actual response: {disagreement['actual_response']}", "",
            f"Human: **{disagreement['human_verdict']}**. "
            f"{disagreement['human_reason'] or 'No written rationale supplied.'}", "",
            f"Judge: **{disagreement['judge_verdict']}**, score {disagreement['judge_score']}, "
            f"threshold {disagreement['judge_threshold']}. {disagreement['judge_reason']}", "",
        ])
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    if report["prior_exposure"] == "scores_or_findings_seen":
        lines.extend(["This review was non-blinded: prior scores or findings had been seen. "
                      "Independent blinded validation remains outstanding.", ""])
    if report["reason_coverage"]["missing_written_reasons"]:
        lines.extend(["Some recorded verdicts have no human-written explanation. Missing reasons "
                      "are reported separately from rating coverage; no AI rationale is attributed to the human.", ""])
    if report.get("evidence_files"):
        lines.extend(["## Evidence", ""])
        labels = {"source_results": "Original pilot results", "human_review": "Human review worksheet",
                  "assistant_review": "Earlier AI assistant review"}
        for key, target in report["evidence_files"].items():
            lines.append(f"- [{labels[key]}]({target})")
        lines.append("")
    lines.extend(["## Evidence fingerprints", "",
                  f"- Source results: `{report['source_sha256']}`.",
                  f"- Human worksheet: `{report['human_review_sha256']}`."])
    if "assistant_review_sha256" in report:
        lines.append(f"- AI reference: `{report['assistant_review_sha256']}`.")
    lines.append("")
    return "\n".join(lines)
