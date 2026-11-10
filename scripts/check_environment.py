"""Check the project's Python packages and local Ollama connection."""

import inspect
import os
import sys
from importlib.metadata import version
from pathlib import Path

# Set these before importing DeepEval. This check needs no hosted services.
os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "1"
os.environ["DEEPEVAL_DISABLE_DOTENV"] = "1"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OLLAMA_HOST = "http://127.0.0.1:11434"


def main() -> int:
    print(f"Python executable: {sys.executable}")
    if Path(sys.prefix).resolve() != (PROJECT_ROOT / ".venv").resolve():
        print("Use this project's .venv interpreter to run this check.")
        return 1

    try:
        import ollama
        import pytest
        from deepeval.metrics import AnswerRelevancyMetric, GEval
        from deepeval.models import OllamaModel
        from deepeval.test_case import LLMTestCase
    except ImportError as error:
        print(f"A required package could not be imported: {error}")
        print("Install the project's requirements into .venv first.")
        return 1

    for package in ("deepeval", "ollama", "pytest"):
        print(f"{package}: {version(package)}")

    # Inspect the interface only; do not ask a model to generate anything.
    for method in (OllamaModel.generate, OllamaModel.a_generate):
        if "schema" not in inspect.signature(method).parameters:
            print(f"Judge interface check failed: {method.__name__} lacks schema.")
            return 1
    print("DeepEval metric imports: OK")
    print("Judge interface: schema parameter present; runtime validation pending")

    try:
        client = ollama.Client(host=OLLAMA_HOST, timeout=10)
        models = client.list().models
    except Exception as error:
        print(f"Local Ollama connection failed: {error}")
        print("Open the installed Ollama application, then retry this check.")
        return 1

    print(f"Local Ollama connection: OK ({len(models)} models installed)")
    print("Environment checks passed. No model inference was run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
