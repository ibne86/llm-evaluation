import copy
import hashlib
from types import SimpleNamespace

import pytest

from llm_eval.config import ROOT, load_config
from llm_eval.dataset import ABSTENTION, load_dataset
from llm_eval.judge import LocalOllamaJudge
from llm_eval.metrics import build_metrics, make_test_case, measure_metric, validate_prompt_budgets
from llm_eval.ollama_client import deterministic_checks, generate_answer, messages_for, unload_model
from llm_eval.reporting import case_outcome, save_reports, summarize
from llm_eval.runner import new_state, validate_saved_cases


@pytest.fixture
def pilot():
    return load_dataset(ROOT / "data" / "pilot.json")


def test_context_and_quoted_attack_stay_in_user_data(pilot):
    case = pilot["cases"][-1]
    messages = messages_for(case)
    assert messages[0]["role"] == "system"
    assert "23:59" not in messages[0]["content"]
    assert case["context"] in messages[1]["content"]
    assert case["question"] in messages[1]["content"]


def test_deterministic_abstention_is_an_explicit_format_contract(pilot):
    case = next(case for case in pilot["cases"] if case["expects_abstention"])
    assert deterministic_checks(case, "  " + ABSTENTION + "\n")["abstention_contract"]
    assert not deterministic_checks(case, ABSTENTION + ".")["abstention_contract"]
    assert not deterministic_checks(pilot["cases"][0], ABSTENTION)["abstention_contract"]


@pytest.mark.parametrize("content,reason", [("", "stop"), ("partial text", "length")])
def test_empty_or_truncated_generation_is_recorded_as_error(pilot, content, reason):
    class Client:
        def chat(self, **kwargs):
            return SimpleNamespace(done=True, done_reason=reason, message=SimpleNamespace(content=content), load_duration=0, prompt_eval_count=30, eval_count=5)
    result = generate_answer(Client(), pilot["cases"][0], load_config())
    assert result["status"] == "error"
    assert result["actual_response"] == content


def test_unloading_does_not_stop_other_models():
    class Client:
        names = ["our-model", "unrelated-model"]
        def ps(self):
            return SimpleNamespace(models=[SimpleNamespace(model=name) for name in self.names])
        def generate(self, model, keep_alive):
            assert keep_alive == 0
            self.names.remove(model)
    client = Client()
    assert unload_model(client, "our-model")
    assert client.names == ["unrelated-model"]


def test_all_actual_pilot_prompts_fit_the_recorded_judge_profile(pilot):
    config = load_config()
    judge = LocalOllamaJudge(options=config["judge"]["options"])
    try:
        validate_prompt_budgets(pilot["cases"], judge, config["thresholds"])
        assert judge.generation_kwargs["num_ctx"] == 4096
    finally:
        judge.close()


@pytest.mark.parametrize("raw_score,normalized", [(10, 1.0), (0, 0.0)])
def test_geval_uses_local_schema_results_and_normalizes_scores(pilot, monkeypatch, raw_score, normalized):
    judge = LocalOllamaJudge(options=load_config()["judge"]["options"])
    try:
        def generate(prompt, schema=None, **kwargs):
            return schema.model_validate({"score": raw_score, "reason": "The supplied answer matches the control decision."}), 0.0
        monkeypatch.setattr(judge, "generate", generate)
        metric = build_metrics(judge, load_config()["thresholds"])["correctness"]
        result = measure_metric(metric, make_test_case(pilot["cases"][0], "an answer"))
        assert result["score"] == normalized
    finally:
        judge.close()


@pytest.mark.parametrize("score", [float("nan"), 1.1, -0.1])
def test_invalid_normalized_scores_do_not_pass(score):
    metric = SimpleNamespace(measure=lambda case: None, score=score, reason="A reason", threshold=0.7, is_successful=lambda: True)
    with pytest.raises(ValueError, match="0..1"):
        measure_metric(metric, None)


def completed_result(case):
    return {
        "case": case, "generation": {"status": "completed", "actual_response": "x", "response_sha256": hashlib.sha256(b"x").hexdigest()},
        "checks": {"nonempty_response": True, "abstention_contract": True},
        "metrics": {name: {"status": "completed", "score": 1.0, "passed": True, "reason": "supported"} for name in ("answer_relevancy", "correctness", "groundedness")},
    }


def test_quality_failures_are_distinct_from_execution_errors(pilot, tmp_path):
    good, bad, error = [completed_result(case) for case in pilot["cases"][:3]]
    bad["metrics"]["correctness"].update(score=0.0, passed=False)
    error["metrics"]["groundedness"] = {"status": "error", "error": "timeout", "score": None, "passed": None}
    state = {"config": load_config(), "metadata": {"case_count": 3}, "results": [good, bad, error], "unloads": {"answer": True, "judge": True}, "phase_errors": []}
    summary = summarize(state)
    assert (summary["passed"], summary["failed"], summary["errors"]) == (1, 1, 1)
    assert not summary["execution_complete"]
    assert summary["human_validation"]["agreement_rate"] is None
    save_reports(tmp_path, state)
    assert "timeout" in (tmp_path / "summary.md").read_text(encoding="utf-8")


def test_quality_failure_does_not_make_a_completed_run_incomplete(pilot):
    row = completed_result(pilot["cases"][0])
    row["checks"]["abstention_contract"] = False
    state = {"metadata": {"case_count": 1}, "results": [row], "unloads": {"answer": True, "judge": True}, "phase_errors": []}
    assert summarize(state)["execution_complete"]
    assert summarize(state)["failed"] == 1
    state["unloads"]["judge"] = False
    assert not summarize(state)["execution_complete"]


def test_missing_checks_cannot_be_reported_as_passed(pilot):
    result = completed_result(pilot["cases"][0])
    result["checks"] = {}
    assert case_outcome(result) == "incomplete"


def test_changed_saved_responses_or_case_inputs_are_rejected(pilot):
    saved = {"results": [completed_result(case) for case in pilot["cases"]]}
    validate_saved_cases(saved, pilot["cases"])
    saved["results"][0]["generation"]["actual_response"] = "edited"
    with pytest.raises(ValueError, match="modified"):
        validate_saved_cases(saved, pilot["cases"])


def test_reusing_responses_never_reuses_old_judge_scores(pilot):
    previous = {"run_id": "old", "metadata": {"generation_signature": "same"}, "results": [completed_result(case) for case in pilot["cases"]]}
    state = new_state(load_config(), pilot, {"generation_signature": "same", "case_count": 10}, previous)
    assert all(row["generation"]["status"] == "completed" and not row["metrics"] for row in state["results"])
    with pytest.raises(ValueError, match="different"):
        new_state(load_config(), pilot, {"generation_signature": "changed"}, previous)
