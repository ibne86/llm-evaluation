"""Synthetic repeated-response tests; every model client below is a test double."""

import copy
import csv
import hashlib
import importlib.util
import json
from types import SimpleNamespace

import pytest

from llm_eval.config import ROOT, load_config
from llm_eval.consistency import make_plan, new_consistency_state, save_consistency_reports, summarize_consistency, validate_trials
from llm_eval.dataset import load_dataset
from llm_eval.ollama_client import deterministic_checks
from llm_eval.reporting import METRICS


@pytest.fixture
def repeated():
    case = {"case_id": "synthetic-library", "question": "When did the library open?",
            "context": "The library opened in 2018.", "expected_answers": ["2018"],
            "category": "answerable", "expects_abstention": False}
    config = load_config()
    plan, cases = make_plan({"cases": [case]}, 3, [case["case_id"]])
    state = new_consistency_state("synthetic-test-only", config, plan, cases, {})
    for row in state["results"]:
        set_response(row, "2018")
        row["metrics"] = {name: {"status": "completed", "score": 1.0, "passed": True,
                                 "threshold": config["thresholds"][name], "reason": "Synthetic test verdict."}
                          for name in METRICS}
    state["unloads"] = {"answer": True, "judge": True}
    return state


def set_response(row, text):
    row["generation"] = {"status": "completed", "actual_response": text,
                         "response_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    row["checks"] = deterministic_checks(row["case"], text)


def test_default_plan_uses_structural_coverage_and_preserves_original_cases():
    dataset = load_dataset(ROOT / "data/pilot.json")
    before = copy.deepcopy(dataset)
    plan, cases = make_plan(dataset)
    assert [case["category"] for case in cases] == ["answerable", "unanswerable", "instruction_in_context"]
    assert (plan["generation_requests"], plan["metric_evaluations"]) == (9, 27)
    assert cases[0]["case_id"] == dataset["cases"][0]["case_id"]
    assert dataset == before


@pytest.mark.parametrize("repeats", [0, 1, 6, True])
def test_repeat_count_is_bounded(repeats):
    with pytest.raises(ValueError, match="2 to 5"):
        make_plan({"cases": []}, repeats)


@pytest.mark.parametrize("ids", [[], ["missing"], ["synthetic-library", "synthetic-library"]])
def test_unknown_empty_or_duplicate_selections_are_rejected(repeated, ids):
    with pytest.raises(ValueError, match="Case IDs"):
        make_plan({"cases": repeated["cases"]}, 3, ids)


def test_an_identical_wrong_answer_is_stable_and_still_fails_quality(repeated):
    for row in repeated["results"]:
        set_response(row, "2019")
        row["metrics"]["correctness"].update(score=0.0, passed=False)
    summary = summarize_consistency(repeated)
    assert summary["execution_complete"]
    assert summary["exact_stable_cases"] == 1
    assert summary["quality_failed_trials"] == 3
    assert summary["cases_with_all_repeats_passing"] == 0
    assert summary["human_validation"]["agreement_rate"] is None


def test_different_wording_can_have_all_repeats_passing(repeated):
    set_response(repeated["results"][1], "The library opened in 2018.")
    case = summarize_consistency(repeated)["cases"][0]
    assert case["exact_stable"] is False
    assert case["normalized_stable"] is False
    assert case["all_repeats_quality_pass"] is True


def test_normalization_only_ignores_case_and_whitespace(repeated):
    set_response(repeated["results"][0], "  2018\n")
    assert summarize_consistency(repeated)["cases"][0]["normalized_stable"] is True
    assert summarize_consistency(repeated)["cases"][0]["exact_stable"] is False
    set_response(repeated["results"][0], "2018.")
    assert summarize_consistency(repeated)["cases"][0]["normalized_stable"] is False


def test_failed_request_cannot_inflate_stability_or_quality(repeated):
    repeated["results"][0].update(generation={"status": "error", "error": "timeout"}, checks={}, metrics={})
    summary = summarize_consistency(repeated)
    assert not summary["execution_complete"]
    assert summary["errors"] == 1
    assert summary["cases_with_all_generations"] == 0
    assert summary["cases"][0]["exact_stable"] is None
    assert summary["cases"][0]["all_repeats_quality_pass"] is None


def test_identical_answers_and_varying_judge_decisions_are_distinct(repeated):
    repeated["results"][1]["metrics"]["correctness"].update(score=0.0, passed=False)
    case = summarize_consistency(repeated)["cases"][0]
    assert case["exact_stable"] is True
    assert case["metric_decisions_stable"] is False
    assert case["all_repeats_quality_pass"] is False


@pytest.mark.parametrize("change", ["response", "context", "repeat", "missing_trial", "bad_score", "bad_pass"])
def test_modified_or_invalid_saved_trials_are_rejected(repeated, change):
    if change == "response":
        repeated["results"][0]["generation"]["actual_response"] = "edited"
    elif change == "context":
        repeated["results"][0]["case"]["context"] = "edited"
    elif change == "repeat":
        repeated["results"][0]["repeat"] = 2
    elif change == "missing_trial":
        repeated["results"].pop()
    elif change == "bad_score":
        repeated["results"][0]["metrics"]["correctness"]["score"] = float("nan")
    else:
        repeated["results"][0]["metrics"]["correctness"]["passed"] = False
    with pytest.raises(ValueError):
        validate_trials(repeated)


def test_missing_checks_and_failed_unload_prevent_execution_success(repeated):
    repeated["results"][0]["checks"] = {}
    summary = summarize_consistency(repeated)
    assert summary["incomplete"] == 1
    assert not summary["execution_complete"]
    repeated["results"][0]["checks"] = deterministic_checks(repeated["cases"][0], "2018")
    repeated["unloads"]["judge"] = False
    assert not summarize_consistency(repeated)["execution_complete"]


def test_reports_keep_every_response_and_metric_error(repeated, tmp_path):
    repeated["results"][1]["metrics"]["groundedness"] = {"status": "error", "error": "synthetic metric timeout"}
    save_consistency_reports(tmp_path, repeated)
    saved = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    with (tmp_path / "results.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 3 and [row["repeat"] for row in rows] == ["1", "2", "3"]
    assert rows[1]["groundedness_error"] == "synthetic metric timeout"
    assert "synthetic metric timeout" in (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert saved["summary"]["errors"] == 1


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    from llm_eval import consistency_runner as runner
    runtime = SimpleNamespace(events=[], loaded=set(), generations=0, measurements=0, generation_error=None,
                              metric_error_once=False, cleanup_error=False, wrong_scores=False, server="synthetic-server")
    config = load_config()
    runtime.case_id = load_dataset(ROOT / "data/pilot.json")["cases"][0]["case_id"]
    monkeypatch.setattr(runner, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(runner, "server_version", lambda host: runtime.server)
    monkeypatch.setattr(runner, "memory_snapshot", lambda: {"available_gib": None, "note": "synthetic test"})
    monkeypatch.setattr(runner, "validate_prompt_budgets", lambda cases, judge, thresholds: None)

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["trust_env"] is False
        def list(self):
            return SimpleNamespace(models=[SimpleNamespace(model=config[role]["model"], digest=f"synthetic-{role}") for role in ("answer", "judge")])
        def ps(self):
            return SimpleNamespace(models=[SimpleNamespace(model=name) for name in runtime.loaded])
        def chat(self, **kwargs):
            assert runtime.loaded <= {config["answer"]["model"]}
            assert len(kwargs["messages"]) == 2
            assert kwargs["options"] == config["answer"]["options"]
            runtime.loaded.add(kwargs["model"])
            runtime.generations += 1
            runtime.events.append("generate")
            error, runtime.generation_error = runtime.generation_error, None
            if error == "timeout":
                raise TimeoutError("synthetic generation timeout")
            if error == "interrupt":
                raise KeyboardInterrupt()
            return SimpleNamespace(done=True, done_reason="stop", message=SimpleNamespace(content="the state and its laws"),
                                   load_duration=0, prompt_eval_count=10, eval_count=6)
        def generate(self, model, keep_alive):
            assert keep_alive == 0
            if runtime.cleanup_error and model == config["answer"]["model"]:
                raise RuntimeError("synthetic unload failure")
            runtime.loaded.remove(model)
            runtime.events.append("unload-" + model)
        def close(self):
            pass

    class Judge:
        def __init__(self, options, timeout):
            self.request_log = []
        def close(self):
            pass

    class Metric:
        def __init__(self, judge, name, threshold):
            self.judge, self.name, self.threshold = judge, name, threshold
        def measure(self, test_case):
            assert runtime.loaded <= {config["judge"]["model"]}
            runtime.loaded.add(config["judge"]["model"])
            runtime.events.append("judge")
            runtime.measurements += 1
            if self.name == "correctness" and runtime.metric_error_once:
                runtime.metric_error_once = False
                raise TimeoutError("synthetic metric timeout")
            self.score = 0.0 if runtime.wrong_scores and self.name == "correctness" else 1.0
            self.reason = "Synthetic metric result for unit tests only."
            self.judge.request_log.append({"status": "completed", "prompt_sha256": "synthetic"})
        def is_successful(self):
            return self.score >= self.threshold

    monkeypatch.setattr(runner.ollama, "Client", Client)
    monkeypatch.setattr(runner, "LocalOllamaJudge", Judge)
    monkeypatch.setattr(runner, "build_metrics", lambda judge, thresholds: {name: Metric(judge, name, thresholds[name]) for name in METRICS})
    runtime.runner = runner
    runtime.folder = lambda: next(runner.RUNS.iterdir())
    runtime.saved = lambda: json.loads((runtime.folder() / "results.json").read_text(encoding="utf-8"))
    return runtime


def test_runner_uses_fresh_requests_and_unloads_before_judging(runtime):
    assert runtime.runner.run_consistency(repeats=2, case_ids=[runtime.case_id]) == 0
    assert (runtime.generations, runtime.measurements) == (2, 6)
    assert runtime.events.index("unload-qwen2.5:1.5b") < runtime.events.index("judge")
    assert not runtime.loaded
    assert runtime.saved()["summary"]["execution_complete"]
    assert len(runtime.saved()["results"]) == 2


def test_quality_failure_has_exit_one_and_a_completed_execution(runtime):
    runtime.wrong_scores = True
    assert runtime.runner.run_consistency(repeats=2, case_ids=[runtime.case_id]) == 1
    assert runtime.saved()["summary"]["execution_complete"]
    assert runtime.saved()["summary"]["quality_failed_trials"] == 2


def test_resume_retries_only_failed_metrics_without_regenerating_answers(runtime):
    runtime.metric_error_once = True
    assert runtime.runner.run_consistency(repeats=2, case_ids=[runtime.case_id]) == 2
    before = [row["generation"] for row in runtime.saved()["results"]]
    assert runtime.runner.run_consistency(resume=runtime.folder()) == 0
    assert (runtime.generations, runtime.measurements) == (2, 7)
    assert [row["generation"] for row in runtime.saved()["results"]] == before
    assert len(runtime.saved()["attempts"]) == 1


def test_generation_errors_remain_visible_and_resume_retries_them(runtime):
    runtime.generation_error = "timeout"
    assert runtime.runner.run_consistency(repeats=2, case_ids=[runtime.case_id]) == 2
    assert runtime.saved()["summary"]["cases"][0]["exact_stable"] is None
    assert runtime.runner.run_consistency(resume=runtime.folder()) == 0
    assert (runtime.generations, runtime.measurements) == (3, 6)


def test_unload_failure_prevents_loading_the_judge(runtime):
    runtime.cleanup_error = True
    assert runtime.runner.run_consistency(repeats=2, case_ids=[runtime.case_id]) == 2
    assert runtime.measurements == 0
    assert runtime.saved()["unloads"]["answer"] is False
    assert runtime.saved()["phase_errors"]


def test_changed_server_signature_cannot_silently_reuse_old_scores(runtime):
    assert runtime.runner.run_consistency(repeats=2, case_ids=[runtime.case_id]) == 0
    path = runtime.folder() / "results.json"
    before = path.read_bytes()
    runtime.server = "changed-server"
    assert runtime.runner.run_consistency(resume=runtime.folder()) == 2
    assert path.read_bytes() == before


def test_operator_interrupt_saves_progress_and_unloads_the_answer_model(runtime):
    runtime.generation_error = "interrupt"
    with pytest.raises(KeyboardInterrupt):
        runtime.runner.run_consistency(repeats=2, case_ids=[runtime.case_id])
    assert not runtime.loaded
    assert runtime.saved()["unloads"]["answer"] is True
    assert runtime.runner.run_consistency(resume=runtime.folder()) == 0


def test_plan_cli_makes_no_ollama_client(runtime, monkeypatch, capsys):
    def unexpected_client(**kwargs):
        pytest.fail("Preview must not contact Ollama.")
    monkeypatch.setattr(runtime.runner.ollama, "Client", unexpected_client)
    spec = importlib.util.spec_from_file_location("consistency_cli", ROOT / "scripts/run_consistency.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    assert cli.main(["--plan"]) == 0
    assert json.loads(capsys.readouterr().out)["generation_requests"] == 9
