# Pilot review findings

Ibne completed a manual review of all ten saved development-pilot answers: **30 human pass/fail decisions**, with no missing or uncertain ratings. The human reviewer and original local LLM judge agree on **25/30 decisions (83.3%)**. The human decisions match the earlier AI assistant ratings on **30/30 decisions (100%)**.

The primary comparison is human versus the local judge. The earlier assistant review retains AI authorship and is a secondary reference. Prior AI assessments and judge findings had been seen, so this manual review was **non-blinded**. Written human rationales were not collected; the worksheet uses an explicit optional-reason policy and empty reason strings. Rating coverage and written-reason coverage are reported separately.

## Evidence files

| File | Contents |
| --- | --- |
| [Completed human worksheet](../results/examples/pilot-human-review.json) | All ten cases and 30 user-supplied verdicts, with declared prior exposure and reason policy |
| [Human comparison JSON](../results/examples/pilot-human-comparison.json) | All paired decisions, original scores/reasons, five disagreements and evidence fingerprints |
| [Readable human comparison](../results/examples/pilot-human-comparison.md) | Agreement tables, all decisions, disagreement details and limitations |
| [Earlier assistant review JSON](../results/examples/pilot-assistant-review.json) | AI-authored ratings and explanations with full supplied contexts |
| [Readable assistant review](../results/examples/pilot-assistant-review.md) | Case table and explanations for the earlier AI assessment |
| [Earlier AI-only comparison](../results/examples/pilot-assistant-comparison.md) | Preserved assistant-versus-judge analysis made before the manual review |

The source is the [original pilot result](../results/examples/pilot-results.json), run `pilot-20261110T062839549380Z`, using `human-review-v1`. Original questions, contexts, references, responses, judge scores and explanations are preserved. The human worksheet, source results and AI reference each have a canonical SHA-256 fingerprint in the new comparison report.

## Agreement and coverage

| Metric | Matching decisions | Paired decisions | Human/judge agreement |
| --- | ---: | ---: | ---: |
| Answer relevancy | 8 | 10 | 80.0% |
| Correctness | 9 | 10 | 90.0% |
| Groundedness | 8 | 10 | 80.0% |
| Overall | 25 | 30 | 83.3% |

The denominator is 30 metric decisions, rather than ten case outcomes. Six cases pass all three criteria in the manual review; four have a failed criterion. The original pipeline's two passes and eight flags use its machine metrics and deterministic checks and remain unchanged. Agreement is not model accuracy or proof that either reviewer is correct.

## Investigated disagreements

| Case | Metric | Evidence-based finding |
| --- | --- | --- |
| Protein transport | Relevancy | Statement extraction changes who shuts down host defenses, then grades the rewritten claim. |
| Rhine boundary | Relevancy | The response supplies the western boundary and a contextual alias, but the judge penalizes the alias as irrelevant. |
| Steam turbine | Groundedness | The human accepts the passage's national attribution; the judge requires explicit inventor nationality. This is interpretation-sensitive, rather than a proven judge error. |
| University of Chicago Press | Groundedness | The judge accepts an accreditation claim transferred from the university to its Press. |
| Support desk opening | Correctness | The saved answer is exactly `09:00`, while the failing explanation invents `09:0:0`. |

These investigation explanations are the saved project analysis, not quotations of human-written rationales. The manual review supplies verdicts only. Read the original evidence and the earlier AI analysis to assess each explanation.

## Reproduce the comparison offline

From the project folder, use the published evidence and a fresh output directory:

```powershell
python scripts/review_judge.py compare --results results/examples/pilot-results.json --review results/examples/pilot-human-review.json --assistant-review results/examples/pilot-assistant-review.json --output-dir results/reviews/pilot-human-reproduction-01
```

The command makes no model calls. It validates the source, case evidence, rubric, human metadata and AI reference, then computes coverage, agreement and content fingerprints. Existing reviews and reports are never overwritten. Local working reports remain ignored by Git; the deliberate examples above are publishable files.

## Calibration status and next checkpoint

The manual ten-case review is complete. Independent blinded validation remains outstanding, and the nine separate consistency trials have not received their own human ratings. The small sample, related metrics, missing written rationales, prior exposure and shared model-family bias limit interpretation; 100% agreement with the earlier AI review is not independent confirmation.

The answer model remains `qwen2.5:1.5b`, and the judge remains `qwen3:4b`. Prompts, thresholds, CPU settings and original model outputs are unchanged. Before preparing the separate final 50-case set, record whether the baseline judge is retained or a separately versioned pilot calibration is attempted. Exclude pilot source IDs and contexts, and freeze settings before inspecting final-set outcomes.

See the [human review guide](human-validation.md) for reason policies and review metadata. SQuAD material retains its [dataset attribution](../data/DATASET_CARD.md) and [CC BY-SA 4.0 notice](../data/LICENSE-SQUAD.txt).
