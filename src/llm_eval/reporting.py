"""Write honest summaries that separate quality failures from execution errors."""

import csv
import json
from collections import Counter
from statistics import mean

METRICS = ("answer_relevancy", "correctness", "groundedness")


def case_outcome(result):
    generation = result.get("generation", {})
    metrics = result.get("metrics", {})
    if generation.get("status") == "error" or any(value.get("status") == "error" for value in metrics.values()):
        return "error"
    if generation.get("status") != "completed" or any(name not in metrics for name in METRICS):
        return "incomplete"
    if not {"nonempty_response", "abstention_contract"}.issubset(result.get("checks", {})):
        return "incomplete"
    if any(metrics[name].get("status") != "completed" for name in METRICS):
        return "incomplete"
    if not all(result.get("checks", {}).values()) or any(not metrics[name]["passed"] for name in METRICS):
        return "failed"
    return "passed"


def summarize(state):
    outcomes = Counter(case_outcome(result) for result in state["results"])
    metrics_summary = {}
    for name in METRICS:
        entries = [result.get("metrics", {}).get(name, {}) for result in state["results"]]
        completed = [entry for entry in entries if entry.get("status") == "completed"]
        metrics_summary[name] = {
            "completed": len(completed),
            "errors": sum(entry.get("status") == "error" for entry in entries),
            "average_score": mean(entry["score"] for entry in completed) if completed else None,
            "failed": sum(not entry["passed"] for entry in completed),
        }
    unanswerable = [row for row in state["results"] if row["case"]["category"] == "unanswerable"]
    source_abstention_passes = sum(row.get("checks", {}).get("abstention_contract") is True for row in unanswerable)
    complete = (
        bool(state["results"]) and len(state["results"]) == state["metadata"]["case_count"]
        and outcomes["error"] == 0 and outcomes["incomplete"] == 0 and not state.get("phase_errors")
        and all(state.get("unloads", {}).get(role) is True for role in ("answer", "judge"))
    )
    return {
        "total": len(state["results"]), "passed": outcomes["passed"], "failed": outcomes["failed"],
        "errors": outcomes["error"], "incomplete": outcomes["incomplete"], "execution_complete": complete,
        "phase_errors": len(state.get("phase_errors", [])),
        "metrics": metrics_summary,
        "squad_unanswerable": {"total": len(unanswerable), "exact_abstention_passes": source_abstention_passes},
        "human_validation": {"status": "not_started", "reviewed_cases": 0, "agreement_rate": None},
    }


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def save_reports(run_dir, state):
    state["summary"] = summarize(state)
    write_json(run_dir / "results.json", state)
    columns = ["case_id", "source_id", "category", "question", "context", "expected_answers", "actual_response", "answer_model", "judge_model", "outcome", "abstention_contract"]
    columns += [f"{name}_{field}" for name in METRICS for field in ("score", "passed", "reason", "error")]
    with (run_dir / "results.csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for result in state["results"]:
            case = result["case"]
            row = {
                "case_id": case["case_id"], "source_id": case["source"].get("original_id", "custom"),
                "category": case["category"], "question": case["question"],
                "context": case["context"], "answer_model": state["config"]["answer"]["model"],
                "judge_model": state["config"]["judge"]["model"],
                "expected_answers": json.dumps(case["expected_answers"], ensure_ascii=False),
                "actual_response": result.get("generation", {}).get("actual_response", ""),
                "outcome": case_outcome(result), "abstention_contract": result.get("checks", {}).get("abstention_contract"),
            }
            for name in METRICS:
                metric = result.get("metrics", {}).get(name, {})
                for field in ("score", "passed", "reason", "error"):
                    row[f"{name}_{field}"] = metric.get(field)
            writer.writerow(row)
    summary = state["summary"]
    lines = [
        "# Ten-case development pilot", "",
        f"- Answer model: {state['config']['answer']['model']}; judge: {state['config']['judge']['model']}.",
        f"- Total: {summary['total']}; quality passes: {summary['passed']}; quality failures: {summary['failed']}; case execution errors: {summary['errors']}; phase errors: {summary['phase_errors']}; incomplete: {summary['incomplete']}.",
        f"- Execution complete: {summary['execution_complete']}. A quality failure does not by itself mean the harness failed to execute.",
        f"- SQuAD unanswerable exact-abstention checks: {summary['squad_unanswerable']['exact_abstention_passes']}/{summary['squad_unanswerable']['total']}.",
        "- Human validation: not started; agreement rate is not computed.",
        "", "| Metric | Average score | Completed | Failed | Errors |", "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, metric in summary["metrics"].items():
        average = f"{metric['average_score']:.3f}" if metric["average_score"] is not None else "not available"
        lines.append(f"| {name} | {average} | {metric['completed']} | {metric['failed']} | {metric['errors']} |")
    lines.extend(["", "## Per-case outcomes", "", "| Case ID | Category | Outcome |", "| --- | --- | --- |"])
    for result in state["results"]:
        lines.append(f"| {result['case']['case_id']} | {result['case']['category']} | {case_outcome(result)} |")
    lines.extend(["", "## Responses and important findings", ""])
    for result in state["results"]:
        case = result["case"]
        lines.extend([
            f"### {case['case_id']}", "", f"Question: {case['question']}", "",
            f"Reference alternatives: {json.dumps(case['expected_answers'], ensure_ascii=False)}", "",
            f"Actual response: {result.get('generation', {}).get('actual_response', 'not generated')}", "",
            f"Deterministic checks: {result.get('checks', {})}", "",
        ])
        if result.get("generation", {}).get("error"):
            lines.extend([f"Generation error: {result['generation']['error']}", ""])
        for name, metric in result.get("metrics", {}).items():
            if metric.get("status") == "completed":
                lines.extend([f"- {name}: {metric['score']:.2f}, passed={metric['passed']}. Judge reason: {metric['reason']}", ""])
            else:
                lines.extend([f"- {name}: execution error: {metric.get('error')}", ""])
    lines.extend(["## Phase and cleanup records", "", f"Model unloading: {state.get('unloads', {})}", ""])
    for error in state.get("phase_errors", []):
        lines.extend([f"- {error}", ""])
    lines.extend([
        "## Interpretation and limitations", "",
        "These are development cases selected for short, complete contexts and article diversity; they are not a representative benchmark or the final 50-case set.",
        "Scores are judgments from a small local model. A prior control produced an internally inconsistent explanation, so scores and reasons need review. Unsupported-claim flags are judge findings, not human-verified facts.",
        "The exact abstention marker is a strict format contract; semantic abstention correctness is evaluated separately. Groundedness alone does not establish correctness: a refusal can be grounded and still fail an answerable case.",
        "Average scores include only completed metrics; error and incomplete counts remain visible. Memory snapshots cover the whole system and are not peak/model-only memory.",
        "Human reviews and agreement measurement are still pending. A completed run does not unlock the final dataset until the user reviews this pilot.",
        "", "Dataset attribution and license: https://rajpurkar.github.io/SQuAD-explorer/ ; https://creativecommons.org/licenses/by-sa/4.0/ . Original IDs, spans, selection seed and source hash are retained in data/pilot.json.",
    ])
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
