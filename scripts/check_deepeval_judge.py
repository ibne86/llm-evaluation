"""Check a real DeepEval metric against the original local judge."""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "1"
os.environ["DEEPEVAL_DISABLE_DOTENV"] = "1"

import ollama
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

from benchmark_model import memory_snapshot
from llm_eval.judge import JUDGE_MODEL, JUDGE_OPTIONS, OLLAMA_HOST, LocalOllamaJudge

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "runs"


def print_summary(report):
    print(f"DeepEval judge check: {report['status']}")
    print(f"Judge model: {report['model']}")
    for result in report["controls"]:
        print(f"{result['label']}: score={result['score']}; expected_pass={result['expected_pass']}; {result['wall_seconds']:.3f}s")
        print(f"Reason: {result['reason']}")
    print(f"Judge unloaded: {report.get('model_unloaded')}")
    for note in report.get("review_notes", []):
        print(f"Review note: {note['note']}")
    for error in report["errors"]:
        print(f"Error: {error}")


def save_report(report):
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"deepeval-judge-{report['run_id']}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# DeepEval local judge integration check", "",
        f"- Status: {report['status']}",
        f"- Judge: {JUDGE_MODEL}; digest: {report.get('model_digest', 'unavailable')}",
        f"- DeepEval: {report['deepeval_version']}",
        f"- Options: `{json.dumps(JUDGE_OPTIONS)}`; think=false; metric async_mode=false; eval_mode=llm.",
        f"- Judge unloaded: {report.get('model_unloaded')}", "",
    ]
    for result in report["controls"]:
        lines.extend([
            f"## {result['label']}", "",
            f"- Answer: {result['actual_output']}",
            f"- Relevancy score: {result['score']}; threshold: 0.7; expected pass: {result['expected_pass']}",
            f"- Decision matched control: {result['control_passed']}",
            f"- Wall time: {result['wall_seconds']} seconds.",
            f"- Reason: {result['reason']}", "",
        ])
    lines.extend(["## Available system RAM snapshots", ""])
    for label, snapshot in report["memory_snapshots"].items():
        lines.append(f"- {label}: {snapshot['available_gib']} GiB.")
    if report["errors"]:
        lines.extend(["", "## Errors", ""] + [f"- {error}" for error in report["errors"]])
    lines.extend([
        "", "These are synthetic setup controls, not SQuAD cases or the 10-case pilot.",
        "The metric checks relevancy only; a relevant answer can still be factually wrong.",
        "Passing two obvious controls does not establish judge accuracy. Human review remains required.",
        "Memory values describe the whole system, not peak or process-only memory.",
    ])
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"JSON report: {path}")
    print(f"Readable report: {path.with_suffix('.md')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", action="store_true", help="Read saved results without inference.")
    args = parser.parse_args()
    if args.summary:
        reports = sorted(RESULTS.glob("deepeval-judge-*.json"))
        if not reports:
            print("No saved DeepEval judge check exists yet.")
            return 1
        print_summary(json.loads(reports[-1].read_text(encoding="utf-8")))
        return 0

    report = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
        "status": "error", "model": JUDGE_MODEL,
        "deepeval_version": version("deepeval"),
        "options": JUDGE_OPTIONS, "controls": [], "memory_snapshots": {}, "errors": [],
    }
    client = ollama.Client(host=OLLAMA_HOST, timeout=15)
    judge = None
    request_started = False
    try:
        if client.ps().models:
            raise RuntimeError("Another model is already loaded; it was not stopped.")
        report["model_digest"] = next(model.digest for model in client.list().models if model.model == JUDGE_MODEL)
        report["memory_snapshots"]["before_metric"] = memory_snapshot()
        judge = LocalOllamaJudge()
        for label, answer, expected_pass in (
            ("relevant_answer", "The Cedar Library opened in 2018.", True),
            ("irrelevant_answer", "Bananas are yellow.", False),
        ):
            print(f"Running DeepEval answer relevancy: {label}...", flush=True)
            metric = AnswerRelevancyMetric(model=judge, threshold=0.7, include_reason=True, async_mode=False, eval_mode="llm")
            case = LLMTestCase(input="In what year did the Cedar Library open?", actual_output=answer, context=["The Cedar Library opened in 2018."])
            request_started = True
            start = time.perf_counter()
            metric.measure(case)
            passed = metric.is_successful()
            report["controls"].append({
                "label": label, "actual_output": answer,
                "score": metric.score, "reason": metric.reason,
                "statements": metric.statements,
                "verdicts": [verdict.model_dump(mode="json") for verdict in metric.verdicts],
                "expected_pass": expected_pass, "control_passed": passed == expected_pass,
                "wall_seconds": round(time.perf_counter() - start, 6),
            })
            report["memory_snapshots"][f"after_{label}"] = memory_snapshot()
            print(f"{label}: score={metric.score}; reason={metric.reason}", flush=True)
        report["loaded_models"] = client.ps().model_dump(mode="json")
        report["status"] = "passed" if all(result["control_passed"] for result in report["controls"]) else "control_failed"
    except Exception as error:
        report["errors"].append(f"{type(error).__name__}: {error}")
    finally:
        if judge:
            report["judge_requests"] = judge.request_log
            judge.close()
        if request_started:
            try:
                if any(model.model == JUDGE_MODEL for model in client.ps().models):
                    client.generate(model=JUDGE_MODEL, keep_alive=0)
                report["model_unloaded"] = not any(model.model == JUDGE_MODEL for model in client.ps().models)
                report["memory_snapshots"]["after_cleanup"] = memory_snapshot()
                if not report["model_unloaded"]:
                    raise RuntimeError("Judge is still listed as loaded after cleanup.")
            except Exception as error:
                report["status"] = "error"
                report["errors"].append(f"Cleanup: {error}")
        print_summary(report)
        save_report(report)
        client.close()
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
