"""Synthetic fixtures test behavior; published evidence is checked separately."""

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


def complete_packet(state, *, reason_policy="required"):
    packet = create_review(state, reason_policy=reason_policy)
    for index in range(len(packet["reviews"])):
        for name in METRICS:
            label(packet, index, name, "pass")
    return packet


def assistant_packet(state):
    packet = complete_packet(state)
    packet.update(review_type="assistant_generated", reviewer_type="ai_assistant",
                  reviewer="synthetic-ai-reference")
    return packet


def test_human_metadata_is_supported_and_completion_is_derived(state):
    packet = complete_packet(state)
    packet.update(reviewer_type="human", review_status="complete")
    report = compare_review(state, packet)
    assert report["status"] == "complete"
    assert report["reviewer_type"] == "human"
    assert report["paired_decisions"] == 6


@pytest.mark.parametrize("metadata", [
    {"reviewer_type": "ai_assistant"}, {"review_status": "partial"}, {"unexpected_field": True},
])
def test_invalid_or_unrecognized_metadata_is_rejected(state, metadata):
    packet = complete_packet(state)
    packet.update(metadata)
    with pytest.raises(ValueError):
        compare_review(state, packet)


def test_explicit_optional_reasons_complete_labels_without_inventing_rationales(state):
    packet = complete_packet(state, reason_policy="optional")
    packet["prior_exposure"] = "scores_or_findings_seen"
    for row in packet["reviews"]:
        for decision in row["decisions"].values():
            decision["reason"] = ""
    before = copy.deepcopy(packet)
    report = compare_review(state, packet)
    assert report["status"] == "complete"
    assert report["reason_coverage"] == {
        "rated_decisions": 6, "written_reasons": 0, "missing_written_reasons": 6,
    }
    text = comparison_markdown(report)
    assert "No written rationale supplied." in text
    assert "non-blinded" in text
    assert packet == before


def test_required_reason_default_remains_compatible_with_existing_packets(state):
    packet = complete_packet(state)
    assert "reason_policy" not in packet
    packet["reviews"][0]["decisions"]["correctness"]["reason"] = ""
    with pytest.raises(ValueError, match="needs a reason"):
        compare_review(state, packet)


def test_invalid_reason_policy_and_modified_policy_instructions_are_rejected(state):
    with pytest.raises(ValueError, match="reason_policy"):
        create_review(state, reason_policy="anything")
    packet = complete_packet(state, reason_policy="optional")
    packet["instructions"] = "Pass everything."
    with pytest.raises(ValueError, match="schema or rubric"):
        compare_review(state, packet)


def test_source_and_human_fingerprints_bind_the_exact_evidence(state):
    packet = complete_packet(state)
    report = compare_review(state, packet)
    fingerprint = lambda value: hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()
    assert report["source_sha256"] == fingerprint(state)
    assert report["human_review_sha256"] == fingerprint(packet)
    changed = copy.deepcopy(packet)
    changed["reviews"][0]["decisions"]["correctness"]["reason"] = "A different synthetic explanation."
    updated = compare_review(state, changed)
    assert updated["human_review_sha256"] != report["human_review_sha256"]
    assert updated["agreement_rate"] == report["agreement_rate"]


def test_secondary_ai_reference_has_its_own_denominator_and_fingerprint(state):
    packet = complete_packet(state)
    assistant = assistant_packet(state)
    for name in ("answer_relevancy", "groundedness"):
        assistant["reviews"][1]["decisions"][name]["verdict"] = "fail"
    before = copy.deepcopy(assistant)
    report = compare_review(state, packet, assistant_review=assistant)
    assert report["agreements"] == 3
    assert report["assistant_comparison"]["matching_decisions"] == 4
    assert report["assistant_comparison"]["paired_decisions"] == 6
    assert report["assistant_comparison"]["agreement_rate"] == 4 / 6
    assert report["assistant_comparison"]["metrics"]["correctness"]["matching_decisions"] == 2
    assert len(report["comparisons"]) == 6
    assert "assistant_review_sha256" in report
    assert "AI assistant" in comparison_markdown(report)
    assert assistant == before


