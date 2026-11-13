# Ten-case development pilot

This is a development set for implementing and reviewing the evaluation harness. It is not the final 50-case evaluation set and is not a training dataset.

## Sources and license

- SQuAD 2.0, Rajpurkar, Jia and Liang (2018): https://rajpurkar.github.io/SQuAD-explorer/
- Hugging Face dataset card: https://huggingface.co/datasets/rajpurkar/squad_v2
- Publisher download: https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json
- Download SHA-256: `80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8`
- Data license: CC BY-SA 4.0. See [LICENSE-SQUAD.txt](LICENSE-SQUAD.txt).

The existing publisher dev/validation split is a source-selection convenience. No new training/validation/test split is created because no model is trained.

## Reproducible selection

`scripts/prepare_dataset.py` selects exactly six answerable and two unanswerable questions. It sorts original IDs, shuffles with Python's local random generator seeded at 42, and takes the first eligible question from each unused article. All eight SQuAD cases come from different articles.

Eligibility is fixed before generation: complete contexts of 150–650 UTF-8 bytes, questions up to 180 UTF-8 bytes, and deduplicated reference-answer JSON up to 160 UTF-8 bytes. The source snapshot has 2,219 eligible answerable and 2,335 eligible unanswerable questions. Selection does not inspect model responses or scores. The short-context restriction makes this pilot practical on the laptop and limits representativeness.

Questions and contexts are unchanged, including source typos. Original question IDs, article titles and every original answer span are preserved. Expected answer aliases are deduplicated without changing their wording. Plausible answers for impossible questions are retained only as provenance and are never supplied as expected answers.

| Category | Article / scenario | Original ID |
| --- | --- | --- |
| answerable | Civil disobedience | 5728d9403acd2414000e001b |
| answerable | Immune system | 572a019f3f37b31900478645 |
| answerable | Rhine | 572f57c704bcaa1900d7686e |
| answerable | Amazon rainforest | 572a03a06aef0514001551ad |
| answerable | Steam engine | 5711658e50c2381900b54ad6 |
| answerable | Huguenot | 57107c24a58dae1900cd69ec |
| unanswerable | Southern California | 5ad01f0f77cf76001a686ac3 |
| unanswerable | University of Chicago | 5acf900177cf76001a685281 |
| custom | Ambiguous identity; abstention expected | pilot-custom-ambiguity-01 |
| custom | Quoted misleading instruction; factual answer expected | pilot-custom-instruction-01 |

The two custom fixtures are project-authored and also licensed CC BY-SA 4.0. The full 10-case set includes three abstention expectations: two SQuAD impossible questions and one custom ambiguity case.

## Evaluation separation

`pilot.json` is immutable test input. Actual responses and scores belong in run outputs linked by case ID. The metadata records source IDs and context hashes excluded from the separately prepared [final 50-case set](FINAL_DATASET_CARD.md). The pilot's original `final_evaluation_prepared: false` is a historical creation-time record and is preserved. Final inputs and their fingerprints live in separate files. Avoid tuning against final evaluation outcomes.

## Reproduction

In a fresh checkout with no `pilot.json`, run the preparation script with `--download`. It fetches the publisher JSON, verifies its format and answer spans, and records the content hash. If the hash differs from the snapshot above, investigate before claiming an identical reproduction. The script refuses to silently replace an existing selected pilot.

The raw 4 MB source download stays in ignored `data/raw`. The small licensed pilot, this card, the source hash and the license notice are intended repository deliverables.
