"""Generate first, unload, then judge sequentially with checkpointed results."""

import copy
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "1"
os.environ["DEEPEVAL_DISABLE_DOTENV"] = "1"

import ollama

from llm_eval.config import ROOT, fingerprint, load_config
from llm_eval.dataset import load_dataset, sha256_bytes
from llm_eval.judge import LocalOllamaJudge
from llm_eval.metrics import CORRECTNESS_STEPS, GROUNDEDNESS_STEPS, build_metrics, make_test_case, measure_metric, validate_prompt_budgets
from llm_eval.ollama_client import SYSTEM_PROMPT, deterministic_checks, ensure_idle, generate_answer, unload_model
from llm_eval.reporting import save_reports, summarize
from llm_eval.resources import memory_snapshot

RUNS = ROOT / "results" / "runs"


def read_run(path):
    path = Path(path).resolve()
    if not path.is_relative_to(RUNS.resolve()) or not path.is_dir():
        raise ValueError("Select an existing run folder inside this project's results/runs.")
    return path, json.loads((path / "results.json").read_text(encoding="utf-8-sig"))


def signatures(config, dataset_path, digests, server_version):
    code_files = ("config.py", "dataset.py", "judge.py", "metrics.py", "ollama_client.py", "runner.py")
    source_hashes = {name: sha256_bytes((Path(__file__).parent / name).read_bytes()) for name in code_files}
    dataset_hash = sha256_bytes(dataset_path.read_bytes())
    software = {name: version(name) for name in ("deepeval", "ollama", "pydantic")}
    generation = fingerprint({
        "dataset_sha256": dataset_hash, "prompt": SYSTEM_PROMPT, "prompt_version": config["prompt_version"],
        "answer": config["answer"], "model_digest": digests[config["answer"]["model"]],
        "server_version": server_version, "client_version": software["ollama"],
        "generation_source": source_hashes["ollama_client.py"],
    })
    return {
        "case_count": 10, "dataset_sha256": dataset_hash, "model_digests": digests,
        "software": software, "python_version": sys.version.split()[0], "ollama_server_version": server_version,
        "source_hashes": source_hashes, "config_sha256": fingerprint(config),
        "generation_signature": generation,
        "evaluation_signature": fingerprint({
            "config": config, "dataset": dataset_hash, "digests": digests, "sources": source_hashes,
            "software": software, "server_version": server_version,
            "correctness_steps": CORRECTNESS_STEPS, "groundedness_steps": GROUNDEDNESS_STEPS,
        }),
    }


def validate_saved_cases(saved, cases):
    if len(saved["results"]) != len(cases):
        raise ValueError("Saved run case count does not match the pilot.")
    for result, case in zip(saved["results"], cases):
        if result["case"] != case:
            raise ValueError("Saved case inputs differ from the current dataset.")
        generation = result.get("generation", {})
        if generation.get("status") == "completed":
            content_hash = hashlib.sha256(generation["actual_response"].encode()).hexdigest()
            if content_hash != generation.get("response_sha256"):
                raise ValueError("A saved response was modified or corrupted.")


def new_state(config, dataset, metadata, previous=None):
    state = {
        "run_id": "pilot-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
        "config": config, "metadata": metadata, "dataset_metadata": dataset["metadata"],
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "results": [{"case": copy.deepcopy(case), "generation": {}, "checks": {}, "metrics": {}} for case in dataset["cases"]],
        "phase_errors": [], "unloads": {}, "memory_snapshots": [], "attempts": [],
    }
    if previous:
        validate_saved_cases(previous, dataset["cases"])
        if previous["metadata"]["generation_signature"] != metadata["generation_signature"]:
            raise ValueError("Saved responses use different inputs, answer settings, source, or model digest.")
        state["reused_responses_from"] = previous["run_id"]
        for old, result in zip(previous["results"], state["results"]):
            if old["generation"].get("status") == "completed":
                result["generation"] = copy.deepcopy(old["generation"])
                result["checks"] = deterministic_checks(result["case"], result["generation"]["actual_response"])
    return state


