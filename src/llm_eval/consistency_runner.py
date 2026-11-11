"""Run bounded repetitions, unload the answer model, then judge every saved trial."""

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

import ollama

from llm_eval.config import ROOT, fingerprint, load_config
from llm_eval.consistency import make_plan, new_consistency_state, save_consistency_reports, summarize_consistency, validate_trials
from llm_eval.dataset import load_dataset, sha256_bytes
from llm_eval.judge import LocalOllamaJudge
from llm_eval.metrics import build_metrics, make_test_case, measure_metric, validate_prompt_budgets
from llm_eval.ollama_client import deterministic_checks, ensure_idle, generate_answer, unload_model
from llm_eval.reporting import METRICS
from llm_eval.resources import memory_snapshot
from llm_eval.runner import signatures

RUNS = ROOT / "results/runs"


def read_consistency_run(path):
    path = Path(path).resolve()
    if not path.is_relative_to(RUNS.resolve()) or not path.is_dir():
        raise ValueError("Select an existing consistency folder inside this project's results/runs.")
    state = json.loads((path / "results.json").read_text(encoding="utf-8-sig"))
    validate_trials(state)
    return path, state


def server_version(host):
    with build_opener(ProxyHandler({})).open(host + "/api/version", timeout=10) as response:
        return json.load(response)["version"]


def consistency_metadata(config, dataset_path, digests, server, plan):
    metadata = signatures(config, dataset_path, digests, server)
    sources = {name: sha256_bytes((Path(__file__).parent / name).read_bytes())
               for name in ("consistency.py", "consistency_runner.py")}
    metadata.update(dataset_case_count=metadata["case_count"], case_count=plan["case_count"],
                    repeat_count=plan["repeats"], trial_count=plan["generation_requests"], consistency_sources=sources)
    metadata["consistency_signature"] = fingerprint({
        "evaluation_signature": metadata["evaluation_signature"], "plan": plan, "sources": sources,
    })
    return metadata


def _cleanup(state, cleanup, role):
    state["unloads"][role] = False
    try:
        state["unloads"][role] = unload_model(cleanup, state["config"][role]["model"])
    except Exception as error:
        state["phase_errors"].append(f"{role} model cleanup: {type(error).__name__}: {error}")
    state["memory_snapshots"].append({"stage": f"after_{role}_cleanup", **memory_snapshot()})


