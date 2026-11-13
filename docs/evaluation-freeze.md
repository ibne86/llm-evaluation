# Evaluation protocol freeze

Recorded on 12 November 2026 as **`context-qa-baseline-v1`**, before preparing the separate final 50-case dataset. The machine-readable record is [evaluation-freeze.json](../evaluation-freeze.json).

## Judge decision

Retain the original `qwen2.5:1.5b` answer model and `qwen3:4b` judge, with the existing prompts, metric rubrics, thresholds and CPU options. No judge calibration, threshold tuning, model substitution or new inference was performed for this decision.

The purpose is to carry a documented baseline from development into the final evaluation. Keeping it does not establish judge accuracy or resolve its known errors. Raising agreement on the same small, already reviewed sample would not demonstrate general improvement. Any later calibration should be a separately versioned development experiment, with its own evidence and comparison.

The decision uses the completed reviews:

| Development evidence | Human decisions with reasons | Matching judge decisions | Findings |
| --- | ---: | ---: | --- |
| [Ten-case pilot](../results/examples/pilot-human-comparison-with-reasons.md) | 30/30 | 25/30 (83.3%) | Relevance extraction/alias errors, a disputed nationality inference, an unsupported accreditation claim, and an incorrect grade for `09:00` |
| [Nine consistency responses](../results/examples/consistency-human-comparison.md) | 27/27 | 24/27 (88.9%) | County-answer relevance differs on repeats 2/3; `09:00` correctness differs on repeat 1 despite identical answer text and grading prompts |

Both reviews were non-blinded: prior findings had been seen. They overlap in questions, and repeated responses and criteria are correlated, so the rates are kept separate. They are agreement measurements, not accuracy estimates. Independent blinded review would provide additional validation; it is not a new requirement for completing the current manual reviews.

The original model responses, grades, human verdicts and written reasons remain unchanged. Final reporting must retain contradictory explanations and separate judge findings from human conclusions. Do not retry a completed quality failure until it passes or overwrite a prior grade; a deliberate re-evaluation gets a new run/version.

## Frozen settings

| Setting | Answer model | Judge |
| --- | --- | --- |
| Model | `qwen2.5:1.5b` | `qwen3:4b` |
| Context tokens | 2048 | 4096 |
| Output cap | 96 | 256 |
| Prompt batch | 32 | 16 |
| CPU threads | 4 | 4 |
| Temperature / seed | 0 / 42 | 0 / 42 |
| GPU layers | 0 | 0 |

Prompt version is `context-qa-v1`; metric rubric version is `pilot-rubrics-v1`. The judge uses `think=False` and sequential LLM evaluation. Thresholds remain relevancy **0.7**, correctness **0.7**, and groundedness **0.8**. The endpoint is `http://127.0.0.1:11434`, with a 120-second request timeout. Generation requests contain the system instruction plus context/question as user data. Abstention still requires the exact `INSUFFICIENT_CONTEXT` marker after trimming surrounding whitespace; semantic correctness and grounding are assessed separately.

The record includes the original model manifest digests and Ollama server version `0.40.16` from both completed runs. Python **3.12** is required; patch versions may differ. All 70 installed package versions must match the recorded dependency snapshot, including DeepEval `4.3.3`, Ollama client `0.6.3` and Pydantic `2.14.3`. A seed and temperature zero do not guarantee identical model judgments.

## Check the record offline

From the project terminal:

```powershell
python scripts/check_evaluation_freeze.py
```

The command reads files and installed package metadata. It makes no network requests, loads no model, writes no result files and does not regenerate the record. Exit **0** means the checked protocol/environment matches; exit **2** means a mismatch, missing input or invalid record, with an explanation.

The checker compares every configuration field except `dataset`. It checks the generation, judge-adapter and metric source files plus both dependency files, and fingerprints the pilot inputs, both original runs and their completed human worksheets/comparison JSON. Source/dependency text hashes normalize Windows/Linux line endings and a UTF-8 BOM. JSON evidence hashes ignore layout/key order but preserve all values and list order. Changes to a verdict, reason or response invalidate the evidence check.

For a future final configuration, only its dataset selector may differ:

```powershell
python scripts/check_evaluation_freeze.py --config final-config.toml
```

`final-config.toml` is an example future filename, not a file created by this increment. A passing check deliberately reports `ollama_runtime_checked: false` and `final_dataset_frozen: false`. It compares recorded model/version evidence; it does not inspect today's running service, downloaded weights, input contents or execution hardware. It also does not hash the entire runner/reporting implementation. The record's canonical fingerprint is printed so a future final run can bind itself to the exact reviewed record.

## Next implementation boundary

The existing pilot and consistency runners are unchanged and do not invoke this checker automatically. The [separate final dataset](final-dataset.md) is now prepared, with its own validator and manifest. Final-runner support is next: before inference, it must invoke the protocol and dataset checks, inspect the actual local server version and model digests, bind the freeze fingerprint and selected dataset hash to the run, and retain the sequential generation/unload/judging/unload policy. The protocol-only command still reports `final_dataset_frozen: false` because dataset validation is performed by the separate command.

The prepared final inputs contain **30 answerable SQuAD cases, 10 unanswerable SQuAD cases and 10 custom cases**, with documented seed/selection rules. Pilot source IDs and contexts are excluded; original source answers, provenance and attribution are preserved. The [dataset card and manifest](../data/FINAL_DATASET_CARD.md) record the separate input identity before any final model outcome. This original record continues to freeze the evaluation protocol; its content is unchanged.

Changes to a frozen prompt, rubric, model, dependency or threshold require an explicit new record and explanation. Do not regenerate hashes merely to silence a mismatch. New runner/reporting code should be reviewed and tested against this protocol; changes to its evaluation behavior require a new version. Settings must not be tuned after inspecting final outcomes and then presented as the original evaluation.