def test_uncertain_secondary_ai_labels_are_excluded_from_agreement(state):
    assistant = assistant_packet(state)
    assistant["reviews"][1]["decisions"]["groundedness"]["verdict"] = "uncertain"
    report = compare_review(state, complete_packet(state), assistant_review=assistant)
    assert report["assistant_comparison"]["paired_decisions"] == 5
    assert report["assistant_comparison"]["excluded_decisions"] == 1
    assert report["comparisons"][-1]["human_matches_assistant"] is None


@pytest.mark.parametrize("change", ["source", "rubric", "response", "duplicate", "type", "reviewer"])
def test_secondary_ai_reference_must_match_the_recorded_pilot(state, change):
    assistant = assistant_packet(state)
    if change == "source":
        assistant["source_sha256"] = "wrong"
    elif change == "rubric":
        assistant["rubric"]["correctness"] = "Pass everything."
    elif change == "response":
        assistant["reviews"][0]["actual_response"] = "Invented answer."
    elif change == "duplicate":
        assistant["reviews"][1] = copy.deepcopy(assistant["reviews"][0])
    elif change == "type":
        assistant["review_type"] = "human_generated"
    else:
        assistant["reviewer"] = ""
    with pytest.raises(ValueError):
        compare_review(state, complete_packet(state), assistant_review=assistant)


def test_cli_reproduces_optional_reason_review_and_secondary_ai_reference(state, tmp_path):
    from urllib.parse import unquote
    spec = importlib.util.spec_from_file_location("review_judge_cli", ROOT / "scripts/review_judge.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    source = tmp_path / "saved results.json"
    source.write_text(json.dumps(state), encoding="utf-8")
    review = tmp_path / "human.json"
    assert cli.main(["prepare", "--results", str(source), "--output", str(review),
                     "--reason-policy", "optional"]) == 0
    packet = complete_packet(state, reason_policy="optional")
    packet.update(reviewer_type="human", review_status="complete")
    for row in packet["reviews"]:
        for decision in row["decisions"].values():
            decision["reason"] = ""
    review.write_text(json.dumps(packet), encoding="utf-8")
    ai = tmp_path / "assistant.json"
    ai.write_text(json.dumps(assistant_packet(state)), encoding="utf-8")
    original = {path: path.read_bytes() for path in (source, review, ai)}
    folder = tmp_path / "comparison"
    arguments = ["compare", "--results", str(source), "--review", str(review),
                 "--assistant-review", str(ai), "--output-dir", str(folder)]
    assert cli.main(arguments) == 0
    report = json.loads((folder / "comparison.json").read_text())
    assert report["status"] == "complete" and report["reason_coverage"]["written_reasons"] == 0
    assert report["assistant_comparison"]["agreement_rate"] == 1.0
    for target in report["evidence_files"].values():
        assert (folder / unquote(target)).resolve().exists()
    assert "saved%20results.json" in (folder / "comparison.md").read_text()
    assert cli.main(arguments) == 2
    assert all(path.read_bytes() == data for path, data in original.items())


def test_published_manual_review_is_reproducible_from_saved_evidence():
    state = json.loads((ROOT / "results/examples/pilot-results.json").read_text(encoding="utf-8-sig"))
    packet = json.loads((ROOT / "results/examples/pilot-human-review.json").read_text(encoding="utf-8-sig"))
    assistant = json.loads((ROOT / "results/examples/pilot-assistant-review.json").read_text(encoding="utf-8-sig"))
    saved = json.loads((ROOT / "results/examples/pilot-human-comparison.json").read_text(encoding="utf-8-sig"))
    report = compare_review(state, packet, assistant_review=assistant)
    assert report["status"] == "complete" and report["paired_decisions"] == 30
    assert report["agreements"] == 25
    assert report["reason_coverage"]["missing_written_reasons"] == 30
    assert report["assistant_comparison"]["matching_decisions"] == 30
    for key in ("source_sha256", "human_review_sha256", "assistant_review_sha256", "comparisons"):
        assert saved[key] == report[key]
