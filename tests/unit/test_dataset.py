import copy
import json

import pytest

from llm_eval.config import ROOT
from llm_eval.dataset import ABSTENTION, load_dataset, prepare_pilot, validate_dataset


@pytest.fixture
def pilot():
    return load_dataset(ROOT / "data" / "pilot.json")


def test_pilot_preserves_source_ids_aliases_and_answer_spans(pilot):
    assert len(pilot["cases"]) == 10
    squad = [case for case in pilot["cases"] if case["source"]["dataset"] == "SQuAD 2.0"]
    assert len({case["source"]["article_title"] for case in squad}) == 8
    assert len(pilot["metadata"]["exclude_from_final_source_ids"]) == 8
    assert sum(case["expects_abstention"] for case in pilot["cases"]) == 3
    assert any(len(case["expected_answers"]) > 1 for case in squad)


def test_duplicate_ids_are_rejected(pilot):
    pilot["cases"][1]["case_id"] = pilot["cases"][0]["case_id"]
    with pytest.raises(ValueError, match="Duplicate"):
        validate_dataset(pilot)


def test_wrong_answer_span_is_rejected(pilot):
    pilot["cases"][0]["source"]["original_answers"][0]["answer_start"] = 0
    with pytest.raises(ValueError, match="span"):
        validate_dataset(pilot)


def test_unanswerable_reference_must_not_be_a_plausible_answer(pilot):
    case = next(case for case in pilot["cases"] if case["category"] == "unanswerable")
    case["expected_answers"] = ["a tempting but unsupported answer"]
    with pytest.raises(ValueError, match="Abstention"):
        validate_dataset(pilot)


def test_source_references_cannot_be_silently_changed(pilot):
    pilot["cases"][0]["expected_answers"] = ["fabricated reference"]
    with pytest.raises(ValueError, match="Reference"):
        validate_dataset(pilot)


def test_selection_is_reproducible_without_a_network_download():
    articles = []
    for index in range(8):
        context = "The library opened in 2018. " + "A quiet reading room is available. " * 5
        impossible = index >= 6
        qa = {"id": f"source-{index}", "question": "When did the library open?", "is_impossible": impossible,
              "answers": [] if impossible else [{"text": "2018", "answer_start": context.index("2018")}], "plausible_answers": []}
        articles.append({"title": f"Article {index}", "paragraphs": [{"context": context, "qas": [qa]}]})
    raw = json.dumps({"version": "v2.0", "data": articles}).encode()
    first, second = prepare_pilot(raw), prepare_pilot(raw)
    assert first == second
    assert first["metadata"]["selection"]["performance_based_selection"] is False
    assert first["cases"][6]["expected_answers"] == [ABSTENTION]


def test_a_large_or_wrongly_labelled_dataset_is_not_a_pilot(pilot):
    pilot["cases"].append(copy.deepcopy(pilot["cases"][0]))
    with pytest.raises(ValueError, match="exactly 10"):
        validate_dataset(pilot)
