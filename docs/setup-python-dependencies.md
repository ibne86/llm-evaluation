# Step 2b: Python dependencies

The user has verified the local Ollama application. This checkpoint installs Python packages into the project's existing `.venv`.

## Package roles

| Package | Purpose |
| --- | --- |
| deepeval | Evaluation metrics and the interface to the local judge |
| ollama | Python client for the already-installed Ollama application |
| pytest | Automated test execution and assertions |

DeepEval also installs its own supporting dependencies. Installing provider libraries does not run model evaluation; our evaluation code will explicitly select the local Ollama judge.

## Installation and reproducibility

During initial setup, pip resolves compatible releases for Python 3.12. After validation, the three installed direct versions are pinned in `requirements.txt`, and the complete tested dependency snapshot is saved in `requirements-lock.txt`.

To reproduce the tested Windows/Python 3.12 package environment in a fresh virtual environment:

```powershell
Set-Location -LiteralPath 'C:\Users\khani\Projects\llm-evaluation'
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip check
```

The full snapshot records this tested Windows environment. Resolve and verify dependencies separately before claiming compatibility with a different Python version or operating system.

## Verify in PyCharm's Terminal

Run this command in the **Terminal** tab with the `PS` prompt:

```powershell
.\.venv\Scripts\python.exe .\scripts\check_environment.py
```

It should print the project's Python executable, the three package versions, successful DeepEval imports, the judge interface check, and a successful local Ollama connection. It ends with:

```text
Environment checks passed. No model inference was run.
```

The check sets `DEEPEVAL_TELEMETRY_OPT_OUT=1` before importing DeepEval and disables automatic dotenv loading for this diagnostic. It sends only a model-list request to the explicit localhost address. It does not load, download, generate with, or evaluate a model.

The schema interface check is a prerequisite only. The judge's real JSON output, scoring behavior, speed, and memory requirements still need testing after model setup.

## Next checkpoint

After user verification, recheck available RAM and download/benchmark one proposed model at a time. The final 50-case dataset remains gated on a successful and user-reviewed 10-case pilot.

Official references:

- https://deepeval.com/integrations/models/ollama
- https://deepeval.com/docs/data-privacy
- https://github.com/ollama/ollama-python
- https://docs.pytest.org/en/stable/getting-started.html