def run_consistency(config_path=None, repeats=None, case_ids=None, resume=None):
    state, run_dir, client, cleanup = None, None, None, None
    try:
        config = load_config(config_path)
        dataset_path = ROOT / config["dataset"]
        dataset = load_dataset(dataset_path)
        previous = read_consistency_run(resume) if resume else None
        if previous:
            saved_plan = previous[1]["plan"]
            if ((repeats is not None and repeats != saved_plan["repeats"])
                    or (case_ids is not None and case_ids != saved_plan["case_ids"])):
                raise ValueError("Resume must use the original repeats and selected case IDs.")
            _, cases = make_plan(dataset, saved_plan["repeats"], saved_plan["case_ids"])
            plan = copy.deepcopy(saved_plan)
            if cases != previous[1]["cases"]:
                raise ValueError("Saved cases differ from the current pilot.")
        else:
            plan, cases = make_plan(dataset, 3 if repeats is None else repeats, case_ids)
        client = ollama.Client(host=config["host"], timeout=config["timeout_seconds"], trust_env=False)
        cleanup = ollama.Client(host=config["host"], timeout=15, trust_env=False)
        installed = {model.model: model.digest for model in client.list().models}
        names = [config[role]["model"] for role in ("answer", "judge")]
        if any(name not in installed for name in names):
            raise ValueError("A configured local model is absent; complete the model setup first.")
        metadata = consistency_metadata(config, dataset_path, {name: installed[name] for name in names},
                                        server_version(config["host"]), plan)
        now = datetime.now(timezone.utc)
        if previous:
            candidate = previous[1]
            if candidate["metadata"]["consistency_signature"] != metadata["consistency_signature"]:
                raise ValueError("Resume settings, code, data, model digests or software changed; start a new run.")
            run_dir, state = previous
            state["attempts"].append({"started_at_utc": now.isoformat(), "previous_phase_errors": state["phase_errors"]})
            state["phase_errors"] = []
        else:
            state = new_consistency_state("consistency-" + now.strftime("%Y%m%dT%H%M%S%fZ"), config, plan, cases, metadata)
            state["started_at_utc"] = now.isoformat()
            run_dir = RUNS / state["run_id"]
            run_dir.mkdir(parents=True, exist_ok=False)
        print(f"Run folder: {run_dir}", flush=True)
        save_consistency_reports(run_dir, state)
        preflight = LocalOllamaJudge(options=config["judge"]["options"], timeout=config["timeout_seconds"])
        try:
            validate_prompt_budgets(cases, preflight, config["thresholds"])
        finally:
            preflight.close()
        if any(row["generation"].get("status") != "completed" for row in state["results"]):
            ensure_idle(client)
            state["unloads"]["answer"] = False
            state["memory_snapshots"].append({"stage": "before_generation", **memory_snapshot()})
            try:
                for index, row in enumerate(state["results"], 1):
                    if row["generation"].get("status") == "completed":
                        continue
                    row["metrics"], row["checks"] = {}, {}
                    print(f"Generate {index}/{len(state['results'])}: {row['case']['case_id']} repeat {row['repeat']}", flush=True)
                    try:
                        row["generation"] = generate_answer(client, row["case"], config)
                        if row["generation"]["status"] == "completed":
                            row["checks"] = deterministic_checks(row["case"], row["generation"]["actual_response"])
                    except Exception as error:
                        row["generation"] = {"status": "error", "error": f"{type(error).__name__}: {error}", "actual_response": ""}
                    save_consistency_reports(run_dir, state)
            finally:
                _cleanup(state, cleanup, "answer")
                save_consistency_reports(run_dir, state)
        else:
            _cleanup(state, cleanup, "answer")

        pending = any(row["generation"].get("status") == "completed"
                      and any(row["metrics"].get(name, {}).get("status") != "completed" for name in METRICS)
                      for row in state["results"])
        if not state["phase_errors"] and pending:
            ensure_idle(client)
            judge = LocalOllamaJudge(options=config["judge"]["options"], timeout=config["timeout_seconds"])
            state["unloads"]["judge"] = False
            state["memory_snapshots"].append({"stage": "before_judging", **memory_snapshot()})
            try:
                for row in state["results"]:
                    if row["generation"].get("status") != "completed":
                        continue
                    test_case = make_test_case(row["case"], row["generation"]["actual_response"])
                    for name, metric in build_metrics(judge, config["thresholds"]).items():
                        if row["metrics"].get(name, {}).get("status") == "completed":
                            continue
                        print(f"Judge {row['case']['case_id']} repeat {row['repeat']} / {name}", flush=True)
                        start = len(judge.request_log)
                        try:
                            result = measure_metric(metric, test_case)
                        except Exception as error:
                            result = {"status": "error", "score": None, "passed": None, "error": f"{type(error).__name__}: {error}"}
                        result["requests"] = copy.deepcopy(judge.request_log[start:])
                        row["metrics"][name] = result
                        save_consistency_reports(run_dir, state)
            finally:
                try:
                    judge.close()
                except Exception as error:
                    state["phase_errors"].append(f"Judge client cleanup: {error}")
                _cleanup(state, cleanup, "judge")
                save_consistency_reports(run_dir, state)
        elif not state["phase_errors"]:
            _cleanup(state, cleanup, "judge")
        state["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        save_consistency_reports(run_dir, state)
        summary = summarize_consistency(state)
        print(json.dumps(summary, indent=2), flush=True)
        print(f"Readable report: {run_dir / 'summary.md'}", flush=True)
        if not summary["execution_complete"]:
            return 2
        return 1 if summary["quality_failed_trials"] else 0
    except Exception as error:
        if state is not None and run_dir is not None:
            state["phase_errors"].append(f"Orchestration: {type(error).__name__}: {error}")
            save_consistency_reports(run_dir, state)
        print(f"Consistency execution error: {type(error).__name__}: {error}", flush=True)
        return 2
    finally:
        if client is not None:
            client.close()
        if cleanup is not None:
            cleanup.close()
