"""Check the recorded evaluation protocol without importing or calling a model."""

import hashlib
import json
import sys
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from llm_eval.config import ROOT, fingerprint

FROZEN_TEXT_FILES = (
    "src/llm_eval/ollama_client.py",
    "src/llm_eval/judge.py",
    "src/llm_eval/metrics.py",
    "requirements.txt",
    "requirements-lock.txt",
)
EVIDENCE_FILES = (
    "data/pilot.json",
    "results/examples/pilot-results.json",
    "results/examples/pilot-human-review-with-reasons.json",
    "results/examples/pilot-human-comparison-with-reasons.json",
    "results/examples/consistency-results.json",
    "results/examples/consistency-human-review.json",
    "results/examples/consistency-human-comparison.json",
)


def text_sha256(path):
    """Ignore checkout line endings and a UTF-8 BOM, preserving other text."""
    content = Path(path).read_text(encoding="utf-8-sig")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def json_sha256(path):
    """Ignore JSON layout while preserving every recorded value and list order."""
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _locked_packages(path):
    packages = {}
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, pin = line.split("==")
        if not name or not pin or name in packages:
            raise ValueError("Dependency snapshot needs unique exact package pins.")
        packages[name] = pin
    if not packages:
        raise ValueError("Dependency snapshot is empty.")
    return packages


def check_evaluation_freeze(root=ROOT, config_path=None, *, check_environment=True):
    """Raise on drift; the dataset, live server and model weights are separate checks."""
    root = Path(root)
    freeze = json.loads((root / "evaluation-freeze.json").read_text(encoding="utf-8-sig"))
    if type(freeze.get("schema_version")) is not int or freeze["schema_version"] != 1:
        raise ValueError("Unsupported evaluation freeze schema.")
    if freeze["scope"] != "evaluation_protocol_only" or freeze["decision"] != "retain_original_baseline":
        raise ValueError("This freeze records the original evaluation baseline only.")
    if not isinstance(freeze["freeze_id"], str) or not freeze["freeze_id"].strip():
        raise ValueError("Evaluation freeze needs an identifier.")
    if set(freeze["text_sha256"]) != set(FROZEN_TEXT_FILES) or set(freeze["evidence_sha256"]) != set(EVIDENCE_FILES):
        raise ValueError("Frozen file coverage changed; a required source or evidence file is missing or unexpected.")

    errors = []
    config_path = root / (config_path or "config.toml")
    config = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
    # Final input selection will get its own immutable dataset hash. No other
    # configuration field is exempt from this comparison.
    dataset = config.pop("dataset", None)
    if not isinstance(dataset, str) or not dataset.strip():
        errors.append("Configuration needs a dataset path (dataset contents are not checked here).")
    expected = freeze["protocol_config"]
    for key in sorted(set(expected) | set(config)):
        if key not in config or key not in expected or fingerprint(config[key]) != fingerprint(expected[key]):
            errors.append(f"Configuration differs: {key}.")

    for field, paths, hash_file in (
        ("text_sha256", FROZEN_TEXT_FILES, text_sha256),
        ("evidence_sha256", EVIDENCE_FILES, json_sha256),
    ):
        for relative in paths:
            if hash_file(root / relative) != freeze[field][relative]:
                errors.append(f"Frozen file changed: {relative}.")

    environment = freeze["environment"]
    if environment["packages"] != _locked_packages(root / "requirements-lock.txt"):
        errors.append("Frozen package versions differ from requirements-lock.txt.")
    # These are recorded artifacts from completed runs, not a query of today's
    # Ollama service. Keep that distinction visible in the command's result.
    for relative in (EVIDENCE_FILES[1], EVIDENCE_FILES[4]):
        source = json.loads((root / relative).read_text(encoding="utf-8-sig"))
        metadata = source["metadata"]
        if metadata["model_digests"] != freeze["recorded_ollama"]["model_digests"]:
            errors.append(f"Model digest record differs: {relative}.")
        if metadata["ollama_server_version"] != freeze["recorded_ollama"]["server_version"]:
            errors.append(f"Ollama version record differs: {relative}.")
        if any(environment["packages"].get(name) != pin for name, pin in metadata["software"].items()):
            errors.append(f"Recorded evaluation package versions differ: {relative}.")
        source_config = {key: value for key, value in source["config"].items() if key != "dataset"}
        if fingerprint(source_config) != fingerprint(expected):
            errors.append(f"Protocol differs from original run: {relative}.")

    if check_environment:
        if f"{sys.version_info.major}.{sys.version_info.minor}" != environment["python_major_minor"]:
            errors.append(f"Python {environment['python_major_minor']} is required.")
        for name, pin in environment["packages"].items():
            try:
                actual = version(name)
            except PackageNotFoundError:
                actual = "not installed"
            if actual != pin:
                errors.append(f"Installed dependency differs: {name} expected {pin}, found {actual}.")
    if errors:
        raise ValueError("Evaluation freeze mismatch:\n- " + "\n- ".join(errors))
    return {
        "freeze_id": freeze["freeze_id"],
        "freeze_sha256": json_sha256(root / "evaluation-freeze.json"),
        "protocol_matches": True,
        "frozen_text_files": len(FROZEN_TEXT_FILES),
        "evidence_files": len(EVIDENCE_FILES),
        "installed_environment_checked": check_environment,
        "ollama_runtime_checked": False,
        "final_dataset_frozen": False,
    }
