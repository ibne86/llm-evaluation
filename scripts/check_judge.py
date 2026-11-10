"""Check the originally planned local judge's memory and structured outputs."""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import ollama
from pydantic import BaseModel, Field

from benchmark_model import memory_snapshot

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "runs"
HOST = "http://127.0.0.1:11434"
MODEL = "qwen3:4b"
OPTIONS = {
    "num_gpu": 0,
    "num_ctx": 1024,
    "num_predict": 160,
    "num_batch": 16,
    "num_thread": 4,
    "temperature": 0,
    "seed": 42,
}


class Verdict(BaseModel):
    score: Literal[0, 1]
    reason: str = Field(min_length=1, max_length=240)


def print_summary(report: dict) -> None:
    print(f"Judge model: {report['model']}")
    print(f"Structured-output status: {report['status']}")
    for check in report["checks"]:
        print(f"{check['label']}: score={check['verdict']['score']}; expected={check['expected_score']}; {check['wall_seconds']:.3f}s")
    for label, snapshot in report["memory_snapshots"].items():
        print(f"Available system RAM ({label}): {snapshot['available_gib']:.3f} GiB")
    print(f"Judge unloaded: {report.get('model_unloaded')}")
    print(f"DeepEval metric: {report['deepeval_metric_status']}")
    for error in report["errors"]:
        print(f"Error during {error['stage']}: {error['message']}")


def save_report(report: dict) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS / f"judge-check-{report['run_id']}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Original judge feasibility and structured-output check",
        "",
        f"- Model: {MODEL}",
        f"- Digest: {report.get('model_digest', 'not available')}",
        f"- Status: {report['status']}",
        f"- DeepEval metric: {report['deepeval_metric_status']}",
        f"- Judge unloaded: {report.get('model_unloaded')}",
        f"- Options: `{json.dumps(OPTIONS)}`; `think=false`; sequential requests.",
        "",
        "## Controls",
        "",
    ]
    for check in report["checks"]:
        lines.append(f"- {check['label']}: {check['verdict']} (expected score {check['expected_score']}); {check['wall_seconds']} seconds.")
    lines.extend(["", "## Available system RAM snapshots", ""])
    for label, snapshot in report["memory_snapshots"].items():
        lines.append(f"- {label}: {snapshot['available_gib']} GiB.")
    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        for error in report["errors"]:
            lines.extend([f"Stage: {error['stage']}", "", "```text", error["message"], "```", ""])
    lines.extend([
        "",
        "These synthetic setup controls are separate from the SQuAD pilot and final evaluation.",
        "Valid JSON and two simple control decisions would show basic integration only, not judge accuracy.",
        "Memory snapshots describe the entire system, not model-only RSS or peak memory.",
        "No alternate judge model is selected or downloaded by this script.",
    ])
    markdown_path = report_path.with_suffix(".md")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"JSON report: {report_path}")
    print(f"Readable report: {markdown_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pull", action="store_true", help="Download the original judge if absent.")
    parser.add_argument("--summary", action="store_true", help="Read saved results without model inference.")
    args = parser.parse_args()
    if args.summary:
        reports = sorted(RESULTS.glob("judge-check-*.json"))
        if not reports:
            print("No judge report exists yet.")
            return 1
        print_summary(json.loads(reports[-1].read_text(encoding="utf-8")))
        return 0

    report = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
        "model": MODEL,
        "status": "error",
        "options": OPTIONS,
        "think": False,
        "checks": [],
        "memory_snapshots": {},
        "errors": [],
        "deepeval_metric_status": "not attempted; structured-output feasibility must pass first",
    }
    client = ollama.Client(host=HOST, timeout=120)
    stage = "preflight"
    request_started = False
    try:
        if client.ps().models:
            raise RuntimeError("Another model is already loaded. No existing model was stopped.")
        installed = {model.model: model for model in client.list().models}
        if MODEL not in installed:
            if not args.pull:
                raise RuntimeError("The original judge is absent; use --pull to download it.")
            stage = "download"
            previous_status, previous_percent = "", -10
            for event in client.pull(MODEL, stream=True):
                percent = int(100 * (event.completed or 0) / event.total) if event.total else None
                if event.status != previous_status:
                    previous_percent = -10
                if event.status != previous_status or (percent is not None and percent >= previous_percent + 10):
                    print(f"Download: {event.status}" + (f" {percent}%" if percent is not None else ""), flush=True)
                    previous_status = event.status
                    if percent is not None:
                        previous_percent = percent
            installed = {model.model: model for model in client.list().models}
        report["model_digest"] = installed[MODEL].digest
        report["model_details"] = client.show(MODEL).model_dump(mode="json").get("details")
        report["memory_snapshots"]["before_inference"] = memory_snapshot()
        print(f"Available RAM before judge request: {report['memory_snapshots']['before_inference']['available_gib']:.3f} GiB", flush=True)

        for label, answer, expected_score in (("correct_answer", "2018", 1), ("incorrect_answer", "2021", 0)):
            stage = label
            prompt = (
                "Evaluate whether the answer is correct using only the context. "
                "Score 1 for a correct answer and 0 for an incorrect answer. "
                "Give a brief one-sentence reason.\n"
                "Context: The Cedar Library opened in 2018.\n"
                "Question: In what year did the Cedar Library open?\n"
                f"Answer to evaluate: {answer}\n"
                f"Return only JSON matching this schema: {json.dumps(Verdict.model_json_schema())}"
            )
            request_started = True
            print(f"Running original judge control: {label}...", flush=True)
            start = time.perf_counter()
            response = client.chat(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                format=Verdict.model_json_schema(),
                options=OPTIONS,
                think=False,
                keep_alive="30s",
            )
            if not response.done or response.done_reason == "length":
                raise RuntimeError("Judge output did not complete within the bounded response budget.")
            verdict = Verdict.model_validate_json(response.message.content or "")
            report["checks"].append({
                "label": label,
                "expected_score": expected_score,
                "verdict": verdict.model_dump(),
                "control_passed": verdict.score == expected_score,
                "wall_seconds": round(time.perf_counter() - start, 6),
                "load_seconds": round((response.load_duration or 0) / 1e9, 6),
                "output_tokens": response.eval_count,
                "prompt_tokens": response.prompt_eval_count,
                "done_reason": response.done_reason,
                "unexpected_thinking_output": bool(response.message.thinking),
            })
            report["memory_snapshots"][f"after_{label}"] = memory_snapshot()
            print(f"Control {label}: score {verdict.score}; expected {expected_score}", flush=True)

        if not all(check["control_passed"] and not check["unexpected_thinking_output"] for check in report["checks"]):
            raise RuntimeError("Structured output was valid, but a control decision or thinking-mode check failed.")
        report["status"] = "structured_controls_passed"
    except Exception as error:
        report["errors"].append({"stage": stage, "message": f"{type(error).__name__}: {error}"})
    finally:
        if request_started:
            try:
                cleanup = ollama.Client(host=HOST, timeout=15)
                if any(model.model == MODEL for model in cleanup.ps().models):
                    cleanup.generate(model=MODEL, keep_alive=0)
                report["model_unloaded"] = not any(model.model == MODEL for model in cleanup.ps().models)
                cleanup.close()
                report["memory_snapshots"]["after_cleanup"] = memory_snapshot()
                if not report["model_unloaded"]:
                    raise RuntimeError("Judge is still listed as loaded after cleanup.")
            except Exception as error:
                report["status"] = "error"
                report["errors"].append({"stage": "cleanup", "message": str(error)})
        print_summary(report)
        save_report(report)
        client.close()
    return 0 if report["status"] == "structured_controls_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
