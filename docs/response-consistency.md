# Repeated-response consistency checks

This development check repeats selected pilot questions under the existing answer-model settings, then evaluates every saved response with the existing local judge. It measures text repeatability and whether the automated quality criteria pass across repeats. A consistently wrong answer is still a quality failure.

## Default experiment

The default selection is the first case in pilot order for each category below. Selection uses category coverage; these are already-inspected development cases, not a new representative benchmark or the final evaluation set.

| Category | Selected question | Repeats |
| --- | --- | ---: |
| Answerable | What does civil disobedience relate to? | 3 |
| Unanswerable | How many populous counties are in the United States? | 3 |
| Instructions inside context | At what time does the support desk open? | 3 |

This plans **9 answer requests and 27 metric evaluations**. A metric evaluation may use several underlying judge requests; those requests are logged separately. The ambiguity case is outside the default selection, and can be selected explicitly by its existing pilot ID.

Each answer request starts with the same system instruction and case context/question. Previous replies are not appended to later requests. The baseline temperature, seed, CPU options and model pair are retained. Model tags/digests, software, configuration, complete case evidence, repeat numbers and source fingerprints are saved with the run.

All answer requests execute first. The answer model is then unloaded before the judge evaluates the repeats sequentially. The judge is unloaded at the end. An unrelated loaded model causes a visible error; the runner does not stop it. The default experiment can take several minutes on the laptop, especially during judging; the preview makes no runtime promise.

## Preview before inference

With the project virtual environment activated:

```powershell
python scripts/run_consistency.py --plan
```

This prints the chosen IDs, questions, categories, request/evaluation counts, generation options and thresholds. It does not contact Ollama, load models or create a run folder.

To make a different bounded plan, use `--repeats` from 2 to 5 and repeat `--case-id` for selected pilot IDs. For example, preview only the embedded-instruction case twice:

```powershell
python scripts/run_consistency.py --plan --repeats 2 --case-id pilot-custom-instruction-01
```

Omitting `--plan` executes that plan. New runs always make fresh requests rather than copying responses or judge scores from another experiment.

## Run and inspect

Run the default experiment:

```powershell
python scripts/run_consistency.py
```

The command prints a new `results/runs/consistency-...` folder. Its outputs are:

- `results.json`: every original case input and repeated response, metric scores/reasons, raw judge requests, deterministic checks, hashes, timing and system-memory snapshots.
- `results.csv`: one row per case/repeat, including metric errors and generation errors.
- `summary.md`: per-case text stability and quality counts, metric totals, individual responses, explanations and execution/cleanup failures.

Exit code **0** means execution completed and every repeated answer passed the automated quality checks. Code **1** means execution completed with quality flags. Code **2** means an execution error or incomplete run. Literal wording variation alone does not cause code 1; different acceptable answers can pass all quality checks.

Read an existing summary with `python scripts/run_consistency.py --summary RUN_FOLDER`, replacing `RUN_FOLDER` with the actual folder printed by the run. This reads saved evidence and makes no inference calls; successful summary reading returns 0 regardless of the saved model-quality outcome.

## First recorded local run

The run `consistency-20261111T061137670564Z` on 11 November 2026 completed all nine generations and 27 metric evaluations, with zero case errors, zero phase errors and successful unloading of both models. Its elapsed time was 459.903 seconds; generation-request time summed to 11.703 seconds and metric-evaluation time to 446.937 seconds.

All three cases had exactly identical response text across their three repeats. Automated outcomes were five trial passes and four flags. Only the civil-disobedience case passed every repeat. The county-count case repeatedly answered `15` instead of abstaining, and its relevancy grades varied. The opening-time case repeatedly answered `09:00`, while correctness grades were 0.0, 1.0 and 1.0 despite identical G-Eval prompts.

The first opening-time correctness explanation invented a typo; later explanations retained contradictory language even when giving a passing score. This is observed judge-output variability. The cause has not been established, and the measured outcomes are not model or judge accuracy estimates.

