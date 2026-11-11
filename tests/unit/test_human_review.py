"""All ratings below are synthetic test fixtures, never real human validation."""

import copy
import hashlib
import importlib.util
import json
import pytest

from llm_eval.config import ROOT
from llm_eval.human_review import compare_review, comparison_markdown, create_review
from llm_eval.reporting import METRICS


@pytest.fixture
def state():
    thresholds = dict(zip(METRICS, (0.7, 0.7, 0.8)))
    rows = []
    for index in range(2):
        rows.append({
            "case": {"case_id": f"synthetic-{index}", "question": "When did the library open?",
                     "context": "The library opened in 2018.", "expected_answers": ["2018"],
                     "category": "answerable", "expects_abstention": False},
            "generation": {"status": "completed", "actual_response": "2018",
                           "response_sha256": hashlib.sha256(b"2018").hexdigest()},
            "metrics": {name: {"status": "completed", "score": float(index == 0),
                               "threshold": thresholds[name], "passed": index == 0,
                               "reason": "Synthetic judge reason."} for name in METRICS},
        })
    return {"run_id": "synthetic-test-only", "metadata": {"case_count": 2},
            "config": {"thresholds": thresholds}, "results": rows}


def label(packet, case_index, metric, verdict):
    packet["reviewer"] = "synthetic-test-reviewer"
    packet["prior_exposure"] = "none"
    packet["reviews"][case_index]["decisions"][metric] = {
        "verdict": verdict, "reason": "Synthetic decision for an automated test."
    }


def test_unlabelled_packet_omits_judge_information_and_does_not_mutate_source(state):
    before = copy.deepcopy(state)
    packet = create_review(state)
    text = json.dumps(packet)
    assert "Synthetic judge reason" not in text
    assert all("score" not in row and "metrics" not in row for row in packet["reviews"])
    assert all(decision["verdict"] is None for row in packet["reviews"] for decision in row["decisions"].values())
    assert state == before


def test_no_human_labels_means_no_agreement_rate(state):
    report = compare_review(state, create_review(state))
    assert report["status"] == "not_started"
    assert report["paired_decisions"] == 0
    assert report["agreement_rate"] is None
    assert all(metric["agreement_rate"] is None for metric in report["metrics"].values())
    assert "not available" in comparison_markdown(report)


def test_partial_and_uncertain_reviews_have_explicit_denominators(state):
    packet = create_review(state)
    label(packet, 0, "correctness", "pass")
    label(packet, 1, "correctness", "pass")
    label(packet, 0, "groundedness", "uncertain")
    before = copy.deepcopy(packet)
    report = compare_review(state, packet)
    assert report["status"] == "partial"
    assert report["paired_decisions"] == 2
    assert report["unreviewed_decisions"] == 3
    assert report["uncertain_decisions"] == 1
    assert report["agreement_rate"] == 0.5
    assert report["metrics"]["correctness"]["human_pass_judge_fail"] == 1
    assert report["metrics"]["groundedness"]["agreement_rate"] is None
    assert report["fully_reviewed_cases"] == 0
    assert report["disagreements"][0]["case_id"] == "synthetic-1"
    assert packet == before


def test_complete_review_can_have_disagreements_and_reordered_rows(state):
    packet = create_review(state)
    for index in range(2):
        for name in METRICS:
            label(packet, index, name, "pass")
    packet["reviews"].reverse()
    packet["prior_exposure"] = "scores_or_findings_seen"
    report = compare_review(state, packet)
    assert report["status"] == "complete"
    assert report["fully_reviewed_cases"] == 2
    assert report["agreement_rate"] == 0.5
    assert len(report["disagreements"]) == 3
    assert report["prior_exposure"] == "scores_or_findings_seen"


