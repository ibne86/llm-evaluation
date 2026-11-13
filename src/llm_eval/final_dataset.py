"""Prepare and validate the separate final inputs without running any model."""

import copy
import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path

from llm_eval.dataset import ABSTENTION, SOURCE_URL, sha256_bytes, validate_dataset

VERSION = "final-selection-v1"
SEED = 42
LICENSE = "CC-BY-SA-4.0"
CATEGORIES = {"answerable": 30, "unanswerable": 10, "ambiguity": 5, "instruction_in_context": 5}
CASE_FIELDS = {"case_id", "question", "context", "expected_answers", "expects_abstention", "category", "source"}
RULES = {
    "context_utf8_bytes_min": 150,
    "context_utf8_bytes_max": 650,
    "question_utf8_bytes_max": 180,
    "reference_json_utf8_bytes_max": 160,
    "order": "answerable then unanswerable; sort original IDs; seeded shuffle per category; first eligible case from a least-used article",
    "distinct_contexts": True,
    "performance_based_selection": False,
}


def canonical_sha256(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _exclusions(pilot):
    validate_dataset(pilot)
    source_ids = {case["source"]["original_id"] for case in pilot["cases"] if case["source"]["dataset"] == "SQuAD 2.0"}
    contexts = {sha256_bytes(case["context"].encode("utf-8")) for case in pilot["cases"]}
    return source_ids, contexts, {case["case_id"] for case in pilot["cases"]}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _spans(answers, context):
    if not isinstance(answers, list):
        raise ValueError("Source answer spans must be a list.")
    for answer in answers:
        if not isinstance(answer, dict) or not _text(answer.get("text")):
            raise ValueError("Source answer span needs nonempty text.")
        start, text = answer.get("answer_start"), answer["text"]
        if type(start) is not int or start < 0 or context[start:start + len(text)] != text:
            raise ValueError("Source answer span does not match its full context.")


def _check_cases(cases, pilot):
    pilot_ids, pilot_contexts, pilot_case_ids = _exclusions(pilot)
    ids, source_ids, contexts, articles, categories = set(), set(), set(), set(), Counter()
    for case in cases:
        if not isinstance(case, dict) or set(case) != CASE_FIELDS:
            raise ValueError("Final cases must contain input fields only; responses/scores belong in run results.")
        if not all(_text(case.get(field)) for field in ("case_id", "question", "context", "category")):
            raise ValueError("Case IDs, questions, contexts and categories must be nonempty strings.")
        if case["case_id"] in ids or case["case_id"] in pilot_case_ids:
            raise ValueError("Duplicate or reused pilot case ID.")
        ids.add(case["case_id"])
        context_hash = sha256_bytes(case["context"].encode("utf-8"))
        if context_hash in pilot_contexts:
            raise ValueError("Pilot context reused in final inputs.")
        if context_hash in contexts:
            raise ValueError("Duplicate context in final inputs.")
        contexts.add(context_hash)
        if not RULES["context_utf8_bytes_min"] <= len(case["context"].encode("utf-8")) <= RULES["context_utf8_bytes_max"]:
            raise ValueError("Context exceeds the declared complete-context byte limits.")
        if len(case["question"].encode("utf-8")) > RULES["question_utf8_bytes_max"]:
            raise ValueError("Question exceeds the declared byte limit.")
        answers = case["expected_answers"]
        if not isinstance(answers, list) or not answers or not all(_text(answer) for answer in answers):
            raise ValueError("Cases need nonempty reference alternatives.")
        if len(set(answers)) != len(answers) or len(json.dumps(answers, ensure_ascii=False).encode("utf-8")) > RULES["reference_json_utf8_bytes_max"]:
            raise ValueError("Reference alternatives must be unique and fit the declared byte limit.")
        category = case["category"]
        if category not in CATEGORIES or type(case["expects_abstention"]) is not bool:
            raise ValueError("Unknown category or invalid abstention flag.")
        abstains = category in ("unanswerable", "ambiguity")
        if case["expects_abstention"] is not abstains or ((answers == [ABSTENTION]) != abstains) or (not abstains and ABSTENTION in answers):
            raise ValueError("Category, abstention flag and reference contract disagree.")
        source = case["source"]
        if not isinstance(source, dict) or source.get("license") != LICENSE:
            raise ValueError("Case source needs the preserved data license.")
        if category in ("answerable", "unanswerable"):
            source_id = source.get("original_id")
            if not _text(source_id) or source_id in source_ids or source_id in pilot_ids:
                raise ValueError("Missing, duplicate or excluded pilot SQuAD ID.")
            source_ids.add(source_id)
            if (case["case_id"] != f"final-squad-{source_id}" or source.get("dataset") != "SQuAD 2.0"
                    or source.get("split") != "dev/validation" or source.get("url") != SOURCE_URL
                    or not _text(source.get("article_title")) or source.get("is_impossible") is not abstains):
                raise ValueError("SQuAD provenance or category was changed.")
            original = source.get("original_answers")
            _spans(original, case["context"])
            _spans(source.get("plausible_answers_not_used_as_references"), case["context"])
            if abstains:
                if original:
                    raise ValueError("Impossible questions must have no reference answer spans.")
            elif answers != list(dict.fromkeys(answer["text"] for answer in original)):
                raise ValueError("Reference alternatives differ from original source spans.")
            articles.add(source["article_title"])
        elif (source.get("dataset") != "project custom" or not case["case_id"].startswith("final-custom-")
              or not _text(source.get("scenario")) or source.get("authorship") != "AI-assisted synthetic project fixture"):
            raise ValueError("Custom cases need explicit synthetic provenance and scenario.")
        categories[category] += 1
    return categories, articles


def _check_custom(custom, pilot):
    if (not isinstance(custom, dict) or set(custom) != {"schema_version", "metadata", "cases"}
            or type(custom.get("schema_version")) is not int or custom["schema_version"] != 1
            or not isinstance(custom.get("cases"), list) or len(custom["cases"]) != 10):
        raise ValueError("Expected ten versioned synthetic custom fixtures.")
    if custom["metadata"] != {"license": LICENSE, "authorship": "AI-assisted synthetic project fixtures; not human review ratings"}:
        raise ValueError("Custom fixture authorship/license metadata changed.")
    counts, _ = _check_cases(custom["cases"], pilot)
    if counts != {"ambiguity": 5, "instruction_in_context": 5}:
        raise ValueError("Custom fixtures require five ambiguity and five embedded-instruction cases.")


def prepare_final_dataset(raw, pilot, custom, freeze_sha256):
    """Select deterministically from the pilot's pinned source, before inference."""
    _check_custom(custom, pilot)
    if sha256_bytes(raw) != pilot["metadata"]["source_sha256"]:
        raise ValueError("Publisher source hash differs from the snapshot used by the frozen pilot.")
    source = json.loads(raw)
    if source.get("version") != "v2.0" or not isinstance(source.get("data"), list):
        raise ValueError("Expected the publisher's SQuAD v2.0 source format.")
    excluded_ids, excluded_contexts, _ = _exclusions(pilot)
    pools = {"answerable": [], "unanswerable": []}
    for article in source["data"]:
        for paragraph in article["paragraphs"]:
            context = paragraph["context"]
            if (sha256_bytes(context.encode("utf-8")) in excluded_contexts
                    or not RULES["context_utf8_bytes_min"] <= len(context.encode("utf-8")) <= RULES["context_utf8_bytes_max"]):
                continue
            for qa in paragraph["qas"]:
                if type(qa["is_impossible"]) is not bool:
                    raise ValueError("Source is_impossible must be a boolean.")
                answers = list(dict.fromkeys(answer["text"] for answer in qa["answers"]))
                if (qa["id"] in excluded_ids or len(qa["question"].encode("utf-8")) > RULES["question_utf8_bytes_max"]
                        or len(json.dumps(answers, ensure_ascii=False).encode("utf-8")) > RULES["reference_json_utf8_bytes_max"]):
                    continue
                category = "unanswerable" if qa["is_impossible"] else "answerable"
                pools[category].append({
                    "case_id": f"final-squad-{qa['id']}", "question": qa["question"], "context": context,
                    "expected_answers": [ABSTENTION] if qa["is_impossible"] else answers,
                    "expects_abstention": qa["is_impossible"], "category": category,
                    "source": {
                        "dataset": "SQuAD 2.0", "split": "dev/validation", "original_id": qa["id"],
                        "article_title": article["title"], "url": SOURCE_URL, "license": LICENSE,
                        "is_impossible": qa["is_impossible"], "original_answers": copy.deepcopy(qa["answers"]),
                        "plausible_answers_not_used_as_references": copy.deepcopy(qa.get("plausible_answers", [])),
                    },
                })
    rng, selected, article_counts = random.Random(SEED), [], Counter()
    used_contexts = {sha256_bytes(case["context"].encode("utf-8")) for case in custom["cases"]}
    for category, count in (("answerable", 30), ("unanswerable", 10)):
        pool = sorted(pools[category], key=lambda case: case["source"]["original_id"])
        rng.shuffle(pool)
        for _ in range(count):
            available = [case for case in pool if sha256_bytes(case["context"].encode("utf-8")) not in used_contexts]
            if not available:
                raise ValueError(f"Not enough eligible distinct contexts for {category}.")
            case = min(available, key=lambda row: article_counts[row["source"]["article_title"]])
            selected.append(case)
            used_contexts.add(sha256_bytes(case["context"].encode("utf-8")))
            article_counts[case["source"]["article_title"]] += 1
    selected.extend(copy.deepcopy(custom["cases"]))
    dataset = {
        "schema_version": 1,
        "metadata": {
            "phase": "final_evaluation", "selection_version": VERSION, "selection_seed": SEED,
            "source_url": SOURCE_URL, "source_sha256": sha256_bytes(raw), "source_version": "v2.0", "license": LICENSE,
            "pilot_sha256": canonical_sha256(pilot), "custom_cases_sha256": canonical_sha256(custom),
            "evaluation_freeze_sha256": freeze_sha256,
            "selection": {
                **RULES, "eligible_answerable": len(pools["answerable"]), "eligible_unanswerable": len(pools["unanswerable"]),
                "selected_squad_articles": len(article_counts), "pilot_source_ids_excluded": sorted(excluded_ids),
                "pilot_context_sha256_excluded": sorted(excluded_contexts),
            },
        },
        "cases": selected,
    }
    validate_final_dataset(dataset, pilot, custom, freeze_sha256)
    return dataset


def validate_final_dataset(dataset, pilot, custom, freeze_sha256):
    _check_custom(custom, pilot)
    if (not isinstance(dataset, dict) or set(dataset) != {"schema_version", "metadata", "cases"}
            or type(dataset.get("schema_version")) is not int or dataset["schema_version"] != 1
            or not isinstance(dataset.get("cases"), list) or len(dataset["cases"]) != 50):
        raise ValueError("The separate final dataset must contain exactly 50 versioned input cases.")
    if not isinstance(freeze_sha256, str) or not re.fullmatch("[0-9a-f]{64}", freeze_sha256):
        raise ValueError("A verified protocol-freeze fingerprint is required.")
    metadata = dataset["metadata"]
    fixed = {
        "phase": "final_evaluation", "selection_version": VERSION, "selection_seed": SEED,
        "source_url": SOURCE_URL, "source_sha256": pilot["metadata"]["source_sha256"], "source_version": "v2.0", "license": LICENSE,
        "pilot_sha256": canonical_sha256(pilot), "custom_cases_sha256": canonical_sha256(custom),
        "evaluation_freeze_sha256": freeze_sha256,
    }
    if not isinstance(metadata, dict) or set(metadata) != {*fixed, "selection"}:
        raise ValueError("Final dataset metadata fields changed.")
    if canonical_sha256({key: metadata[key] for key in fixed}) != canonical_sha256(fixed):
        raise ValueError("Final dataset source, pilot, custom, protocol or selection metadata differs.")
    counts, articles = _check_cases(dataset["cases"], pilot)
    if counts != CATEGORIES:
        raise ValueError(f"Final category composition must be 30/10/5/5, found {dict(counts)}.")
    actual_custom = [case for case in dataset["cases"] if case["source"]["dataset"] == "project custom"]
    if canonical_sha256(actual_custom) != canonical_sha256(custom["cases"]):
        raise ValueError("Selected custom fixtures differ from their preserved input file.")
    excluded_ids, excluded_contexts, _ = _exclusions(pilot)
    selection = metadata["selection"]
    extra = {"eligible_answerable", "eligible_unanswerable", "selected_squad_articles", "pilot_source_ids_excluded", "pilot_context_sha256_excluded"}
    if not isinstance(selection, dict) or set(selection) != set(RULES) | extra:
        raise ValueError("Selection rules/counts are incomplete or unexpected.")
    if canonical_sha256({key: selection[key] for key in RULES}) != canonical_sha256(RULES):
        raise ValueError("Declared selection rules changed.")
    if (selection["pilot_source_ids_excluded"] != sorted(excluded_ids)
            or selection["pilot_context_sha256_excluded"] != sorted(excluded_contexts)
            or type(selection["selected_squad_articles"]) is not int or selection["selected_squad_articles"] != len(articles)):
        raise ValueError("Recorded pilot exclusions or article counts differ from the actual inputs.")
    for category in ("answerable", "unanswerable"):
        count = selection[f"eligible_{category}"]
        if type(count) is not int or count < CATEGORIES[category]:
            raise ValueError("Invalid eligible-source counts.")
    return dataset["cases"]


def make_final_manifest(dataset, pilot, custom, freeze_sha256, filename="final.json"):
    validate_final_dataset(dataset, pilot, custom, freeze_sha256)
    return {
        "schema_version": 1, "dataset_file": filename, "hash_algorithm": "canonical-json-sha256-v1",
        "dataset_sha256": canonical_sha256(dataset), "case_count": 50, "categories": CATEGORIES.copy(),
        "selection_version": VERSION, "selection_seed": SEED,
        "source_sha256": dataset["metadata"]["source_sha256"], "pilot_sha256": canonical_sha256(pilot),
        "custom_cases_sha256": canonical_sha256(custom), "evaluation_freeze_sha256": freeze_sha256,
    }


def load_final_dataset(path, pilot, custom, freeze_sha256, manifest_path=None):
    path = Path(path)
    dataset = read_json(path)
    expected = make_final_manifest(dataset, pilot, custom, freeze_sha256, path.name)
    manifest = read_json(manifest_path or path.with_name("final-manifest.json"))
    if canonical_sha256(manifest) != canonical_sha256(expected):
        raise ValueError("Final dataset manifest does not match its input content and frozen dependencies.")
    return dataset
