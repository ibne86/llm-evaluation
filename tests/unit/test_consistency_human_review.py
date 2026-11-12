"""Synthetic labels exercise repeat identities; actual review labels remain empty."""

import copy
import hashlib
import importlib.util
import json
from urllib.parse import unquote

import pytest

from llm_eval.config import ROOT
from llm_eval.consistency import make_plan, new_consistency_state
from llm_eval.human_review import compare_review, comparison_markdown, create_review
from llm_eval.ollama_client import deterministic_checks
from llm_eval.reporting import METRICS


@pytest.fixture
def consistency_state():
    cases = [
        {
            "case_id": "synthetic-library", "question": "When did the library open?",
            "context": "The library opened in 2018.", "expected_answers": ["2018"],
            "category": "answerable", "expects_abstention": False,
            "source": {"dataset": "synthetic test fixture"},
        },
        {
            "case_id": "synthetic-count", "question": "How many records are on file?",
            "context": "The office keeps records; no total is given.",
            "expected_answers": ["INSUFFICIENT_CONTEXT"], "category": "unanswerable",
            "expects_abstention": True, "source": {"dataset": "synthetic test fixture"},
        },
    ]
    plan, selected = make_plan({"cases": cases}, repeats=3, case_ids=[case["case_id"] for case in cases])
    state = new_consistency_state(
        "synthetic-consistency-review-only",
        {"thresholds": dict(zip(METRICS, (0.7, 0.7, 0.8)))},
        plan, selected, {"case_count": 2, "trial_count": 6, "repeat_count": 3},
    )
    for row in state["results"]:
        response = "2018" if row["case"]["case_id"] == "synthetic-library" else "15"
        row["generation"] = {
            "status": "completed", "actual_response": response,
            "response_sha256": hashlib.sha256(response.encode()).hexdigest(),
        }
        row["checks"] = deterministic_checks(row["case"], response)
        for name in METRICS:
            passed = row["case"]["case_id"] == "synthetic-library"
            if row["repeat"] == 2 and name == "correctness":
                passed = False
            row["metrics"][name] = {
                "status": "completed", "score": float(passed),
                "threshold": state["config"]["thresholds"][name], "passed": passed,
                "reason": "Synthetic local-judge decision for an automated test.",
            }
    state["unloads"] = {"answer": True, "judge": True}
    return state


def label(packet, index, metric, verdict):
    packet["reviewer"] = "synthetic-human-reviewer"
    packet["prior_exposure"] = "scores_or_findings_seen"
    packet["reviews"][index]["decisions"][metric] = {
        "verdict": verdict, "reason": "Synthetic rating, never a real human judgment.",
    }


def label_all(packet):
    for index in range(len(packet["reviews"])):
        for name in METRICS:
            label(packet, index, name, "pass")


def test_packet_preserves_every_repeat_without_judge_information(consistency_state):
    before = copy.deepcopy(consistency_state)
    packet = create_review(consistency_state)
    assert packet["schema_version"] == 2
    assert packet["source_run_type"] == "response_consistency"
    assert (packet["case_count"], packet["trial_count"], packet["repeats"]) == (2, 6, 3)
    assert len({row["trial_id"] for row in packet["reviews"]}) == 6
    for reviewed, original in zip(packet["reviews"], consistency_state["results"]):
        assert reviewed["case_id"] == original["case"]["case_id"]
        assert reviewed["repeat"] == original["repeat"]
        assert reviewed["trial_id"] == f"{reviewed['case_id']}::repeat-{reviewed['repeat']}"
        assert reviewed["actual_response"] == original["generation"]["actual_response"]
        assert not {"score", "metrics", "judge_reason", "checks"} & reviewed.keys()
        assert all(decision == {"verdict": None, "reason": ""} for decision in reviewed["decisions"].values())
    assert consistency_state == before


def test_real_nine_trial_packet_has_twenty_seven_unreviewed_decisions():
    state = json.loads((ROOT / "results/examples/consistency-results.json").read_text(encoding="utf-8-sig"))
    packet = create_review(state)
    report = compare_review(state, packet)
    assert report["status"] == "not_started"
    assert report["selected_cases"] == 3 and report["selected_trials"] == 9
    assert report["fully_reviewed_cases"] == report["fully_reviewed_trials"] == 0
    assert report["possible_pairs"] == report["unreviewed_decisions"] == 27
    assert report["paired_decisions"] == 0 and report["agreement_rate"] is None
    assert len(report["comparisons"]) == 27
    assert "fully reviewed trials: 0/9" in comparison_markdown(report)


