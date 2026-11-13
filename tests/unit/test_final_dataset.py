import copy
import importlib.util
import json
import shutil
from collections import Counter

import pytest

from llm_eval.config import ROOT, load_config
from llm_eval.dataset import ABSTENTION, load_dataset, sha256_bytes
from llm_eval.evaluation_freeze import EVIDENCE_FILES, FROZEN_TEXT_FILES, json_sha256
from llm_eval.final_dataset import CATEGORIES, load_final_dataset, prepare_final_dataset, read_json, validate_final_dataset


@pytest.fixture
def inputs():
    return (
        read_json(ROOT / "data/final.json"), read_json(ROOT / "data/pilot.json"),
        read_json(ROOT / "data/final-custom-cases.json"), json_sha256(ROOT / "evaluation-freeze.json"),
    )


def test_published_inputs_are_fifty_separate_cases_bound_to_the_baseline(inputs):
    _, pilot, custom, freeze = inputs
    final = load_final_dataset(ROOT / "data/final.json", pilot, custom, freeze)
    assert Counter(case["category"] for case in final["cases"]) == CATEGORIES
    assert len({case["context"] for case in final["cases"]}) == 50
    assert sum(case["expects_abstention"] for case in final["cases"]) == 15
    assert final["metadata"]["selection"]["selected_squad_articles"] == 35
    squad = [case for case in final["cases"] if case["source"]["dataset"] == "SQuAD 2.0"]
    assert len({case["source"]["original_id"] for case in squad}) == 40
    assert not ({case["context"] for case in final["cases"]} & {case["context"] for case in pilot["cases"]})
    assert any(len(case["expected_answers"]) > 1 for case in squad)


def test_all_fifty_prompts_fit_the_unchanged_profiles_without_a_model_request(inputs):
    from llm_eval.judge import LocalOllamaJudge
    from llm_eval.metrics import validate_prompt_budgets
    from llm_eval.ollama_client import messages_for

    config = load_config()
    cases = inputs[0]["cases"]
    for case in cases:
        budget = sum(len(message["content"].encode("utf-8")) for message in messages_for(case))
        assert budget + config["answer"]["options"]["num_predict"] + 96 <= config["answer"]["options"]["num_ctx"]
    judge = LocalOllamaJudge(options=config["judge"]["options"])
    try:
        validate_prompt_budgets(cases, judge, config["thresholds"])
        assert judge.request_log == []
    finally:
        judge.close()


def test_the_existing_pilot_loader_still_rejects_final_inputs():
    with pytest.raises(ValueError, match="pilot only"):
        load_dataset(ROOT / "data/final.json")


def synthetic_source(pilot, article_count=40):
    pilot = copy.deepcopy(pilot)
    articles = []
    for index in range(article_count):
        year = str(1800 + index)
        context = f"Archive {index} opened in {year}. " + "Its collection contains maps, letters and photographs for visitors to study. " * 3
        answers = [{"text": year, "answer_start": context.index(year)}]
        articles.append({"title": f"Synthetic article {index}", "paragraphs": [{"context": context, "qas": [
            {"id": f"synthetic-a-{index}", "question": f"When did archive {index} open?", "answers": answers, "is_impossible": False},
            {"id": f"synthetic-u-{index}", "question": f"How many visitors came to archive {index}?", "answers": [], "is_impossible": True, "plausible_answers": answers},
        ]}]})
    old = pilot["cases"][0]
    # Exercise ID and context exclusion independently, including a new ID on
    # an old paragraph and an old ID on a different paragraph.
    articles.append({"title": "Excluded pilot material", "paragraphs": [
        {"context": old["context"], "qas": [{"id": "new-question-on-old-context", "question": old["question"], "answers": old["source"]["original_answers"], "is_impossible": False}]},
        {"context": articles[0]["paragraphs"][0]["context"], "qas": [{"id": old["source"]["original_id"], "question": "When did this archive open?", "answers": articles[0]["paragraphs"][0]["qas"][0]["answers"], "is_impossible": False}]},
    ]})
    raw = json.dumps({"version": "v2.0", "data": articles}).encode("utf-8")
    pilot["metadata"]["source_sha256"] = sha256_bytes(raw)
    return raw, pilot


def test_selection_reproduces_without_download_and_preserves_its_inputs(inputs):
    _, pilot, custom, freeze = inputs
    raw, pilot = synthetic_source(pilot)
    before = copy.deepcopy((pilot, custom))
    first = prepare_final_dataset(raw, pilot, custom, freeze)
    second = prepare_final_dataset(raw, pilot, custom, freeze)
    assert first == second
    assert (pilot, custom) == before
    assert first["metadata"]["selection"]["selected_squad_articles"] == 40
    assert all(case["source"].get("article_title") != "Excluded pilot material" for case in first["cases"])


def test_source_bytes_must_match_the_pinned_snapshot(inputs):
    _, pilot, custom, freeze = inputs
    raw, pilot = synthetic_source(pilot)
    with pytest.raises(ValueError, match="source hash differs"):
        prepare_final_dataset(raw + b" ", pilot, custom, freeze)


def test_insufficient_distinct_contexts_fails_instead_of_reusing_cases(inputs):
    _, pilot, custom, freeze = inputs
    raw, pilot = synthetic_source(pilot, article_count=39)
    with pytest.raises(ValueError, match="Not enough eligible distinct contexts"):
        prepare_final_dataset(raw, pilot, custom, freeze)