@pytest.mark.parametrize("change", ["response", "source_score", "rubric", "duplicate", "missing_case", "missing_metric"])
def test_mismatched_evidence_and_incomplete_review_schema_are_rejected(state, change):
    packet = create_review(state)
    if change == "response":
        packet["reviews"][0]["actual_response"] = "2019"
    elif change == "source_score":
        state["results"][0]["metrics"]["correctness"]["reason"] = "Changed source judge explanation."
    elif change == "rubric":
        packet["rubric"]["correctness"] = "Pass everything."
    elif change == "duplicate":
        packet["reviews"][1] = copy.deepcopy(packet["reviews"][0])
    elif change == "missing_case":
        packet["reviews"].pop()
    else:
        del packet["reviews"][0]["decisions"]["correctness"]
    with pytest.raises(ValueError):
        compare_review(state, packet)


@pytest.mark.parametrize("change", ["bad_label", "no_reason", "no_reviewer", "no_exposure"])
def test_human_labels_require_valid_values_and_provenance(state, change):
    packet = create_review(state)
    label(packet, 0, "correctness", "pass")
    if change == "bad_label":
        packet["reviews"][0]["decisions"]["correctness"]["verdict"] = True
    elif change == "no_reason":
        packet["reviews"][0]["decisions"]["correctness"]["reason"] = " "
    elif change == "no_reviewer":
        packet["reviewer"] = " "
    else:
        packet["prior_exposure"] = None
    with pytest.raises(ValueError):
        compare_review(state, packet)


@pytest.mark.parametrize("change", ["generation_error", "metric_error", "nan_score", "boolean_score", "wrong_pass", "wrong_threshold", "wrong_hash"])
def test_invalid_judge_source_is_never_paired_as_a_quality_failure(state, change):
    metric = state["results"][0]["metrics"]["correctness"]
    if change == "generation_error":
        state["results"][0]["generation"]["status"] = "error"
    elif change == "metric_error":
        metric["status"] = "error"
    elif change == "nan_score":
        metric["score"] = float("nan")
    elif change == "boolean_score":
        metric["score"] = True
    elif change == "wrong_pass":
        metric["passed"] = False
    elif change == "wrong_threshold":
        metric["threshold"] = 0.6
    else:
        state["results"][0]["generation"]["response_sha256"] = "wrong"
    with pytest.raises(ValueError):
        create_review(state)


def test_actual_pilot_template_has_ten_cases_and_thirty_unlabelled_decisions():
    state = json.loads((ROOT / "results/examples/pilot-results.json").read_text(encoding="utf-8-sig"))
    packet = create_review(state)
    report = compare_review(state, packet)
    assert report["selected_cases"] == 10
    assert report["possible_pairs"] == 30
    assert report["unreviewed_decisions"] == 30
    assert report["agreement_rate"] is None


def test_cli_keeps_existing_reviews_and_results_unchanged(state, tmp_path):
    spec = importlib.util.spec_from_file_location("review_judge_cli", ROOT / "scripts/review_judge.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    source = tmp_path / "results.json"
    source.write_text(json.dumps(state), encoding="utf-8")
    original = source.read_bytes()
    packet = tmp_path / "review.json"
    assert cli.main(["prepare", "--results", str(source), "--output", str(packet)]) == 0
    assert cli.main(["prepare", "--results", str(source), "--output", str(packet)]) == 2
    report_dir = tmp_path / "comparison"
    arguments = ["compare", "--results", str(source), "--review", str(packet), "--output-dir", str(report_dir)]
    assert cli.main(arguments) == 0
    assert json.loads((report_dir / "comparison.json").read_text())["agreement_rate"] is None
    assert cli.main(arguments) == 2
    assert cli.main(["prepare", "--results", str(source), "--output", str(source)]) == 2
    assert source.read_bytes() == original


def test_cli_reports_bad_input_without_creating_comparison(tmp_path):
    spec = importlib.util.spec_from_file_location("review_judge_cli", ROOT / "scripts/review_judge.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    source = tmp_path / "bad.json"
    source.write_text("not JSON", encoding="utf-8")
    assert cli.main(["prepare", "--results", str(source), "--output", str(tmp_path / "review.json")]) == 2
    assert not (tmp_path / "review.json").exists()