def test_identical_answers_keep_repeat_specific_human_and_judge_decisions(consistency_state):
    packet = create_review(consistency_state)
    assert packet["reviews"][0]["actual_response"] == packet["reviews"][1]["actual_response"]
    label(packet, 0, "correctness", "pass")
    label(packet, 1, "correctness", "fail")
    report = compare_review(consistency_state, packet)
    assert report["status"] == "partial"
    assert report["paired_decisions"] == report["agreements"] == 2
    assert report["unreviewed_decisions"] == 16
    decisions = [row for row in report["comparisons"]
                 if row["case_id"] == "synthetic-library" and row["metric"] == "correctness"]
    assert [row["human_verdict"] for row in decisions] == ["pass", "fail", None]
    assert [row["judge_verdict"] for row in decisions] == ["pass", "fail", "pass"]
    assert "| Question | Repeat | Metric | Human | Local judge |" in comparison_markdown(report)


def test_complete_trial_review_has_correct_denominators_and_disagreement_identities(consistency_state):
    packet = create_review(consistency_state)
    label_all(packet)
    report = compare_review(consistency_state, packet)
    assert report["status"] == "complete"
    assert report["selected_cases"] == report["fully_reviewed_cases"] == 2
    assert report["selected_trials"] == report["fully_reviewed_trials"] == 6
    assert report["possible_pairs"] == report["paired_decisions"] == 18
    assert report["agreements"] == 8 and report["agreement_rate"] == 8 / 18
    assert len(report["disagreements"]) == 10
    assert any(row["case_id"] == "synthetic-library" and row["repeat"] == 2
               and row["metric"] == "correctness" for row in report["disagreements"])
    assert all("trial_id" in row and "repeat" in row for row in report["disagreements"])
    assert "synthetic-library / repeat 2 / correctness" in comparison_markdown(report)


def test_question_is_complete_only_when_all_its_trials_are_reviewed(consistency_state):
    packet = create_review(consistency_state)
    for index in range(3):
        for name in METRICS:
            label(packet, index, name, "pass")
    report = compare_review(consistency_state, packet)
    assert report["status"] == "partial"
    assert report["fully_reviewed_trials"] == 3 and report["fully_reviewed_cases"] == 1
    assert report["paired_decisions"] == report["unreviewed_decisions"] == 9


def test_reordered_review_rows_still_match_the_correct_trial(consistency_state):
    packet = create_review(consistency_state)
    label_all(packet)
    expected = compare_review(consistency_state, packet)
    packet["reviews"].reverse()
    report = compare_review(consistency_state, packet)
    assert report["comparisons"] == expected["comparisons"]
    assert report["human_review_sha256"] != expected["human_review_sha256"]


def test_uncertain_repeat_rating_is_excluded_and_reported(consistency_state):
    packet = create_review(consistency_state)
    label(packet, 1, "correctness", "uncertain")
    report = compare_review(consistency_state, packet)
    assert report["status"] == "partial"
    assert report["uncertain_decisions"] == 1 and report["unreviewed_decisions"] == 17
    assert report["paired_decisions"] == 0 and report["agreement_rate"] is None


@pytest.mark.parametrize("change", [
    "duplicate", "missing_trial", "repeat_bool", "repeat_number", "missing_repeat",
    "trial_id", "response", "source_type", "rubric",
])
def test_changed_review_identity_or_evidence_is_rejected(consistency_state, change):
    packet = create_review(consistency_state)
    if change == "duplicate":
        packet["reviews"][1] = copy.deepcopy(packet["reviews"][0])
    elif change == "missing_trial":
        packet["reviews"].pop()
    elif change == "repeat_bool":
        packet["reviews"][0]["repeat"] = True
    elif change == "repeat_number":
        packet["reviews"][0]["repeat"] = 2
    elif change == "missing_repeat":
        del packet["reviews"][0]["repeat"]
    elif change == "trial_id":
        packet["reviews"][0]["trial_id"] = "a different trial"
    elif change == "response":
        packet["reviews"][0]["actual_response"] = "2019"
    elif change == "source_type":
        packet["source_run_type"] = "development_pilot"
    else:
        packet["rubric"]["correctness"] = "Pass every answer."
    with pytest.raises(ValueError):
        compare_review(consistency_state, packet)