@pytest.mark.parametrize("change,message", [
    (lambda data, pilot: data["cases"][1].update(case_id=data["cases"][0]["case_id"]), "Duplicate"),
    (lambda data, pilot: data["cases"][1].update(context=data["cases"][0]["context"]), "Duplicate context"),
    (lambda data, pilot: data["cases"][0].update(context=pilot["cases"][0]["context"]), "Pilot context"),
    (lambda data, pilot: data["cases"][0]["source"].update(original_id=pilot["cases"][0]["source"]["original_id"]), "excluded pilot SQuAD"),
    (lambda data, pilot: data["cases"][1]["source"].update(original_id=data["cases"][0]["source"]["original_id"]), "duplicate"),
    (lambda data, pilot: data["cases"][0]["source"]["original_answers"][0].update(answer_start=-1), "span"),
    (lambda data, pilot: data["cases"][0].update(expected_answers=["invented alternative"]), "Reference alternatives differ"),
    (lambda data, pilot: data["cases"][30].update(expected_answers=["a plausible guess"]), "abstention"),
    (lambda data, pilot: data["cases"][0].update(actual_response="a generated answer"), "input fields only"),
    (lambda data, pilot: data["metadata"]["selection"].update(performance_based_selection=True), "selection rules changed"),
    (lambda data, pilot: data["metadata"]["selection"].update(pilot_context_sha256_excluded=[]), "pilot exclusions"),
    (lambda data, pilot: data["metadata"]["selection"].update(selected_squad_articles=40), "article counts"),
    (lambda data, pilot: data.update(schema_version=True), "50 versioned"),
])
def test_invalid_inputs_provenance_leakage_and_outcome_contamination_are_rejected(inputs, change, message):
    dataset, pilot, custom, freeze = inputs
    change(dataset, pilot)
    with pytest.raises(ValueError, match=message):
        validate_final_dataset(dataset, pilot, custom, freeze)


def test_composition_is_checked_separately_from_individual_case_validity(inputs):
    dataset, pilot, custom, freeze = inputs
    case = dataset["cases"][0]
    case.update(category="unanswerable", expects_abstention=True, expected_answers=[ABSTENTION])
    case["source"].update(is_impossible=True, original_answers=[])
    with pytest.raises(ValueError, match="composition"):
        validate_final_dataset(dataset, pilot, custom, freeze)


def test_custom_inputs_and_protocol_fingerprint_are_bound_to_the_selection(inputs):
    dataset, pilot, custom, freeze = inputs
    custom["cases"][0]["question"] += " Please answer."
    with pytest.raises(ValueError, match="metadata differs"):
        validate_final_dataset(dataset, pilot, custom, freeze)
    custom = read_json(ROOT / "data/final-custom-cases.json")
    with pytest.raises(ValueError, match="metadata differs"):
        validate_final_dataset(dataset, pilot, custom, "0" * 64)


def test_manifest_detects_a_structurally_valid_question_edit_and_tolerates_json_layout(inputs, tmp_path):
    dataset, pilot, custom, freeze = inputs
    path = tmp_path / "final.json"
    manifest = tmp_path / "final-manifest.json"
    shutil.copyfile(ROOT / "data/final-manifest.json", manifest)
    path.write_text(json.dumps(dataset, ensure_ascii=False, sort_keys=True, indent=4), encoding="utf-8-sig")
    assert load_final_dataset(path, pilot, custom, freeze) == dataset
    dataset["cases"][0]["question"] += " Please answer."
    path.write_text(json.dumps(dataset), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest does not match"):
        load_final_dataset(path, pilot, custom, freeze)


@pytest.fixture
def cli():
    spec = importlib.util.spec_from_file_location("final_dataset_command", ROOT / "scripts/prepare_final_dataset.py")
    command = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(command)
    return command


def test_cli_validates_published_inputs_without_raw_source_or_model_calls(cli, tmp_path, capsys):
    files = (*FROZEN_TEXT_FILES, *EVIDENCE_FILES, "config.toml", "evaluation-freeze.json",
             "data/final.json", "data/final-custom-cases.json", "data/final-manifest.json")
    for relative in files:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert not (tmp_path / "data/raw").exists()
    assert cli.main(["validate"], root=tmp_path) == 0
    output = capsys.readouterr().out
    assert '"case_count": 50' in output
    assert '"model_inference_performed": false' in output
    assert '"source_reproduction_checked": false' in output
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert cli.main(["prepare"], root=tmp_path) == 2
    assert "already exists" in capsys.readouterr().out
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_cli_creates_a_new_pair_preserves_it_and_stops_on_protocol_drift(cli, inputs, tmp_path, monkeypatch, capsys):
    _, pilot, custom, freeze = inputs
    raw, pilot = synthetic_source(pilot)
    (tmp_path / "data/raw").mkdir(parents=True)
    (tmp_path / "data/pilot.json").write_text(json.dumps(pilot), encoding="utf-8")
    (tmp_path / "data/final-custom-cases.json").write_text(json.dumps(custom), encoding="utf-8")
    (tmp_path / "data/raw/dev-v2.0.json").write_bytes(raw)
    calls = []

    def verified(root):
        calls.append(root)
        return {"freeze_sha256": freeze}

    monkeypatch.setattr(cli, "check_evaluation_freeze", verified)
    assert cli.main(["prepare"], root=tmp_path) == 0
    saved = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert cli.main(["prepare"], root=tmp_path) == 2
    assert "already exists" in capsys.readouterr().out
    assert saved == {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert cli.main(["validate", "--source", "data/raw/dev-v2.0.json"], root=tmp_path) == 0
    assert '"source_reproduction_checked": true' in capsys.readouterr().out
    assert len(calls) == 3

    def drift(root):
        raise ValueError("Protocol was changed")

    monkeypatch.setattr(cli, "check_evaluation_freeze", drift)
    assert cli.main(["prepare", "--output-dir", "new-selection"], root=tmp_path) == 2
    assert "Protocol was changed" in capsys.readouterr().out
    assert not (tmp_path / "new-selection").exists()
