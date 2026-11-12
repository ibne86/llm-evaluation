# Human review of consistency responses

This workflow reviews saved responses from the repeated-response experiment. The included run has **three questions, three repeats each, nine responses and 27 metric decisions**. Preparing the worksheet runs offline and leaves every human verdict unfilled. Model outputs, scores and the ten-case pilot review remain unchanged.

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

Open `results/reviews/consistency-human-review.json` in the editor. Set `reviewer` and declare actual `prior_exposure`: `none` or `scores_or_findings_seen`. Ibne has already seen experiment findings; the initial local worksheet records `Ibne`, `human`, and `scores_or_findings_seen`, with all 27 verdicts still `null`.

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

Working reviews under `results/reviews/` are ignored by Git. Once the human ratings are entered and checked, deliberately prepare publishable examples and update documentation. A worksheet or a synthetic unit test is not completed human validation.

The original [consistency result](../results/examples/consistency-results.json) and [experiment guide](response-consistency.md) remain available. The repeated observations and metrics are correlated, the sample is small, and the local judge remains fallible. Agreement is not model accuracy. An independent blinded assessment would provide additional validation; it is separate from implementing this workflow.
