"""Plan repeated pilot requests and distinguish text stability from answer quality."""

import copy
import csv
import hashlib
import json
import math
from collections import Counter
from statistics import mean

from llm_eval.config import fingerprint
from llm_eval.ollama_client import deterministic_checks
from llm_eval.reporting import METRICS, case_outcome, write_json

DEFAULT_CATEGORIES = ("answerable", "unanswerable", "instruction_in_context")


def make_plan(dataset, repeats=3, case_ids=None):
    if type(repeats) is not int or not 2 <= repeats <= 5:
        raise ValueError("Use 2 to 5 repeats for this bounded development check.")
    available = {case["case_id"]: case for case in dataset["cases"]}
    if case_ids is None:
        case_ids = []
        for category in DEFAULT_CATEGORIES:
            case = next((item for item in dataset["cases"] if item["category"] == category), None)
            if case is None:
                raise ValueError(f"No pilot case found for default category: {category}.")
            case_ids.append(case["case_id"])
        selection = "first case in pilot order for each default coverage category"
    else:
        selection = "explicit case IDs supplied before execution"
    if not case_ids or len(set(case_ids)) != len(case_ids) or any(case_id not in available for case_id in case_ids):
        raise ValueError("Case IDs must be nonempty, unique and present in the pilot.")
    cases = [copy.deepcopy(available[case_id]) for case_id in case_ids]
    plan = {
        "case_ids": list(case_ids), "case_count": len(cases), "repeats": repeats,
        "generation_requests": len(cases) * repeats,
        "metric_evaluations": len(cases) * repeats * len(METRICS),
        "selection_method": selection,
        "generation_policy": "fresh two-message requests; unchanged temperature, seed and model options",
    }
    return plan, cases


def new_consistency_state(run_id, config, plan, cases, metadata):
    return {
        "run_type": "response_consistency", "schema_version": 1, "run_id": run_id,
        "config": copy.deepcopy(config), "plan": copy.deepcopy(plan), "cases": copy.deepcopy(cases),
        "metadata": {**metadata, "selection_sha256": fingerprint(cases), "plan_sha256": fingerprint(plan)},
        "results": [
            {"case": copy.deepcopy(case), "repeat": repeat, "generation": {}, "checks": {}, "metrics": {}}
            for case in cases for repeat in range(1, plan["repeats"] + 1)
        ],
        "phase_errors": [], "unloads": {"answer": False, "judge": False},
        "memory_snapshots": [], "attempts": [],
    }


def validate_trials(state):
    """Reject modified evidence and invalid completed scores before resume/reporting."""
    if state.get("run_type") != "response_consistency" or state.get("schema_version") != 1:
        raise ValueError("Select a response-consistency run.")
    plan, cases = state["plan"], state["cases"]
    if type(plan["repeats"]) is not int or not 2 <= plan["repeats"] <= 5:
        raise ValueError("Saved repeat count is invalid.")
    ids = [case["case_id"] for case in cases]
    if not ids or len(set(ids)) != len(ids) or ids != plan["case_ids"] or len(ids) != plan["case_count"]:
        raise ValueError("Saved selection contains missing, reordered or duplicate cases.")
    expected = [(case, repeat) for case in cases for repeat in range(1, plan["repeats"] + 1)]
    if (len(state["results"]) != len(expected) or plan["generation_requests"] != len(expected)
            or plan["metric_evaluations"] != len(expected) * len(METRICS)):
        raise ValueError("Saved run does not contain the complete planned trial matrix.")
    if (fingerprint(cases) != state["metadata"]["selection_sha256"]
            or fingerprint(plan) != state["metadata"]["plan_sha256"]):
        raise ValueError("Saved selection or plan was modified.")
    for row, (case, repeat) in zip(state["results"], expected, strict=True):
        if row["case"] != case or type(row["repeat"]) is not int or row["repeat"] != repeat:
            raise ValueError("Saved case inputs or repeat identities were modified.")
        generation = row.get("generation", {})
        if generation.get("status") == "completed":
            response = generation.get("actual_response")
            if (not isinstance(response, str) or not response.strip()
                    or generation.get("response_sha256") != hashlib.sha256(response.encode("utf-8")).hexdigest()):
                raise ValueError("A saved response was modified or is invalid.")
            if row.get("checks") and row["checks"] != deterministic_checks(case, response):
                raise ValueError("Saved deterministic checks do not match the response.")
        for name, metric in row.get("metrics", {}).items():
            if name not in METRICS:
                raise ValueError("Saved metric name is unknown.")
            if metric.get("status") == "completed":
                score, threshold = metric.get("score"), metric.get("threshold")
                if (generation.get("status") != "completed" or type(score) not in (int, float)
                        or not math.isfinite(score) or not 0 <= score <= 1
                        or type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 <= threshold <= 1
                        or threshold != state["config"]["thresholds"][name]
                        or type(metric.get("passed")) is not bool or metric["passed"] != (score >= threshold)
                        or not isinstance(metric.get("reason"), str) or not metric["reason"].strip()):
                    raise ValueError("A saved completed metric is invalid.")


