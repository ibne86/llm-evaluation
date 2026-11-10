"""Read explicit, versioned pilot settings without loading API credentials."""

import hashlib
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load_config(path=None):
    path = Path(path) if path else ROOT / "config.toml"
    settings = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    if settings["host"] != "http://127.0.0.1:11434":
        raise ValueError("This pilot uses the explicit local Ollama endpoint.")
    if settings["answer"]["model"] != "qwen2.5:1.5b" or settings["judge"]["model"] != "qwen3:4b":
        raise ValueError("The pilot baseline keeps the original model pair; record an agreed model change separately.")
    for role in ("answer", "judge"):
        options = settings[role]["options"]
        if options["num_gpu"] != 0 or options["num_ctx"] < 1024 or options["num_predict"] <= 0:
            raise ValueError("Invalid CPU/context/output settings.")
    if not all(0 <= value <= 1 for value in settings["thresholds"].values()):
        raise ValueError("Metric thresholds must be between zero and one.")
    if settings["timeout_seconds"] <= 0:
        raise ValueError("Request timeout must be positive.")
    return settings
