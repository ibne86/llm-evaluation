"""Run two short local CPU requests and save a first performance baseline."""

import argparse
import ctypes
import hashlib
import json
import sys
import time
from ctypes import wintypes
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import ollama

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results" / "runs"
HOST = "http://127.0.0.1:11434"
MODEL = "qwen2.5:1.5b"
OPTIONS = {
    "num_gpu": 0,
    "num_ctx": 1024,
    "num_batch": 32,
    "num_thread": 4,
    "num_predict": 64,
    "temperature": 0,
    "seed": 42,
}
MESSAGES = [
    {
        "role": "system",
        "content": (
            "Answer using only the provided context. If the answer is absent, "
            "reply INSUFFICIENT_CONTEXT. Follow the requested answer format."
        ),
    },
    {
        "role": "user",
        "content": (
            "Context: The Cedar Library opened in 2018. Its director is Maya Chen.\n"
            "Question: In what year did the Cedar Library open?\n"
            "Answer with only the four-digit year."
        ),
    },
]


class MemoryStatus(ctypes.Structure):
    """Windows MEMORYSTATUSEX layout, using the documented field sizes."""

    _fields_ = [
        ("length", wintypes.DWORD),
        ("load_percent", wintypes.DWORD),
        ("total_physical", ctypes.c_ulonglong),
        ("available_physical", ctypes.c_ulonglong),
        ("total_page_file", ctypes.c_ulonglong),
        ("available_page_file", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong),
        ("available_virtual", ctypes.c_ulonglong),
        ("available_extended_virtual", ctypes.c_ulonglong),
    ]


def memory_snapshot() -> dict:
    """Read total-system available physical RAM, without WMI or extra packages."""
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    get_status = ctypes.WinDLL("kernel32", use_last_error=True).GlobalMemoryStatusEx
    get_status.argtypes = [ctypes.POINTER(MemoryStatus)]
    get_status.restype = wintypes.BOOL
    if not get_status(ctypes.byref(status)):
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "available_bytes": status.available_physical,
        "available_gib": round(status.available_physical / 1024**3, 3),
        "total_physical_bytes": status.total_physical,
        "system_memory_load_percent": status.load_percent,
    }


def pull_model(client: ollama.Client) -> None:
    last_status, last_percent = "", -10
    for event in client.pull(MODEL, stream=True):
        percent = int(100 * (event.completed or 0) / event.total) if event.total else None
        if event.status != last_status:
            last_percent = -10
        if event.status != last_status or (percent is not None and percent >= last_percent + 10):
            suffix = f" {percent}%" if percent is not None else ""
            print(f"Download: {event.status}{suffix}", flush=True)
            last_status = event.status
            if percent is not None:
                last_percent = percent


def print_summary(report: dict) -> None:
    print(f"Benchmark status: {report['status']}")
    print(f"Model: {report['model']}")
    for run in report["runs"]:
        print(f"{run['label']}: {run['wall_seconds']:.3f}s; answer={run['answer']!r}")
    for label, snapshot in report["memory_snapshots"].items():
        print(f"Available system RAM ({label}): {snapshot['available_gib']:.3f} GiB")
    print(f"Model unloaded: {report.get('model_unloaded')}")
    for error in report["errors"]:
        print(f"Error: {error}")