@pytest.mark.parametrize("change", [
    "missing_trial", "duplicate_trial", "repeat_bool", "schema_bool", "case_count",
    "trial_count", "repeat_count", "selection_hash", "response_hash",
    "metric_error", "incomplete_generation", "wrong_run_type",
])
def test_incomplete_or_changed_consistency_source_is_rejected(consistency_state, change):
    state = copy.deepcopy(consistency_state)
    if change == "missing_trial":
        state["results"].pop()
    elif change == "duplicate_trial":
        state["results"][1] = copy.deepcopy(state["results"][0])
    elif change == "repeat_bool":
        state["results"][0]["repeat"] = True
    elif change == "schema_bool":
        state["schema_version"] = True
    elif change in ("case_count", "trial_count", "repeat_count"):
        state["metadata"][change] += 1
    elif change == "selection_hash":
        state["metadata"]["selection_sha256"] = "wrong"
    elif change == "response_hash":
        state["results"][0]["generation"]["response_sha256"] = "wrong"
    elif change == "metric_error":
        state["results"][0]["metrics"]["correctness"]["status"] = "error"
    elif change == "incomplete_generation":
        state["results"][0]["generation"]["status"] = "pending"
    else:
        state["run_type"] = "unsupported"
    with pytest.raises(ValueError):
        create_review(state)


def test_changed_saved_judge_evidence_invalidates_the_packet(consistency_state):
    packet = create_review(consistency_state)
    consistency_state["results"][0]["metrics"]["correctness"]["reason"] = "Changed explanation."
    with pytest.raises(ValueError, match="source, schema or rubric"):
        compare_review(consistency_state, packet)


def test_trial_ratings_require_reasons_by_default_and_allow_explicit_optional_policy(consistency_state):
    packet = create_review(consistency_state)
    label(packet, 0, "correctness", "pass")
    packet["reviews"][0]["decisions"]["correctness"]["reason"] = ""
    with pytest.raises(ValueError, match="needs a reason"):
        compare_review(consistency_state, packet)
    packet = create_review(consistency_state, reason_policy="optional")
    label(packet, 0, "correctness", "pass")
    packet["reviews"][0]["decisions"]["correctness"]["reason"] = ""
    report = compare_review(consistency_state, packet)
    assert report["paired_decisions"] == 1
    assert report["reason_coverage"]["missing_written_reasons"] == 1


def test_cli_prepares_and_compares_consistency_trials_without_replacing_inputs(consistency_state, tmp_path, capsys):
    spec = importlib.util.spec_from_file_location("consistency_review_cli", ROOT / "scripts/review_judge.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    source = tmp_path / "consistency results.json"
    source.write_text(json.dumps(consistency_state), encoding="utf-8")
    before = source.read_bytes()
    review = tmp_path / "human.json"
    prepare = ["prepare", "--results", str(source), "--output", str(review)]
    assert cli.main(prepare) == 0
    assert "Prepared 6 trials across 2 questions" in capsys.readouterr().out
    packet = json.loads(review.read_text())
    label_all(packet)
    review.write_text(json.dumps(packet), encoding="utf-8")
    submitted = review.read_bytes()
    folder = tmp_path / "comparison"
    compare = ["compare", "--results", str(source), "--review", str(review), "--output-dir", str(folder)]
    assert cli.main(compare) == 0
    report = json.loads((folder / "comparison.json").read_text())
    assert report["evaluation_type"] == "human_vs_local_judge_consistency"
    assert report["paired_decisions"] == 18 and report["agreements"] == 8
    assert len({row["trial_id"] for row in report["comparisons"]}) == 6
    for target in report["evidence_files"].values():
        assert (folder / unquote(target)).resolve().exists()
    assert cli.main(prepare) == 2 and cli.main(compare) == 2
    assert source.read_bytes() == before and review.read_bytes() == submitted
