# Step 2e: a real DeepEval metric with the original judge

The original `qwen3:4b` model passed the direct structured-output controls. This step checks DeepEval's `AnswerRelevancyMetric` using that same local model. The answer model remains `qwen2.5:1.5b`.

## Small extension to the built-in adapter

`src/llm_eval/judge.py` extends DeepEval's existing `OllamaModel`. The installed base implementation already handles schemas and native model integration but does not forward the top-level `think` or `keep_alive` generation fields. The extension adds those fields and retains the installed native return format: output plus a zero local API cost.

Important behavior:

- Requests go to `http://127.0.0.1:11434` using `qwen3:4b`.
- CPU inference, a 2048-token context, a 256-token output cap, a small prompt batch, four CPU threads, temperature zero and seed 42 are explicit.
- `think=False` keeps the response budget for the structured answer.
- A 120-second request timeout bounds waiting; the keep-alive is 30 seconds.
- Pydantic validates JSON against each schema supplied by DeepEval.
- Empty, truncated, invalid and unexpectedly thinking responses raise errors rather than become scores.
- A conservative UTF-8 byte budget reserves output and template space, refusing overlong prompts before sending them. It is deliberately stricter than an exact Qwen token count; no silent truncation is accepted.
- Async calls use the same validated request method. Metric execution itself is sequential (`async_mode=False`).

## Project installation

The source package uses the planned `src/llm_eval` layout. `pyproject.toml` makes it installable into `.venv` in editable mode: Python can import the local source, and source edits are available without reinstalling it.

After installing the third-party lock file in a fresh Windows/Python 3.12 virtual environment, install this local project:

```powershell
Set-Location -LiteralPath 'C:\Users\khani\Projects\llm-evaluation'
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
```

The third-party snapshot excludes this editable project to avoid recording a machine-specific source path.

## Validation

Offline unit tests check malformed/out-of-range JSON, truncation, empty responses, unexpected thinking, network errors, prompt budgeting, and sync/async policy consistency. They use fake responses and do not call a model.

The actual integration diagnostic uses two synthetic controls:

1. A relevant answer to the library opening-year question, expected to pass.
2. An unrelated answer about bananas, expected to fail.

The metric uses threshold 0.7, includes its explanation, and explicitly selects LLM evaluation mode with the local judge. Each metric can make multiple judge requests; timings therefore differ from one direct model call. The runner always attempts to unload the judge after evaluation.

To read saved results without loading a model:

```powershell
& 'C:\Users\khani\Projects\llm-evaluation\.venv\Scripts\python.exe' 'C:\Users\khani\Projects\llm-evaluation\scripts\check_deepeval_judge.py' --summary
```

To run offline unit tests from the project terminal:

```powershell
$env:DEEPEVAL_TELEMETRY_OPT_OUT = '1'
$env:DEEPEVAL_DISABLE_DOTENV = '1'
.\.venv\Scripts\python.exe -m pytest -q
```

The saved JSON and Markdown reports live under `results/runs`. Successful controls demonstrate basic integration only. Relevancy does not establish factual correctness or groundedness, and two controls do not establish judge accuracy. The 10-case pilot and actual human review remain required; the 50-case set is still gated.

Official reference: https://deepeval.com/integrations/models/ollama and https://deepeval.com/docs/metrics-answer-relevancy.
