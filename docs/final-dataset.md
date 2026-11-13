# Final 50-case inputs

Prepared on 13 November 2026, after both development reviews and the [evaluation protocol freeze](evaluation-freeze.md). **No final model inference or final quality result exists yet.**

The [dataset](../data/final.json) contains 30 answerable SQuAD questions, 10 impossible SQuAD questions, five synthetic ambiguity cases and five synthetic embedded-instruction cases. Read the [final dataset card](../data/FINAL_DATASET_CARD.md), [custom fixtures](../data/final-custom-cases.json) and [manifest](../data/final-manifest.json).

## Validate the checked-in inputs

From the project terminal:

```powershell
python scripts/prepare_final_dataset.py validate
```

This verifies the frozen protocol/environment, final input schema, 30/10/5/5 composition, references/spans, attribution, all pilot exclusions, unique contexts, synthetic fixture identity and the manifest's content/dependency fingerprints. It needs the checked-in evidence and installed pinned packages, but not the downloaded SQuAD file or a running Ollama service. It makes no model calls and writes no result files.

The summary should show **50 cases, 50 distinct contexts, 35 SQuAD articles**, and `model_inference_performed: false`. The dataset fingerprint is:

`045889ac4e7b2390fa1d465deae1c710ab6b3caa7196c80087e3ff5ed0104747`

When the publisher snapshot is available locally, also verify that the entire selection reproduces:

```powershell
python scripts/prepare_final_dataset.py validate --source data/raw/dev-v2.0.json
```

This checks the pinned source bytes and rebuilds the expected inputs in memory. It compares all selected questions, full contexts, answer annotations, synthetic fixtures, metadata and list order. `source_reproduction_checked` then becomes `true`. Without `--source`, the summary correctly reports `false`; that describes the scope of this invocation, not a missing rating or a model-quality failure.

Exit **0** means validation/preparation succeeded; exit **2** reports invalid/missing inputs, a protocol mismatch, a nonmatching source or manifest, or an attempted overwrite. A failed check does not trigger model execution.

## How the inputs were selected

The source is the same pinned SQuAD 2.0 publisher dev snapshot as the pilot. Pilot IDs and all ten pilot context hashes are excluded before sampling. Complete contexts must contain 150–650 UTF-8 bytes, questions at most 180 bytes and deduplicated reference JSON at most 160 bytes. No paragraph is truncated. Original question wording, typos, every answer span and reference alias are preserved. Plausible answers on impossible questions are provenance only; the reference is exactly `INSUFFICIENT_CONTEXT`.

The fixed `final-selection-v1` recipe sorts original IDs, then uses a local Python random generator with seed **42** to shuffle each category. It selects 30 answerable cases first, then 10 impossible cases. Each choice takes the first remaining eligible shuffled candidate from an article with the lowest selection count. Previously selected contexts cannot be reused. The source has 35 articles, so all 35 are represented: 30 occur once and five occur twice, using different contexts. Article overlap with the pilot is allowed; source IDs and complete contexts are separate. This does not establish statistical independence or freedom from model pretraining exposure.

The five ambiguity fixtures expect abstention. The five embedded-instruction fixtures expect the stated fact and treat the quoted command as context data. These are **AI-assisted synthetic project fixtures**, not SQuAD questions or human-review ratings. Their intended answers and scenario explanations are included in the fixture file. They account for the ten custom cases; all 40 SQuAD questions and reference annotations remain publisher-provided. There are 15 abstention expectations overall.

Selection uses source/input structure and the declared recipe, with no answer-model outputs, judge grades or pass rates. The fixed short-context limits make the sample feasible on the laptop and limit representativeness. An offline preflight checks every answer prompt and constructs the metric prompts with the existing 400-character placeholder response; they fit the unchanged profiles. Actual generated judge prompts remain subject to the runtime budget check. This is not a live-model performance measurement.

## Reproduce without replacing selected data

The publisher source is cached in ignored `data/raw/dev-v2.0.json`. If it is absent in a fresh checkout, download it before preparation:

```powershell
New-Item -ItemType Directory -Force data/raw | Out-Null
Invoke-WebRequest -Uri "https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json" -OutFile data/raw/dev-v2.0.json
```

The required source SHA-256 is `80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8`. Preparation rejects a different snapshot. No network download is performed by the preparation or validation command itself.

The committed `data/final.json` and `data/final-manifest.json` already exist. Reproduce into a fresh ignored directory:

```powershell
python scripts/prepare_final_dataset.py prepare --output-dir results/runs/final-dataset-reproduction-01
python scripts/prepare_final_dataset.py validate --dataset results/runs/final-dataset-reproduction-01/final.json --manifest results/runs/final-dataset-reproduction-01/final-manifest.json --source data/raw/dev-v2.0.json
```

For initial selection when neither output exists, `python scripts/prepare_final_dataset.py prepare` writes the default pair in `data/`. If either output already exists, the command refuses to overwrite it. The manifest binds the complete ordered inputs, pilot, synthetic fixture packet, source snapshot, recipe/seed and protocol-freeze fingerprint. Canonical JSON hashing ignores whitespace, key order and a UTF-8 BOM; values and list order remain significant. Windows line-ending conversion does not change this identity.

## Next step

The existing `run_evaluation.py` still runs the ten-case pilot. Its loader deliberately rejects the final phase. Do not point that runner at the 50-case file or change the frozen model/metric settings to make it run.

The next increment adds the final runner and final report support. Before inference it must validate these exact inputs/manifest, invoke the protocol check, inspect actual local model digests and server version, preflight prompts, and record the dataset and freeze fingerprints in the run. Generation and judging remain sequential with model cleanup and checkpointed outputs. The protocol-only checker still reports `final_dataset_frozen: false` because it does not perform this separate dataset validation; the new dataset command provides that check.

Final outputs belong in a new run directory, not in the selected input file. Keep failures and execution errors visible. A later change to selected inputs or evaluation settings requires an explicit new version and explanation; do not replace these inputs in response to model outcomes.
