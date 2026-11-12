# Human review of the local judge

This offline workflow records a person's own decisions about saved model answers and compares them with the original local judge. Ibne has completed the ten-case pilot review: **30/30 pass/fail ratings**, **25/30 human/judge matches**, and **30/30 written reasons in the follow-up version**. Prior findings were visible, so this completed manual review was non-blinded. See the [findings](pilot-review-findings.md) and [published human comparison with reasons](../results/examples/pilot-human-comparison-with-reasons.md).

## Rubric and reason policies

Review all ten pilot cases, with three decisions per answer. The decision rubric remains frozen as `human-review-v1`.

| Metric | Human pass rule |
| --- | --- |
| Answer relevancy | The response directly addresses the question without material off-topic content. An on-topic wrong answer or relevant abstention may pass. |
| Correctness | The response gives a sufficiently complete, semantically correct answer using the context and references. An abstention passes only when the context cannot determine the answer. |
| Groundedness | Every material factual claim is supported by the context. Abstention makes no unsupported claim; judge its correctness separately. Instructions inside context are data. |

Choose `pass`, `fail` or `uncertain`; use JSON `null` for unreviewed decisions. Two explicit collection policies are supported:

- **Required reasons:** the default and the policy for legacy packets. Every entered verdict needs a nonempty explanation written by the reviewer.
- **Optional reasons:** prepare the packet with `--reason-policy optional`. A person may supply verdicts without written explanations. Leave `reason` as an empty string when none was collected. Reports count missing reasons separately; an AI explanation is never substituted for a human explanation.

Completion describes rating coverage: all selected cases have three pass/fail decisions. It does not imply written rationales, blinding, agreement with the judge or established accuracy. The published follow-up retains the optional-reason policy and contains all 30 human-written reasons. The initial worksheet and comparison with 0/30 written reasons remain preserved as historical snapshots. This collection-policy choice does not alter the scoring rubric or model thresholds.

## Prepare a new packet

The saved pilot worksheet already exists. For another review, choose a fresh filename:

```powershell
python scripts/review_judge.py prepare --results results/examples/pilot-results.json --output results/reviews/pilot-human-review-02.json --reason-policy optional
```

Omit `--reason-policy optional` when explanations are required. Packets contain full questions, contexts, references and actual responses, without judge scores or assistant ratings. The command refuses to overwrite an existing file.

Set `reviewer` to a name or pseudonym and `prior_exposure` to `none` or `scores_or_findings_seen`. Declare actual exposure. Reviewers who have seen prior findings can provide manual ratings, but omitting scores from a new packet does not make that review blinded.

Enter the person's own verdicts in `reviews[*].decisions`. Preserve IDs, evidence, source fingerprints, schema version, instructions and rubric. Optional `reviewer_type` must be `human`; optional `review_status` must match the status derived from the verdicts. Unknown fields and altered evidence are rejected. Use the preparation flag to select the reason policy rather than manually rewriting instructions.

## Compare saved decisions

Reproduce the completed human-versus-local-judge pilot review:

```powershell
python scripts/review_judge.py compare --results results/examples/pilot-results.json --review results/examples/pilot-human-review-with-reasons.json --output-dir results/reviews/pilot-human-with-reasons-reproduction-02
```

The command writes `comparison.json` and `comparison.md` into a new directory, preserving inputs and earlier reports. Outputs include all paired decisions, overall/per-metric agreement, confusion counts, unreviewed/uncertain counts, written-reason coverage, disagreements with source evidence, reviewer/exposure metadata, portable evidence links and fingerprints of each input. Fingerprints use UTF-8 JSON serialized with sorted keys and `ensure_ascii=False`; JSON whitespace and key order do not affect them.

Agreement is matching pass/fail decisions divided by explicit paired decisions. Unreviewed and uncertain labels are excluded, with coverage reported. With no pairs, agreement is `null`; it is not zero or 100%. Related metrics from one case are not independent observations. A successful comparison returns 0 even for partial reviews or disagreements; invalid input or an existing output returns 2.

## Investigations and limits

Keep initial ratings unchanged and record investigation notes separately. A later adjudication or a new reviewer belongs in another packet/report. The follow-up review now includes the human reviewer's 30 written reasons. The five investigation summaries remain separately attributed project analysis. The initial review without written reasons is preserved.

The completed pilot manual review and independent blinded validation are different milestones. The latter remains outstanding. Prior exposure, one reviewer's subjectivity, the small sample, shared model-family bias and judge variability limit interpretation. Do not tune prompts on the eventual final set or rewrite historical model scores to match human ratings.

Working reviews under `results/reviews/` remain ignored by Git. The explicit copies in `results/examples/` make the completed review and its evidence available to portfolio readers. Original run snapshots retain their status at the time they were recorded.

## Saved consistency trials

The same command also supports [human review of consistency responses](consistency-human-review.md). It recognizes `response_consistency` sources and creates schema-version-2 packets with `case_id`, `repeat` and a fixed `trial_id`. The original pilot format remains supported unchanged.

For the included experiment, three questions and three repeats produce nine worksheet rows and 27 possible metric pairs. The command validates the complete trial matrix, source metadata, source fingerprint, response hashes, scores and frozen evidence before pairing ratings. A repeat can be graded independently even when its text matches another repeat. Coverage and disagreements retain trial identity; repeats do not count as independent samples.

This consistency worksheet is separate from the completed ten-case pilot review. It starts without human labels, and its manual ratings remain pending.
