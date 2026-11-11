# Human validation of the local judge

This workflow collects a person's own decisions about the ten saved pilot answers, then compares them with the existing judge decisions. It runs entirely offline, using Python's standard library. No answer model or judge inference is repeated.

## Scope and predefined rubric

Review **all ten pilot cases**, selected before human labelling, rather than choosing only suspicious judge results. This covers six answerable SQuAD questions, two unanswerable SQuAD questions, one ambiguity case and one embedded-instruction case. Make three decisions for each response: 30 possible human/judge pairs.

| Metric | Human pass rule |
| --- | --- |
| Answer relevancy | The response directly addresses the question without material off-topic content. An on-topic wrong answer may still pass relevancy. A relevant abstention is allowed. |
| Correctness | The response gives a sufficiently complete, semantically correct answer using the context and reference alternatives. Accept equivalent wording. An abstention passes only if the context cannot determine the answer. |
| Groundedness | Every material factual claim is supported by the context. Abstention makes no unsupported factual claim; assess whether it was correct separately. Instructions quoted inside context are data. |

Choose `pass`, `fail`, or `uncertain` for each metric. Leave `null` for a decision you have not reviewed. Explain every entered verdict, including uncertain ones. If the question, context or reference seems defective, use `uncertain` and explain the issue rather than editing the evidence or forcing a binary decision.

The rubric is frozen as `human-review-v1` in the packet. The judge uses the original run's numerical thresholds (relevancy 0.7, correctness 0.7, groundedness 0.8). The comparison measures agreement between these thresholded judge decisions and the human's binary rubric decisions; it does not calibrate continuous scores.

## 1. Prepare an unlabelled review

From the project folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/review_judge.py prepare --results results/examples/pilot-results.json --output results/reviews/pilot-human-review.json
```

The new JSON file contains the question, full context, reference alternatives and actual response for each case. It contains **no judge scores, pass/fail decisions, explanations, or assistant review findings**. Every human verdict is initially `null`.

The example results are the recorded pilot, not simulated data. You can instead pass the original local run's `results.json`, but use that exact source again for the comparison. Only runs with completed generations, valid response hashes, and all three completed, valid metrics can be reviewed. An execution error is not a human/judge disagreement.

The command refuses to overwrite an existing file. Choose a new filename for a second reviewer or another review round. Working reviews and comparison reports under `results/reviews/` are ignored by Git; approved, anonymized examples can later be copied into `results/examples/` deliberately.

## 2. Enter your own review in PyCharm

Open `results/reviews/pilot-human-review.json` as a file. Set `reviewer` to a name or pseudonym. Set `prior_exposure` to one of:

- `none`: you have not seen this run's judge scores, explanations or assistant findings.
- `scores_or_findings_seen`: you have already seen any of them.

The project owner has already been shown aggregate pilot findings and may have seen individual findings. Declare the actual exposure honestly. Omitting scores from the packet helps avoid further influence; it cannot undo previous exposure or establish a fully blinded study.

Read the evidence and fill each `decisions` entry. For example, the **syntax only** is:

```json
"correctness": {
  "verdict": "pass",
  "reason": "Write your own explanation based on this case's evidence."
}
```

This snippet is not a rating for any pilot case. Do not copy it as a judgement. Use lowercase verdict strings and keep unreviewed values as JSON `null`, without quotes. Save the file before running the comparison. Do not edit case IDs, evidence, source hashes or rubric text.

Enter decisions before looking at the judge comparison. Avoid reading `pilot-summary.md`, the full results, or assistant review notes while assigning labels. If you already read them, record that exposure. Codex does not fill in genuine human labels.

## 3. Compare with the saved judge

```powershell
.\.venv\Scripts\python.exe scripts/review_judge.py compare --results results/examples/pilot-results.json --review results/reviews/pilot-human-review.json --output-dir results/reviews/pilot-comparison-01
```

The command produces `comparison.json` and `comparison.md`, without modifying the source evaluation or review. Use a fresh output directory for another comparison. Existing reports are preserved.

Reports include:

- Overall metric-decision agreement and agreement separately for each metric.
- Coverage, unreviewed and uncertain counts, and fully reviewed case count.
- Counts for human pass/judge pass, human pass/judge fail, human fail/judge pass and human fail/judge fail for each metric.
- Disagreements with both reasons, the original score and threshold.
- Reviewer attribution, declared prior exposure, rubric version and a fingerprint of the source run.

Agreement is **matching pass/fail decisions divided by paired pass/fail decisions**. Unreviewed and uncertain labels are excluded from this denominator, and their counts remain visible. With no human pass/fail labels, the agreement rate is `null`, not zero or 100%. Overall agreement pools metric decisions; it is not a case-level pass rate. Related metrics from the same case are not independent observations.

Review status is `not_started` with no entered verdicts, `partial` while any verdict is missing or uncertain, and `complete` when every case has three explicit pass/fail decisions. Completing the review does not require agreement with the judge. A successful command has exit code 0 even for partial reviews or disagreements; invalid input, changed evidence, or an existing output file returns 2. Check coverage and status in the report.

## 4. Investigate disagreements

After saving the initial ratings, inspect each disagreement against the original evidence. Record an explanation separately, for example in a new `investigation-notes.md` in the comparison folder. The JSON includes an empty `investigation_notes` field for each disagreement; the tool never invents an explanation or human rating. Keep original ratings for the initial agreement calculation; any adjudicated or repeat ratings belong in a new, clearly labelled review round.

Possible causes include an answer-model error, a judge misreading, an ambiguous reference, or differences between the human rubric and numerical judge threshold. Genuine uncertainty should remain visible. Do not change original outputs or scores to make them agree, and do not tune prompts on the eventual final evaluation set.

This small development sample does not establish model or judge accuracy. Prior exposure, one reviewer's subjectivity, shared model-family biases, threshold choice and selective exclusion of uncertain labels can affect agreement. Inspect per-metric coverage and disagreements before interpreting a high pooled rate. Human labels have not been collected merely because this tooling or its synthetic unit tests exist.