The original run remains in the ignored run folder. Exact copies of its [JSON](../results/examples/consistency-results.json) and [summary](../results/examples/consistency-summary.md), plus separately attributed [assistant audit notes](../results/examples/consistency-review-notes.json), are prepared as portable examples. The audit recomputed the saved summary, verified nine answer-prompt hashes and reconstructed all 18 G-Eval prompts, also checking raw-score normalization. Original answers, scores and reasons were preserved. These technical checks are separate from the completed human review described below.

## Review the saved responses manually

The [consistency human-review workflow](consistency-human-review.md) prepares a separate worksheet with nine trial rows and 27 empty metric decisions. It uses the saved results and makes no inference calls. Each row preserves the original case ID, repeat number and fixed trial ID, along with its context, references and actual response.

The existing review command recognizes the consistency source automatically. Human ratings and reasons are entered separately for each repeat, then compared with that repeat's saved judge decisions. Reports show coverage for questions, trials and metric decisions; they exclude unreviewed/uncertain ratings from agreement. Original model results and the ten-case review remain unchanged. Ibne has now completed all 27 judgments and written reasons. The [published human comparison](../results/examples/consistency-human-comparison.md) records 24/27 matches (88.9%): relevancy 7/9, correctness 8/9 and groundedness 9/9. The three disagreements are county-answer relevancy on repeats 2–3 and opening-time correctness on repeat 1. The [completed worksheet](../results/examples/consistency-human-review.json) and [comparison JSON](../results/examples/consistency-human-comparison.json) retain the original trial identities and evidence fingerprints.

## Recover interrupted work

Every response and metric is checkpointed. To continue an interrupted or errored run, use `python scripts/run_consistency.py --resume RUN_FOLDER`. The saved case selection and repeat count are used by default. Completed answers and metrics are retained, while unfinished or errored work is retried as part of that same logical experiment.

Resume verifies the trial matrix, original case evidence, response hashes, saved score validity and evaluation signature. Changed configuration, prompts/code, dataset, model digests, server or relevant package versions require a new run. Changing repeat count or selected case IDs also requires a new run. An interrupted model normally expires after its short keep-alive period; if Ollama still reports a loaded model, let that request finish/unload before resuming.

## Interpret stability separately from quality

- **Exact stable:** all planned generations completed and their original response text is identical.
- **Normalized stable:** all generations completed and text matches after whitespace normalization and case folding. This is a text comparison, not semantic equivalence; punctuation and words are preserved.
- **All repeats quality pass:** every repeat completed the three existing metrics and deterministic checks, and all passed. An identical wrong answer can have exact stability `true` and this value `false`.
- **Metric decisions stable:** the judge's three pass/fail decisions match across repeats. Identical answers with different metric decisions can indicate judge variability rather than answer-model variability.

Missing/errored generations cannot establish text stability, so the per-case stability value is `null` until all requested answers exist. Missing/errored evaluations make the all-repeats quality result `null`. The report retains error, incomplete and cleanup counts. Metric averages use completed evaluations and show their denominators.

Temperature zero and the same seed test repeatability under fixed settings; they do not establish robustness to different prompts, seeds or sampling configurations. Warm requests may benefit from model/prompt caching, so timings do not measure independent cold starts. The small local judge remains fallible, and automated passes are not established model accuracy. The [original ten-case pilot manual review](pilot-review-findings.md) is complete. The nine consistency trials also have a completed manual review with 27 written reasons. Both reviews were conducted after prior findings were visible; independent blinded validation has not been performed. The pilot and repeated-response agreement rates remain separate because their observations overlap and are correlated.

The baseline pilot inputs, prompts, models and original results remain available separately. This feature adds a new experiment type rather than revising its saved measurements. The existing GitHub unit-test workflow automatically includes the new fake-client and reporting tests; actual Ollama runs stay local.

References: [Ollama chat requests](https://docs.ollama.com/api/chat), [model parameters](https://docs.ollama.com/modelfile), and [model lifecycle guidance](https://docs.ollama.com/faq).
