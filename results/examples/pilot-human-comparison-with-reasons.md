# Human versus local LLM judge review

- Source run: `pilot-20261110T062839549380Z`.
- Reviewer: Ibne.
- Status: complete; fully reviewed cases: 10/10.
- Prior exposure: scores_or_findings_seen.
- Paired metric decisions: 30/30; agreement: 25/30 (83.3%).
- Unreviewed: 0; uncertain: 0.
- Written reasons: 30/30; reason policy: optional.

| Metric | Paired | Agreements | Agreement rate | Unreviewed | Uncertain |
| --- | ---: | ---: | ---: | ---: | ---: |
| answer_relevancy | 10 | 8 | 80.0% | 0 | 0 |
| correctness | 10 | 9 | 90.0% | 0 | 0 |
| groundedness | 10 | 8 | 80.0% | 0 | 0 |

## Individual decisions

| Case | Metric | Human | Local judge |
| ---: | --- | --- | --- |
| 1 | answer_relevancy | pass | pass |
| 1 | correctness | pass | pass |
| 1 | groundedness | pass | pass |
| 2 | answer_relevancy | pass | fail |
| 2 | correctness | pass | pass |
| 2 | groundedness | pass | pass |
| 3 | answer_relevancy | pass | fail |
| 3 | correctness | pass | pass |
| 3 | groundedness | pass | pass |
| 4 | answer_relevancy | pass | pass |
| 4 | correctness | fail | fail |
| 4 | groundedness | pass | pass |
| 5 | answer_relevancy | pass | pass |
| 5 | correctness | pass | pass |
| 5 | groundedness | pass | fail |
| 6 | answer_relevancy | pass | pass |
| 6 | correctness | pass | pass |
| 6 | groundedness | pass | pass |
| 7 | answer_relevancy | pass | pass |
| 7 | correctness | fail | fail |
| 7 | groundedness | fail | fail |
| 8 | answer_relevancy | pass | pass |
| 8 | correctness | fail | fail |
| 8 | groundedness | fail | pass |
| 9 | answer_relevancy | pass | pass |
| 9 | correctness | fail | fail |
| 9 | groundedness | fail | fail |
| 10 | answer_relevancy | pass | pass |
| 10 | correctness | pass | fail |
| 10 | groundedness | pass | pass |

## Disagreements

### pilot-squad-572a019f3f37b31900478645 / answer_relevancy

Question: In a type III secretion system, proteins are transported to the host cell in order to do what?

Actual response: In a type III secretion system, proteins are transported to the host cell to shut down host defenses.

Human: **pass**. It answers the actual question: why those proteins get sent into the host cell.

Judge: **fail**, score 0.5, threshold 0.7. The score is 0.50 because the output incorrectly states that the type III secretion system shuts down host defenses, which is irrelevant to the question about the purpose of protein transport to the host cell. The score cannot be higher because the output fails to address the actual question about protein function, focusing instead on a system function unrelated to the query's intent.

### pilot-squad-572f57c704bcaa1900d7686e / answer_relevancy

Question: What is the delta in the Rhine delimited in the west by?

Actual response: The delta in the Rhine is delimited in the West by the Alter Rhein ("Old Rhine").

Human: **pass**. It names the western boundary, which is what was asked. The "Old Rhine" in brackets is just a helpful translation.

Judge: **fail**, score 0.5, threshold 0.7. The score is 0.50 because the output incorrectly states that the Alter Rhein is known as the Old Rhine without addressing the west boundary of the Rhine delta, which is the core question. The score cannot be higher as the output fails to provide the west boundary information directly, making it irrelevant to the query.

### pilot-custom-instruction-01 / correctness

Question: At what time does the support desk open?

Actual response: 09:00

Human: **pass**. 09:00 is on the list of accepted answers and matches the office policy.

Judge: **fail**, score 0.0, threshold 0.7. The response '09:0:0' is incorrect as it does not match any expected outputs. The context specifies the support desk opens at 09:00, but the actual output has a typo (09:00 vs 09:0:0), making it invalid. Expected outputs include '09:00', '9:00 AM', and '9 am', so the response is wrong.

### pilot-squad-5711658e50c2381900b54ad6 / groundedness

Question: People of what nationality invented the steam turbine?

Actual response: British

Human: **pass**. The passage calls the steam turbine a British invention. The question only asks about nationality, so that's enough, and the answer doesn't say anything about a specific inventor.

Judge: **fail**, score 0.3, threshold 0.8. The Actual Output claims British nationality for the steam turbine inventor, but Context states it was a British invention without specifying nationality. The claim is unsupported as Context only mentions British origin without confirming nationality.

### pilot-squad-5acf900177cf76001a685281 / groundedness

Question: By which Commission is the University of Chicago Press accredited?

Actual response: The University of Chicago Press is accredited by The Higher Learning Commission.

Human: **fail**. The answer takes a claim about the university and pins it on the Press. The Press being part of the university doesn't mean the passage says it's accredited too.

Judge: **pass**, score 1.0, threshold 0.8. The Actual Output correctly states the accreditation body as The Higher Learning Commission, which is directly supported by the Context. The Context explicitly mentions 'The university is accredited by The Higher Learning Commission,' so the claim is fully supported with no unsupported claims. This aligns perfectly with the evaluation steps, scoring 10.


## Interpretation

Agreement is matching human/judge metric decisions divided by explicit paired decisions, not model accuracy or proof of judge validity. Unreviewed/uncertain labels are excluded and reduce coverage. These pilot cases are development data, not a representative benchmark. Prior exposure to scores/findings can bias human ratings. Keep the original labels; record disagreement investigations separately.

This review was non-blinded: prior scores or findings had been seen. Independent blinded validation remains outstanding.

## Evidence

- [Original pilot results](pilot-results.json)
- [Human review worksheet](pilot-human-review-with-reasons.json)

## Evidence fingerprints

- Source results: `638e93e1b6a6a9d50ba65f18a2b50d997c0bda346edd2b801c3f28fe6ed63406`.
- Human worksheet: `7783771d84896179a2e15fbeb8b0d433c91a66fbfbac850264f5cd674f136234`.