def save_report(report: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    file_stem = f"baseline-{report['run_id']}"
    json_path = RESULTS_DIR / f"{file_stem}.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# First answer-model performance baseline",
        "",
        f"- Status: {report['status']}",
        f"- Model: {MODEL}",
        f"- Model digest: {report.get('model_digest', 'unavailable')}",
        f"- CPU request options: `{json.dumps(OPTIONS)}`",
        f"- Model unloaded after the benchmark: {report.get('model_unloaded')}",
        "",
        "| Request | Wall time (seconds) | Load time (seconds) | Output | Exact year check |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for run in report["runs"]:
        answer = run["answer"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {run['label']} | {run['wall_seconds']} | {run['load_seconds']} | {answer} | {run['exact_year_match']} |")
    lines.extend(["", "| Snapshot | Available system RAM (GiB) |", "| --- | ---: |"])
    for label, snapshot in report["memory_snapshots"].items():
        lines.append(f"| {label} | {snapshot['available_gib']} |")
    lines.extend([
        "",
        "This is a synthetic setup prompt, separate from SQuAD and the evaluation datasets.",
        "The second request repeats the first prompt and may benefit from prompt caching.",
        "System RAM snapshots include every running application. They are not peak measurements or model-only RSS.",
        "Ollama's loaded-model size, if recorded in JSON, is its reported allocation rather than measured process RSS.",
        "Two very short answers do not establish general throughput, QA accuracy, judge accuracy, or 50-case runtime.",
        "No DeepEval scoring, judge inference, or final evaluation cases were used.",
    ])
    if report["errors"]:
        lines.extend(["", "## Errors", ""] + [f"- {error}" for error in report["errors"]])
    markdown_path = RESULTS_DIR / f"{file_stem}.md"
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"JSON report: {json_path}")
    print(f"Readable report: {markdown_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pull", action="store_true", help="Download the model if it is not installed.")
    parser.add_argument("--summary", action="store_true", help="Read the latest saved report without running a model.")
    args = parser.parse_args()
    if args.summary:
        reports = sorted(RESULTS_DIR.glob("baseline-*.json"))
        if not reports:
            print("No saved benchmark is available yet.")
            return 1
        print_summary(json.loads(reports[-1].read_text(encoding="utf-8")))
        return 0

    if sys.platform != "win32" or Path(sys.prefix).resolve() != (PROJECT_ROOT / ".venv").resolve():
        print("Run this Windows benchmark with the project's .venv interpreter.")
        return 1
    report = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "error",
        "model": MODEL,
        "host": HOST,
        "python_version": sys.version.split()[0],
        "ollama_client_version": version("ollama"),
        "options": OPTIONS,
        "messages": MESSAGES,
        "prompt_sha256": hashlib.sha256(json.dumps(MESSAGES, sort_keys=True).encode()).hexdigest(),
        "expected_answer": "2018",
        "runs": [],
        "memory_snapshots": {},
        "errors": [],
    }
    client = ollama.Client(host=HOST, timeout=120)
    request_started = False
    try:
        if client.ps().models:
            raise RuntimeError("A model is already loaded. This cold-start check requires an idle Ollama service; no existing model was stopped.")
        installed = {model.model: model for model in client.list().models}
        if MODEL not in installed:
            if not args.pull:
                raise RuntimeError("The model is not installed. Run once with --pull to download it.")
            pull_model(client)
            installed = {model.model: model for model in client.list().models}
        report["model_digest"] = installed[MODEL].digest
        report["model_details"] = client.show(MODEL).model_dump(mode="json").get("details")
        report["memory_snapshots"]["before_inference"] = memory_snapshot()
        print(f"Available RAM before inference: {report['memory_snapshots']['before_inference']['available_gib']:.3f} GiB", flush=True)

        for label in ("cold_start", "warm_repeat"):
            print(f"Running {label} with a short context and bounded answer...", flush=True)
            request_started = True
            start = time.perf_counter()
            response = client.chat(model=MODEL, messages=MESSAGES, options=OPTIONS, stream=False, keep_alive="30s")
            wall_seconds = round(time.perf_counter() - start, 6)
            run = {
                "label": label,
                "answer": response.message.content or "",
                "wall_seconds": wall_seconds,
                "load_seconds": round((response.load_duration or 0) / 1e9, 6),
                "prompt_tokens": response.prompt_eval_count,
                "output_tokens": response.eval_count,
                "generation_seconds": round((response.eval_duration or 0) / 1e9, 6),
                "done": response.done,
                "done_reason": response.done_reason,
                "exact_year_match": (response.message.content or "").strip() == "2018",
            }
            report["runs"].append(run)
            report["memory_snapshots"][f"after_{label}"] = memory_snapshot()
            print(f"Completed {label}: {wall_seconds:.3f}s; answer={run['answer']!r}", flush=True)
            if not response.done or response.done_reason == "length":
                raise RuntimeError("The response did not complete normally; the benchmark is incomplete.")

        loaded = [model for model in client.ps().models if model.model == MODEL]
        if not loaded:
            raise RuntimeError("The model was not present for loaded-memory verification.")
        report["ollama_loaded_model"] = loaded[0].model_dump(mode="json")
        if loaded[0].size_vram != 0:
            raise RuntimeError("Ollama did not confirm the requested CPU-only memory allocation.")
        report["status"] = "completed"
    except Exception as error:
        report["errors"].append(f"{type(error).__name__}: {error}")
    finally:
        if request_started:
            try:
                cleanup_client = ollama.Client(host=HOST, timeout=15)
                cleanup_client.generate(model=MODEL, keep_alive=0)
                for _ in range(10):
                    report["model_unloaded"] = not any(model.model == MODEL for model in cleanup_client.ps().models)
                    if report["model_unloaded"]:
                        break
                    time.sleep(0.5)
                if not report["model_unloaded"]:
                    raise RuntimeError("The model is still listed as loaded after cleanup.")
                report["memory_snapshots"]["after_unload"] = memory_snapshot()
            except Exception as error:
                report["status"] = "error"
                report["errors"].append(f"Cleanup failed: {error}")
        print_summary(report)
        save_report(report)
        client.close()

    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
