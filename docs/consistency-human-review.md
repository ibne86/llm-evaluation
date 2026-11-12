# Human review of consistency responses

Ibne completed the human review of the saved consistency experiment: **three questions, nine responses, 27 pass/fail judgments and 27 written reasons**. The human reviewer and local judge agree on **24/27 decisions (88.9%)**, with three disagreements. Prior findings had been seen, so the review was non-blinded. Original model outputs, scores and the ten-case pilot review remain unchanged.

## Published review results

| Evidence | Contents |
| --- | --- |
| [Completed human worksheet](../results/examples/consistency-human-review.json) | All nine trial rows, 27 human judgments and the reviewer's written reasons |
| [Comparison JSON](../results/examples/consistency-human-comparison.json) | Paired decisions, coverage, original scores/reasons, disagreements and input fingerprints |
| [Readable comparison](../results/examples/consistency-human-comparison.md) | Trial-specific decisions and human-versus-local-judge findings |

| Metric | Matching decisions | Paired decisions | Agreement |
| --- | ---: | ---: | ---: |
| Relevancy | 7 | 9 | 77.8% |
| Correctness | 8 | 9 | 88.9% |
| Groundedness | 9 | 9 | 100.0% |
| Overall | 24 | 27 | 88.9% |

County-answer relevancy differs on repeats 2 and 3: the human treats a wrong numerical answer as on topic, while the judge rejects it because the context cannot supply the count. Opening-time correctness differs on repeat 1: the saved answer is `09:00`, but the failing explanation refers to `09:0:0`. All original scores and explanations are preserved, and the human reasons remain exactly as submitted.

The human review passes all three criteria on six trials and flags the three county-answer trials. This differs from the original automated five passes and four flags. Rating completeness, quality outcomes and agreement are separate quantities. The three repeated questions and their metrics are correlated; these results are not independent accuracy estimates or a replacement for the separate ten-case pilot report.

Reproduce the completed comparison into a fresh directory:

```powershell
python scripts/review_judge.py compare --results results/examples/consistency-results.json --review results/examples/consistency-human-review.json --output-dir results/reviews/consistency-human-reproduction-01
```

## Identify each saved response

The command recognizes a source with `run_type: response_consistency` and validates its full planned trial matrix. Every response needs completed generation, a matching response hash, and three valid completed judge metrics. A quality failure is reviewable; incomplete execution is rejected.

Each worksheet row contains the original `case_id`, its integer `repeat`, and a fixed `trial_id` such as `pilot-custom-instruction-01::repeat-2`. The original question, full context, acceptable answers and saved response appear alongside it. Identical response text on multiple repeats still produces separate rows. Judge grades and explanations are omitted from the worksheet.

Repeated-response packets use schema version 2 and retain the complete source fingerprint. The existing ten-case pilot packets keep schema version 1. The scoring rubric remains `human-review-v1`; the criteria and thresholds are unchanged.

## Prepare an unlabeled worksheet

From the project folder:

```powershell
python scripts/review_judge.py prepare --results results/examples/consistency-results.json --output results/reviews/consistency-human-review.json
```

The command refuses to overwrite an existing file. If the initial worksheet already exists, open it for review or choose another output filename for a new round. Written reasons are required by default. `--reason-policy optional` is available when a review deliberately collects verdicts without explanations; missing written reasons are then reported separately.

## Enter your own review

Open `results/reviews/consistency-human-review.json` in the editor. Set `reviewer` and declare actual `prior_exposure`: `none` or `scores_or_findings_seen`. Ibne completed the published review with `reviewer: Ibne`, `reviewer_type: human` and `prior_exposure: scores_or_findings_seen`. Newly prepared worksheets start with all verdicts `null`; keep the completed review unchanged and choose another filename for a new round.

Read each row's question, full context, expected answers and actual response. Enter `pass`, `fail` or `uncertain` for relevancy, correctness and groundedness, with your own written reason for each entered judgment. Use the [same rubric as the pilot](human-validation.md). Leave `null` for anything not yet reviewed.

Assess each saved repeat separately. You may reach the same decision for identical answers, but ratings are never filled or copied automatically. Preserve the case IDs, repeat numbers, trial IDs, evidence, instructions, schema, rubric and fingerprints. The comparison command validates all of them. Optional `review_status` metadata, if supplied, must match the status computed from the ratings; it is not needed for this worksheet.

Reviewing the same question three times does not create three independent questions. Prior exposure remains disclosed; this workflow does not claim that the review is blinded or independent.

## Compare with the original local judge

After saving the ratings, use a fresh output directory:

```powershell
python scripts/review_judge.py compare --results results/examples/consistency-results.json --review results/reviews/consistency-human-review.json --output-dir results/reviews/consistency-human-comparison-01
```

This writes `comparison.json` and `comparison.md`, without rerunning models or replacing prior files. The source must be the same saved JSON used to prepare the packet. Inputs, outputs and local working reviews remain separate.

## Read coverage before agreement

Reports distinguish:

- **Selected questions:** three original case IDs.
- **Selected trials:** nine responses identified by case ID and repeat number.
- **Fully reviewed trials:** responses with three explicit pass/fail judgments.
- **Fully reviewed questions:** questions whose three trials all have complete pass/fail judgments.
- **Possible paired decisions:** 27 human/judge metric decisions.
- **Paired decisions:** only human `pass` or `fail` ratings; uncertain and unreviewed ratings are excluded.
- **Written-reason coverage:** reported separately from rating coverage.

Overall agreement is matching human/judge decisions divided by paired decisions. Each metric has at most nine pairs. With no human ratings, status is `not_started` and agreement is `null`. Missing or uncertain judgments produce `partial`; all 27 explicit pass/fail judgments produce `complete`. Agreement need not be high for a review to be complete.

Every comparison and disagreement retains `case_id`, `repeat`, and `trial_id`. The report shows the original score, threshold, judge reason and human explanation for the exact repeat. A repeated answer can receive changing judge grades; preserving repeat identity lets you inspect that behavior without mixing observations.

Original machine scores and raw run summaries remain frozen, including their review status at recording time. Human findings live in the separate comparison. Keep initial human labels and record later adjudication in a new packet/report.

## Publication and limits

Working reviews under `results/reviews/` are ignored by Git. The completed review and comparison above are deliberate publishable copies in `results/examples/`; the original local worksheet and reports are preserved. For a future round, publish examples only after the human has entered and checked the judgments. Preparing a worksheet or running synthetic tests alone does not complete human validation.

The original [consistency result](../results/examples/consistency-results.json) and [experiment guide](response-consistency.md) remain available. The repeated observations and metrics are correlated, the sample is small, and the local judge remains fallible. Agreement is not model accuracy. An independent blinded assessment would provide additional validation; it is separate from implementing this workflow.