def summarize_consistency(state):
    validate_trials(state)
    per_case = []
    for case in state["cases"]:
        rows = [row for row in state["results"] if row["case"]["case_id"] == case["case_id"]]
        outcomes = Counter(case_outcome(row) for row in rows)
        responses = [row["generation"]["actual_response"] for row in rows if row["generation"].get("status") == "completed"]
        generated_all = len(responses) == state["plan"]["repeats"]
        evaluated_all = outcomes["error"] + outcomes["incomplete"] == 0
        decisions = [tuple(row["metrics"][name]["passed"] for name in METRICS) for row in rows] if evaluated_all else []
        per_case.append({
            "case_id": case["case_id"], "category": case["category"], "planned_repeats": len(rows),
            "completed_generations": len(responses), "unique_exact_responses": len(set(responses)),
            "unique_normalized_responses": len({" ".join(response.split()).casefold() for response in responses}),
            "exact_stable": len(set(responses)) == 1 if generated_all else None,
            "normalized_stable": len({" ".join(response.split()).casefold() for response in responses}) == 1 if generated_all else None,
            "quality_passes": outcomes["passed"], "quality_failures": outcomes["failed"],
            "errors": outcomes["error"], "incomplete": outcomes["incomplete"],
            "all_repeats_quality_pass": outcomes["failed"] == 0 if evaluated_all else None,
            "metric_decisions_stable": len(set(decisions)) == 1 if evaluated_all else None,
        })
    outcomes = Counter(case_outcome(row) for row in state["results"])
    metric_totals = {}
    for name in METRICS:
        entries = [row.get("metrics", {}).get(name, {}) for row in state["results"]]
        completed = [metric for metric in entries if metric.get("status") == "completed"]
        metric_totals[name] = {
            "completed": len(completed), "errors": sum(metric.get("status") == "error" for metric in entries),
            "failed": sum(not metric["passed"] for metric in completed),
            "average_score": mean(metric["score"] for metric in completed) if completed else None,
        }
    return {
        "case_count": len(per_case), "planned_trials": len(state["results"]),
        "completed_generations": sum(item["completed_generations"] for item in per_case),
        "quality_passed_trials": outcomes["passed"], "quality_failed_trials": outcomes["failed"],
        "errors": outcomes["error"], "incomplete": outcomes["incomplete"],
        "execution_complete": (outcomes["error"] + outcomes["incomplete"] == 0
                               and not state["phase_errors"] and all(state["unloads"].get(role) is True for role in ("answer", "judge"))),
        "cases_with_all_repeats_passing": sum(item["all_repeats_quality_pass"] is True for item in per_case),
        "cases_with_all_generations": sum(item["exact_stable"] is not None for item in per_case),
        "exact_stable_cases": sum(item["exact_stable"] is True for item in per_case),
        "normalized_stable_cases": sum(item["normalized_stable"] is True for item in per_case),
        "phase_errors": len(state["phase_errors"]), "metrics": metric_totals, "cases": per_case,
        "human_validation": {"status": "not_started", "agreement_rate": None},
    }


