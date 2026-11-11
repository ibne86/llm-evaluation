# Earlier AI assistant versus local judge comparison

This saved AI-only analysis predates the completed [manual human review](pilot-human-comparison.md).

Review owner: **Ibne**. Assessment source: **AI reviewer**. Review and comparison status: **complete**.

This report contains AI-generated review decisions. Human validation is a separate activity and was not performed by this review.

- Cases reviewed: 10; paired metric decisions: 30.

- Matching AI/judge decisions: 25/30 (83.3%); disagreements: 5.

- Human ratings recorded in the separate worksheet when this comparison was created: 0; human agreement rate: not computed.

- Source run: `pilot-20261110T062839549380Z`; rubric: `human-review-v1`.

- Prior judge findings were visible; this is not a blinded comparison.

The agreement percentage describes how often two reviewers reached the same pass/fail decision. It is not an accuracy score.

## Agreement by metric

| Metric | Matching decisions | AI/judge agreement |
| --- | ---: | ---: |
| answer_relevancy | 8/10 | 80.0% |
| correctness | 9/10 | 90.0% |
| groundedness | 8/10 | 80.0% |

## All ten cases

Cells show **assistant / local judge** decisions.

| Case | Question | Relevancy | Correctness | Groundedness |
| ---: | --- | --- | --- | --- |
| 1 | What does civil disobedience relate to? | pass / pass | pass / pass | pass / pass |
| 2 | In a type III secretion system, proteins are transported to the host cell in order to do what? | pass / fail | pass / pass | pass / pass |
| 3 | What is the delta in the Rhine delimited in the west by? | pass / fail | pass / pass | pass / pass |
| 4 | How long may the Amazon rainforest be threatened, according to some computer models? | pass / pass | fail / fail | pass / pass |
| 5 | People of what nationality invented the steam turbine? | pass / pass | pass / pass | pass / fail |
| 6 | When did France and the Dutch fight in the 17th century? | pass / pass | pass / pass | pass / pass |
| 7 | How many populous counties are in the United States? | pass / pass | fail / fail | fail / fail |
| 8 | By which Commission is the University of Chicago Press accredited? | pass / pass | fail / fail | fail / pass |
| 9 | Which researcher approved the study? | pass / pass | fail / fail | fail / fail |
| 10 | At what time does the support desk open? | pass / pass | pass / fail | pass / pass |

## Investigated disagreements

### Case 2: answer_relevancy

Question: In a type III secretion system, proteins are transported to the host cell in order to do what?

Actual model response: In a type III secretion system, proteins are transported to the host cell to shut down host defenses.

Assistant: **pass**. The response directly states the purpose of transporting the proteins into the host cell.

Local judge: **fail**, score 0.5, threshold 0.7. The score is 0.50 because the output incorrectly states that the type III secretion system shuts down host defenses, which is irrelevant to the question about the purpose of protein transport to the host cell. The score cannot be higher because the output fails to address the actual question about protein function, focusing instead on a system function unrelated to the query's intent.

Finding: **Statement extraction changed the subject of a claim.** The actual answer says the transported proteins shut down host defenses. The metric's extracted statement instead attributes that action to the secretion system, then rejects that rewritten statement. The assistant assesses the original answer as directly relevant.

### Case 3: answer_relevancy

Question: What is the delta in the Rhine delimited in the west by?

Actual model response: The delta in the Rhine is delimited in the West by the Alter Rhein ("Old Rhine").

Assistant: **pass**. The response identifies the requested western boundary. The parenthetical alias is relevant clarification.

Local judge: **fail**, score 0.5, threshold 0.7. The score is 0.50 because the output incorrectly states that the Alter Rhein is known as the Old Rhine without addressing the west boundary of the Rhine delta, which is the core question. The score cannot be higher as the output fails to provide the west boundary information directly, making it irrelevant to the query.

Finding: **A contextual alias was penalized as irrelevant.** The original answer identifies Alter Rhein as the western boundary and includes Old Rhine, the alias supplied by the context. The metric accepts the boundary statement but rejects the alias statement. The assistant treats the alias as relevant clarification.

### Case 5: groundedness

Question: People of what nationality invented the steam turbine?

Actual model response: British

Assistant: **pass**. The passage calls the steam turbine a British invention. At the national-attribution level intended by this question, British is supported. This assessment does not infer the citizenship or biography of a named individual.

Local judge: **fail**, score 0.3, threshold 0.8. The Actual Output claims British nationality for the steam turbine inventor, but Context states it was a British invention without specifying nationality. The claim is unsupported as Context only mentions British origin without confirming nationality.

Finding: **Interpretation-sensitive national-attribution disagreement.** The reference is British and the passage calls the turbine a British invention. The assistant accepts the national attribution intended by this question; the local judge requires a more explicit statement about an inventor's nationality. This disagreement needs judgement about the intended inference and should not automatically be counted as a proven judge error.

### Case 8: groundedness

Question: By which Commission is the University of Chicago Press accredited?

Actual model response: The University of Chicago Press is accredited by The Higher Learning Commission.

Assistant: **fail**. The response transfers an accreditation claim from the university to its Press. The passage listing the Press as part of the university does not establish that specific accreditation relationship.

Local judge: **pass**, score 1.0, threshold 0.8. The Actual Output correctly states the accreditation body as The Higher Learning Commission, which is directly supported by the Context. The Context explicitly mentions 'The university is accredited by The Higher Learning Commission,' so the claim is fully supported with no unsupported claims. This aligns perfectly with the evaluation steps, scoring 10.

Finding: **Accreditation was transferred between different entities.** The question and model answer concern the University of Chicago Press. The context accredits the university. Listing the Press as part of the university does not supply the Press-specific accreditation claim. The assistant flags that unsupported transfer, while the local judge accepts it.

### Case 10: correctness

Question: At what time does the support desk open?

Actual model response: 09:00

Assistant: **pass**. 09:00 exactly matches an acceptable reference answer and the office policy's opening time.

Local judge: **fail**, score 0.0, threshold 0.7. The response '09:0:0' is incorrect as it does not match any expected outputs. The context specifies the support desk opens at 09:00, but the actual output has a typo (09:00 vs 09:0:0), making it invalid. Expected outputs include '09:00', '9:00 AM', and '9 am', so the response is wrong.

Finding: **An exact reference match was rejected after an invented typo.** The saved actual response is 09:00, which exactly matches an acceptable reference and the supplied office policy. The local judge's failing explanation instead refers to 09:0:0. That altered string is not the saved model answer.

## Limitations

- This is an AI-versus-AI comparison, not human-versus-judge agreement or model accuracy.

- Prior judge outputs and findings were available to the assistant; the review is not blinded or independent of those findings.

- The ten development cases and three related metrics per case are a small, dependent sample, not a representative benchmark.

- Agreement does not establish that either reviewer is correct, and disagreements are not automatically local-judge errors.

- Original source outputs, assistant ratings and the separate human worksheet are preserved.

## Evidence

- [Completed assistant ratings](pilot-assistant-review.json)

- [Readable assistant review](pilot-assistant-review.md)

- [Original pilot results](pilot-results.json)