def run_pilot(config_path=None, resume=None, reuse_responses=None):
    config = load_config(config_path)
    dataset_path = ROOT / config["dataset"]
    dataset = load_dataset(dataset_path)
    client = ollama.Client(host=config["host"], timeout=config["timeout_seconds"], trust_env=False)
    cleanup = ollama.Client(host=config["host"], timeout=15, trust_env=False)
    state, run_dir = None, None
    try:
        installed = {model.model: model.digest for model in client.list().models}
        models = [config["answer"]["model"], config["judge"]["model"]]
        if any(model not in installed for model in models):
            raise ValueError("A configured local model is absent; complete the model setup first.")
        digests = {model: installed[model] for model in models}
        with build_opener(ProxyHandler({})).open(config["host"] + "/api/version", timeout=10) as response:
            server_version = json.load(response)["version"]
        metadata = signatures(config, dataset_path, digests, server_version)
        if resume:
            run_dir, state = read_run(resume)
            validate_saved_cases(state, dataset["cases"])
            if state["metadata"]["evaluation_signature"] != metadata["evaluation_signature"]:
                raise ValueError("Resume settings/code/data changed. Use --reuse-responses for a separately recorded re-evaluation if generation still matches.")
            state["attempts"].append({"started_at_utc": datetime.now(timezone.utc).isoformat(), "previous_phase_errors": state.get("phase_errors", [])})
            state["phase_errors"] = []
        else:
            previous = read_run(reuse_responses)[1] if reuse_responses else None
            state = new_state(config, dataset, metadata, previous)
            run_dir = RUNS / state["run_id"]
            run_dir.mkdir(parents=True, exist_ok=False)
        print(f"Run folder: {run_dir}", flush=True)
        save_reports(run_dir, state)

        # Check prompt sizes before any generation. This constructs metrics but
        # does not call the judge model, and closes the temporary HTTP client.
        preflight_judge = LocalOllamaJudge(options=config["judge"]["options"], timeout=config["timeout_seconds"])
        try:
            validate_prompt_budgets(dataset["cases"], preflight_judge, config["thresholds"])
        finally:
            preflight_judge.close()

        if any(row["generation"].get("status") != "completed" for row in state["results"]):
            ensure_idle(client)
            state["unloads"]["answer"] = False
            state["memory_snapshots"].append({"stage": "before_generation", **memory_snapshot()})
            try:
                for index, result in enumerate(state["results"], 1):
                    if result["generation"].get("status") == "completed":
                        continue
                    case = result["case"]
                    print(f"Generate {index}/10: {case['case_id']}", flush=True)
                    try:
                        result["generation"] = generate_answer(client, case, config)
                        if result["generation"]["status"] == "completed":
                            result["checks"] = deterministic_checks(case, result["generation"]["actual_response"])
                            print(f"Answer: {result['generation']['actual_response']}", flush=True)
                    except Exception as error:
                        result["generation"] = {"status": "error", "error": f"{type(error).__name__}: {error}", "actual_response": ""}
                    save_reports(run_dir, state)
            finally:
                try:
                    state["unloads"]["answer"] = unload_model(cleanup, config["answer"]["model"])
                except Exception as error:
                    state["phase_errors"].append(f"Answer-model cleanup: {error}")
                state["memory_snapshots"].append({"stage": "after_generation_cleanup", **memory_snapshot()})
                save_reports(run_dir, state)
        else:
            state["unloads"]["answer"] = unload_model(cleanup, config["answer"]["model"])

        if not state["phase_errors"]:
            ensure_idle(client)
            judge = LocalOllamaJudge(options=config["judge"]["options"], timeout=config["timeout_seconds"])
            state["unloads"]["judge"] = False
            state["memory_snapshots"].append({"stage": "before_judging", **memory_snapshot()})
            try:
                for index, result in enumerate(state["results"], 1):
                    if result["generation"].get("status") != "completed":
                        continue
                    case = result["case"]
                    test_case = make_test_case(case, result["generation"]["actual_response"])
                    for name, metric in build_metrics(judge, config["thresholds"]).items():
                        if result["metrics"].get(name, {}).get("status") == "completed":
                            continue
                        print(f"Judge {index}/10: {case['case_id']} / {name}", flush=True)
                        start = len(judge.request_log)
                        try:
                            measured = measure_metric(metric, test_case)
                            print(f"Score {name}: {measured['score']:.2f}; passed={measured['passed']}", flush=True)
                        except Exception as error:
                            measured = {"status": "error", "score": None, "passed": None, "error": f"{type(error).__name__}: {error}"}
                            print(f"Metric error: {measured['error']}", flush=True)
                        measured["requests"] = copy.deepcopy(judge.request_log[start:])
                        result["metrics"][name] = measured
                        save_reports(run_dir, state)
                    state["memory_snapshots"].append({"stage": f"after_judging_{index}", **memory_snapshot()})
            finally:
                judge.close()
                try:
                    state["unloads"]["judge"] = unload_model(cleanup, config["judge"]["model"])
                except Exception as error:
                    state["phase_errors"].append(f"Judge-model cleanup: {error}")
                state["memory_snapshots"].append({"stage": "after_judge_cleanup", **memory_snapshot()})
                state["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
                save_reports(run_dir, state)
        summary = summarize(state)
        print(json.dumps(summary, indent=2), flush=True)
        print(f"Readable report: {run_dir / 'summary.md'}", flush=True)
        if not summary["execution_complete"]:
            return 2
        return 1 if summary["failed"] else 0
    except Exception as error:
        if state is not None and run_dir is not None:
            state["phase_errors"].append(f"Orchestration: {type(error).__name__}: {error}")
            save_reports(run_dir, state)
        print(f"Pilot execution error: {type(error).__name__}: {error}", flush=True)
        return 2
    finally:
        client.close()
        cleanup.close()
