# Pilot review findings

Ibne completed a manual review of all ten saved development-pilot answers: **30 human pass/fail decisions**, with no missing or uncertain ratings. The human reviewer and original local LLM judge agree on **25/30 decisions (83.3%)**.

The comparison is human versus the local judge. Prior AI assessments and judge findings had been seen, so this manual review was **non-blinded**. Ibne subsequently added written rationales for all 30 decisions in a separate follow-up worksheet. The original ratings and earlier worksheet without reasons are preserved. The follow-up retains the optional-reason collection policy, with actual written-reason coverage of 30/30. Rating coverage and written-reason coverage are reported separately.

## Evidence files

| File | Contents |
| --- | --- |
| [Human worksheet with reasons](../results/examples/pilot-human-review-with-reasons.json) | All ten cases and 30 user-supplied verdicts with written explanations, prior exposure and reason policy |
| [Human comparison JSON with reasons](../results/examples/pilot-human-comparison-with-reasons.json) | All paired decisions, original scores/reasons, five disagreements and evidence fingerprints |
| [Readable human comparison with reasons](../results/examples/pilot-human-comparison-with-reasons.md) | Agreement tables, all decisions, human reasons, disagreement details and limitations |
| [Initial human worksheet](../results/examples/pilot-human-review.json) | Preserved first submission: 30 verdicts without written reasons |
| [Initial human comparison](../results/examples/pilot-human-comparison.md) | Historical comparison of the first submission, before written reasons were added |

The source is the [original pilot result](../results/examples/pilot-results.json), run `pilot-20261110T062839549380Z`, using `human-review-v1`. Original questions, contexts, references, responses, judge scores and explanations are preserved. The human worksheet and source results each have a canonical SHA-256 fingerprint in the comparison report.

## Agreement and coverage

| Metric | Matching decisions | Paired decisions | Human/judge agreement |
| --- | ---: | ---: | ---: |
| Answer relevancy | 8 | 10 | 80.0% |
| Correctness | 9 | 10 | 90.0% |
| Groundedness | 8 | 10 | 80.0% |
| Overall | 25 | 30 | 83.3% |

The follow-up has 30/30 written reasons, compared with 0/30 in the preserved initial version. Its pass/fail verdicts are unchanged. The denominator is 30 metric decisions, rather than ten case outcomes. Six cases pass all three criteria in the manual review; four have a failed criterion. The original pipeline's two passes and eight flags use its machine metrics and deterministic checks and remain unchanged. Agreement is not model accuracy or proof that either reviewer is correct.

## Investigated disagreements

| Case | Metric | Evidence-based finding |
| --- | --- | --- |
| Protein transport | Relevancy | Statement extraction changes who shuts down host defenses, then grades the rewritten claim. |
| Rhine boundary | Relevancy | The response supplies the western boundary and a contextual alias, but the judge penalizes the alias as irrelevant. |
| Steam turbine | Groundedness | The human accepts the passage's national attribution; the judge requires explicit inventor nationality. This is interpretation-sensitive, rather than a proven judge error. |
| University of Chicago Press | Groundedness | The judge accepts an accreditation claim transferred from the university to its Press. |
| Support desk opening | Correctness | The saved answer is exactly `09:00`, while the failing explanation invents `09:0:0`. |

The follow-up worksheet and comparison contain the human reviewer's own written reasons. The investigation summaries above remain saved project analysis and are distinct from those human explanations. Read both against the original evidence.

## Reproduce the comparison offline

From the project folder, use the published evidence and a fresh output directory:

```powershell
python scripts/review_judge.py compare --results results/examples/pilot-results.json --review results/examples/pilot-human-review-with-reasons.json --output-dir results/reviews/pilot-human-with-reasons-reproduction-01
```

The command makes no model calls. It validates the source, case evidence, rubric and human metadata, then computes coverage, agreement and content fingerprints. Existing reviews and reports are never overwritten. Local working reports remain ignored by Git; the deliberate examples above are publishable files.

## Calibration status and next checkpoint

The manual ten-case review and the [nine-response consistency review](consistency-human-review.md) are complete, with written reasons for all judgments. The latter has 24/27 matching judge decisions and is reported separately because the questions overlap and observations are correlated. Independent blinded review remains an additional validation option. The small sample, related metrics, prior exposure and shared model-family bias limit interpretation. Human/judge agreement does not establish accuracy or independent confirmation.

The [judge decision and evaluation freeze](evaluation-freeze.md) retain `qwen2.5:1.5b` and `qwen3:4b`, with the same prompts, rubric versions, thresholds and CPU settings. No judge calibration or new inference was performed for that decision. Original outputs remain preserved. The separate [final 50-case inputs](final-dataset.md) are now prepared and validated, with pilot IDs/contexts excluded and their hash recorded before inference. Final-runner integration and model evaluation are next.

See the [human review guide](human-validation.md) for reason policies and review metadata. SQuAD material retains its [dataset attribution](../data/DATASET_CARD.md) and [CC BY-SA 4.0 notice](../data/LICENSE-SQUAD.txt).
