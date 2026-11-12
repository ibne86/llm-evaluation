# Running and interpreting the 10-case development pilot

## What this step implements

1. Load and validate the 10-case JSON dataset and explicit TOML configuration.
2. Generate every response using `qwen2.5:1.5b`, supporting context and an abstention policy.
3. Save responses as they arrive, then unload the answer model.
4. Load the unchanged `qwen3:4b` judge and evaluate each completed response sequentially.
5. Unload the judge and save JSON, CSV and a readable Markdown summary.

The answer profile uses a 2048-token context and a 96-token output cap. The judge uses a 4096-token context and 256-token output cap so complete evidence and rubrics fit. CPU inference, four threads, small prompt batches, temperature zero and seed 42 remain explicit. These context changes are configuration changes, not model replacements.

## Metrics and checks

| Area | Method | Passing threshold |
| --- | --- | ---: |
| Answer relevancy | DeepEval AnswerRelevancyMetric | 0.7 |
| Semantic correctness | DeepEval G-Eval; any reference alias or equivalent wording is acceptable | 0.7 |
| Groundedness | DeepEval G-Eval; every factual claim must be supported by context | 0.8 |
| Abstention format | Exact `INSUFFICIENT_CONTEXT` marker when expected; no marker when answerable | deterministic |

G-Eval uses predefined evaluation steps, avoiding a separate model call to invent grading steps on each case. Its 0–10 score is normalized by DeepEval to 0–1. The steps, thresholds and versions are saved before the run. Groundedness does not assess retrieval and requires no retrieval pipeline.

A refusal can be grounded yet incorrect on an answerable question. An answer can be relevant yet factually wrong. Therefore all three metrics and the deterministic checks contribute to a case's result. Correct abstention is evaluated semantically and as a separate strict output-format contract.

## Commands in PyCharm's Terminal

Run a new pilot:

```powershell
& 'C:\Users\khani\Projects\llm-evaluation\.venv\Scripts\python.exe' 'C:\Users\khani\Projects\llm-evaluation\scripts\run_evaluation.py'
```

The command prints a new run folder inside `results/runs`. Every response and metric is checkpointed. Resume an interrupted run by adding `--resume` followed by that absolute folder path. Inputs, model digests, software, configuration and evaluation-code fingerprints must match. Completed work is skipped; unfinished or errored work is retried.

When intentionally changing judge code or settings during development, `--reuse-responses` followed by the old run folder creates a separate scoring run. It preserves compatible answers but never copies old scores. The dataset, generation policy, answer model digest and generation settings must still match. This does not permit tuning on final evaluation cases.

Read a saved summary without model inference by adding `--summary` followed by the run folder.

Exit codes: 0 means all quality checks passed; 1 means execution completed with model-quality failures; 2 means an execution error or incomplete run. The setup gate depends on execution completion and user review, not on hiding genuine quality failures.

## Reports and audit trail

- `results.json`: full contexts, references, responses, scores, explanations, errors, raw judge JSON, timing, model digests, software versions, hashes, configuration and memory snapshots.
- `results.csv`: combined case fields and metric results for inspection.
- `summary.md`: totals, metric averages with denominators, per-case outcomes, responses, failures and limitations.

Scores outside 0–1, malformed/truncated/empty responses, missing explanations, timeouts and context-budget violations are execution errors. They never become passing scores. Whole-system RAM snapshots are not peak or model-only measurements.

The original judge produced a contradictory explanation in a setup control. All pilot explanations are therefore review material, not established facts. The subsequent [manual review](pilot-review-findings.md) now records all 30 pilot verdicts and 25/30 human/local-judge matches. It was non-blinded; a separate follow-up now contains 30/30 written human reasons. Independent blinded validation remains outstanding, and the earlier review without reasons is preserved. Historical run snapshots keep their original status.

## Current milestone boundary

Review this pilot before preparing the 50-case final set. The pilot and final set will use separate IDs/contexts. No final cases, larger dataset, consistency suite or GitHub publication are part of this step.