def save_consistency_reports(run_dir, state):
    summary = state["summary"] = summarize_consistency(state)
    write_json(run_dir / "results.json", state)
    columns = ["case_id", "repeat", "category", "question", "context", "expected_answers", "actual_response",
               "outcome", "abstention_contract", "response_sha256", "generation_error"]
    columns += [f"{name}_{field}" for name in METRICS for field in ("score", "passed", "reason", "error")]
    with (run_dir / "results.csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for trial in state["results"]:
            case, generation = trial["case"], trial["generation"]
            row = {key: case[key] for key in ("case_id", "category", "question", "context")}
            row.update(repeat=trial["repeat"], expected_answers=json.dumps(case["expected_answers"], ensure_ascii=False),
                       actual_response=generation.get("actual_response", ""), outcome=case_outcome(trial),
                       abstention_contract=trial["checks"].get("abstention_contract"),
                       response_sha256=generation.get("response_sha256"), generation_error=generation.get("error"))
            for name in METRICS:
                for field in ("score", "passed", "reason", "error"):
                    row[f"{name}_{field}"] = trial["metrics"].get(name, {}).get(field)
            writer.writerow(row)
    lines = [
        "# Repeated-response development check", "",
        f"- Run: {state['run_id']}; cases: {summary['case_count']}; repeats per case: {state['plan']['repeats']}.",
        f"- Answer model: {state['config']['answer']['model']}; judge: {state['config']['judge']['model']}.",
        f"- Planned trials: {summary['planned_trials']}; generated: {summary['completed_generations']}.",
        f"- Quality passes: {summary['quality_passed_trials']}; flags: {summary['quality_failed_trials']}; "
        f"errors: {summary['errors']}; incomplete: {summary['incomplete']}; phase errors: {summary['phase_errors']}.",
        f"- Execution complete: {summary['execution_complete']}; model unloading: {state['unloads']}.",
        f"- Cases with all repeats passing: {summary['cases_with_all_repeats_passing']}/{summary['case_count']}.",
        "- Human validation: pending; agreement is not computed.", "",
        "| Case | Exact stable | Normalized stable | Passing repeats | Errors | Incomplete | Metric decisions stable |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for case in summary["cases"]:
        values = ["pending" if case[key] is None else str(case[key]) for key in ("exact_stable", "normalized_stable", "metric_decisions_stable")]
        lines.append(f"| {case['case_id']} | {values[0]} | {values[1]} | {case['quality_passes']}/{case['planned_repeats']} | "
                     f"{case['errors']} | {case['incomplete']} | {values[2]} |")
    lines.extend(["", "## Metric totals", "", "| Metric | Completed | Mean score | Flags | Errors |",
                  "| --- | ---: | ---: | ---: | ---: |"])
    for name, metric in summary["metrics"].items():
        score = "pending" if metric["average_score"] is None else f"{metric['average_score']:.3f}"
        lines.append(f"| {name} | {metric['completed']} | {score} | {metric['failed']} | {metric['errors']} |")
    for trial in state["results"]:
        lines.extend(["", f"## {trial['case']['case_id']} — repeat {trial['repeat']}", "",
                      f"Question: {trial['case']['question']}", "",
                      f"Reference alternatives: {json.dumps(trial['case']['expected_answers'], ensure_ascii=False)}", "",
                      f"Actual response: {trial['generation'].get('actual_response', 'not generated')}", "",
                      f"Outcome: {case_outcome(trial)}; deterministic checks: {trial['checks']}.", ""])
        if trial["generation"].get("error"):
            lines.extend([f"Generation error: {trial['generation']['error']}", ""])
        for name, metric in trial["metrics"].items():
            lines.extend([f"- {name}: {metric.get('score')}; passed={metric.get('passed')}. "
                          f"{metric.get('reason') or metric.get('error', 'pending')}", ""])
    lines.extend(["", "## Phase errors", "", *state["phase_errors"], "", "## Interpretation", "",
                  "Exact stability compares unmodified text. Normalized stability only ignores casing and whitespace; it is not a semantic-equivalence metric. An identical wrong answer can still fail every quality check.", "",
                  "Each repeat uses the same complete prompt, seed and generation options in a fresh request. This measures repeatability under fixed settings, not robustness to prompt changes or sampling settings. Warm requests may benefit from server caching.", "",
                  "Quality and metric-decision stability depend on the small local judge, whose errors and variability can affect these findings. Human validation is pending. These selected development cases and repeated observations do not establish general accuracy.", ""])
    (run_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
