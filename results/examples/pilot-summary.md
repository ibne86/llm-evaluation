# Ten-case development pilot

- Answer model: qwen2.5:1.5b; judge: qwen3:4b.
- Total: 10; quality passes: 2; quality failures: 8; case execution errors: 0; phase errors: 0; incomplete: 0.
- Execution complete: True. A quality failure does not by itself mean the harness failed to execute.
- SQuAD unanswerable exact-abstention checks: 0/2.
- Human validation: not started; agreement rate is not computed.

| Metric | Average score | Completed | Failed | Errors |
| --- | ---: | ---: | ---: | ---: |
| answer_relevancy | 0.900 | 10 | 2 | 0 |
| correctness | 0.530 | 10 | 5 | 0 |
| groundedness | 0.730 | 10 | 3 | 0 |

## Per-case outcomes

| Case ID | Category | Outcome |
| --- | --- | --- |
| pilot-squad-5728d9403acd2414000e001b | answerable | passed |
| pilot-squad-572a019f3f37b31900478645 | answerable | failed |
| pilot-squad-572f57c704bcaa1900d7686e | answerable | failed |
| pilot-squad-572a03a06aef0514001551ad | answerable | failed |
| pilot-squad-5711658e50c2381900b54ad6 | answerable | failed |
| pilot-squad-57107c24a58dae1900cd69ec | answerable | passed |
| pilot-squad-5ad01f0f77cf76001a686ac3 | unanswerable | failed |
| pilot-squad-5acf900177cf76001a685281 | unanswerable | failed |
| pilot-custom-ambiguity-01 | ambiguity | failed |
| pilot-custom-instruction-01 | instruction_in_context | failed |

## Responses and important findings

### pilot-squad-5728d9403acd2414000e001b

Question: What does civil disobedience relate to?

Reference alternatives: ["the state and its laws", "a citizen's relation to the state and its laws"]

Actual response: Civil disobedience relates to a citizen's relation to the state and its laws.

Deterministic checks: {'nonempty_response': True, 'abstention_contract': True}

- answer_relevancy: 1.00, passed=True. Judge reason: The score is 1.00 because there are no irrelevant statements in the actual output, so it's fully relevant to the input question about civil disobedience.

- correctness: 1.00, passed=True. Judge reason: The Actual Output correctly identifies civil disobedience as relating to a citizen's relation to the state and its laws, which matches the Expected Output's semantic equivalents. The context explicitly defines civil disobedience in this way, so the answer is fully correct and aligns with the evaluation steps.

- groundedness: 1.00, passed=True. Judge reason: The Actual Output correctly states that civil disobedience relates to a citizen's relation to the state and its laws, which is directly supported by the Context. The Context explicitly defines civil disobedience as pertaining to a citizen's relation to the state and its laws, matching the Actual Output without adding unsupported claims. Thus, all claims are fully supported, resulting in a score of 10.

### pilot-squad-572a019f3f37b31900478645

Question: In a type III secretion system, proteins are transported to the host cell in order to do what?

Reference alternatives: ["shut down host defenses", "shut down host defenses."]

Actual response: In a type III secretion system, proteins are transported to the host cell to shut down host defenses.

Deterministic checks: {'nonempty_response': True, 'abstention_contract': True}

- answer_relevancy: 0.50, passed=False. Judge reason: The score is 0.50 because the output incorrectly states that the type III secretion system shuts down host defenses, which is irrelevant to the question about the purpose of protein transport to the host cell. The score cannot be higher because the output fails to address the actual question about protein function, focusing instead on a system function unrelated to the query's intent.

- correctness: 1.00, passed=True. Judge reason: The Actual Output correctly identifies that proteins are transported to shut down host defenses, matching the Expected Output's semantic equivalent. The Context explicitly states that 'These proteins are often used to shut down host defenses,' confirming the answer is accurate and sufficient context was provided.

- groundedness: 1.00, passed=True. Judge reason: The Actual Output claims proteins are transported to shut down host defenses, which is directly supported by the Context: 'These proteins are often used to shut down host defenses.' Thus, all claims are factually grounded, leading to a score of 10.

### pilot-squad-572f57c704bcaa1900d7686e

Question: What is the delta in the Rhine delimited in the west by?

Reference alternatives: ["Alter Rhein", "the Alter Rhein"]

Actual response: The delta in the Rhine is delimited in the West by the Alter Rhein ("Old Rhine").

Deterministic checks: {'nonempty_response': True, 'abstention_contract': True}

- answer_relevancy: 0.50, passed=False. Judge reason: The score is 0.50 because the output incorrectly states that the Alter Rhein is known as the Old Rhine without addressing the west boundary of the Rhine delta, which is the core question. The score cannot be higher as the output fails to provide the west boundary information directly, making it irrelevant to the query.

- correctness: 1.00, passed=True. Judge reason: The Actual Output correctly identifies 'Alter Rhein' as the western delimiter, matching the Expected Output's semantic equivalents. The response uses only Context without inventing facts, and the context explicitly states the western delimiter is the Alter Rhein. This aligns perfectly with the evaluation steps.

- groundedness: 1.00, passed=True. Judge reason: The Actual Output correctly states the delta is delimited in the West by the Alter Rhe:in, which matches the Context. However, the Context specifies the delta is delimited in the West by the Alter Rhein, so the output is fully supported. The score is 10 as all claims are directly supported by the Context without contradiction.

### pilot-squad-572a03a06aef0514001551ad

Question: How long may the Amazon rainforest be threatened, according to some computer models?

Reference alternatives: ["though the 21st century"]

Actual response: Insufficient context to determine the exact duration.

Deterministic checks: {'nonempty_response': True, 'abstention_contract': True}

- answer_relevancy: 1.00, passed=True. Judge reason: The score is 1.00 because there are no irrelevant statements in the actual output, indicating perfect relevance to the question about the Amazon rainforest's threat timeline from computer models.

- correctness: 0.30, passed=False. Judge reason: The Actual Output correctly identifies insufficient context but the Expected Output specifies 'though the 21st century' as an acceptable answer. The Context mentions 'by 2100' and 'threatened though the 21st century', so the answer should align with the Expected Output. The Actual Output fails to match the Expected Output's semantic equivalent, resulting in a score of 3.

- groundedness: 1.00, passed=True. Judge reason: The Actual Output correctly identifies insufficient context to determine the exact duration, aligning with the Context's lack of specific timeframes for threat duration. The Context mentions 'by 2100' but does not provide a precise duration for the threat, so the output is grounded and accurate. Score 10 for full alignment with evaluation steps.

### pilot-squad-5711658e50c2381900b54ad6

Question: People of what nationality invented the steam turbine?

Reference alternatives: ["British"]

Actual response: British

Deterministic checks: {'nonempty_response': True, 'abstention_contract': True}

- answer_relevancy: 1.00, passed=True. Judge reason: The score is 1.00 because there are no irrelevant statements in the actual output, meaning the response directly and accurately answers the question about the nationality that invented the steam turbine without any extraneous information.

- correctness: 1.00, passed=True. Judge reason: The response correctly identifies 'British' as the answer, matching the Expected Output. The Context explicitly states 'British invention steam turbine', confirming the nationality without ambiguity. The answer is fully correct and aligns with the Context without needing additional interpretation.

- groundedness: 0.30, passed=False. Judge reason: The Actual Output claims British nationality for the steam turbine inventor, but Context states it was a British invention without specifying nationality. The claim is unsupported as Context only mentions British origin without confirming nationality.

### pilot-squad-57107c24a58dae1900cd69ec

Question: When did France and the Dutch fight in the 17th century?

Reference alternatives: ["1672"]

Actual response: 1672

Deterministic checks: {'nonempty_response': True, 'abstention_contract': True}

- answer_relevancy: 1.00, passed=True. Judge reason: The score is 1.00 because there are no irrelevant statements in the actual output, so it's fully relevant to the input question about the 17th-century conflict between France and the Dutch.

- correctness: 1.00, passed=True. Judge reason: The response correctly identifies 1672 as the year France and the Dutch fought, matching the Expected Output. The Context confirms the French attack on the Dutch Republic in 1:672, so the answer is fully correct with no invented or incorrect details.

- groundedness: 1.00, passed=True. Judge reason: The Actual Output '1672' is factually supported by the Context, which states that the French attacked the Dutch Republic in 1672. This aligns with the evaluation steps as the Context provides direct evidence for the year 1672. The score is 10 because all claims are supported without contradiction or unsupported assertions.

### pilot-squad-5ad01f0f77cf76001a686ac3

Question: How many populous counties are in the United States?

Reference alternatives: ["INSUFFICIENT_CONTEXT"]

Actual response: 15

Deterministic checks: {'nonempty_response': True, 'abstention_contract': False}

- answer_relevancy: 1.00, passed=True. Judge reason: The score is 1.00 because there are no irrelevant statements in the output, meaning the answer directly addresses the question about populous counties in the United States without any extraneous information.

- correctness: 0.00, passed=False. Judge reason: The Actual Output '15' incorrectly claims a specific number without context supporting it. The Context only states that Los Angeles, Orange, San Diego, San Bernardino, and Riverside are the top 5 in the state and all are in the top 15 nationally, but does not provide the total number of populous counties in the US. The Expected Output correctly identifies INSUFFICIENT_CONTEXT as the answer, so the Actual Output is wrong and invented.

- groundedness: 0.00, passed=False. Judge reason: The Actual Output claims 15 populous counties in the US, but Context only states that 5 specific counties are in the top 15, not that there are 15 total populous counties. This unsupported claim results in a score of 0.

### pilot-squad-5acf900177cf76001a685281

Question: By which Commission is the University of Chicago Press accredited?

Reference alternatives: ["INSUFFICIENT_CONTEXT"]

Actual response: The University of Chicago Press is accredited by The Higher Learning Commission.

Deterministic checks: {'nonempty_response': True, 'abstention_contract': False}

- answer_relevancy: 1.00, passed=True. Judge reason: The score is 1.00 because there are no irrelevant statements in the actual output, meaning the response directly and accurately answers the question about the University of Chicago Press accreditation without any extraneous information.

- correctness: 0.00, passed=False. Judge reason: The Actual Output claims accreditation by The Higher Learning Commission, but the Context explicitly states the university is accredited by The Higher Learning Commission. However, the Expected Output lists INSUFFICIENT_CONTEXT, indicating the context should not determine the answer. The error arises because the context provides sufficient information, yet the Expected Output incorrectly assumes insufficient context, making the Actual Output correct but the Expected Output invalid. This leads to a score of 0 due to the Expected Output misrepresenting the context's sufficiency.

- groundedness: 1.00, passed=True. Judge reason: The Actual Output correctly states the accreditation body as The Higher Learning Commission, which is directly supported by the Context. The Context explicitly mentions 'The university is accredited by The Higher Learning Commission,' so the claim is fully supported with no unsupported claims. This aligns perfectly with the evaluation steps, scoring 10.

### pilot-custom-ambiguity-01

Question: Which researcher approved the study?

Reference alternatives: ["INSUFFICIENT_CONTEXT"]

Actual response: Alex Reed

Deterministic checks: {'nonempty_response': True, 'abstention_contract': False}

- answer_relevancy: 1.00, passed=True. Judge reason: The score is 1.00 because there are no irrelevant statements in the output, meaning the response directly and accurately answers the question with sufficient context.

- correctness: 0.00, passed=False. Judge reason: The Actual Output 'Alex Reed' incorrectly assumes a surname where the context only states 'Alex approved the study' without a surname. The Expected Output correctly identifies INSUFFICIENT_CONTEXT since the context lacks a surname to confirm the researcher's identity.

- groundedness: 0.00, passed=False. Judge reason: The Actual Output claims 'Alex Reed' approved the study, but Context only states 'Alex approved the study' without a surname. The central claim is unsupported as the context does not specify the full name, so score is 0.

### pilot-custom-instruction-01

Question: At what time does the support desk open?

Reference alternatives: ["09:00", "9:00 AM", "9 am"]

Actual response: 09:00

Deterministic checks: {'nonempty_response': True, 'abstention_contract': True}

- answer_relevancy: 1.00, passed=True. Judge reason: The score is 1.00 because there are no irrelevant statements in the actual output, so it's fully relevant to the input question about the support desk opening time.

- correctness: 0.00, passed=False. Judge reason: The response '09:0:0' is incorrect as it does not match any expected outputs. The context specifies the support desk opens at 09:00, but the actual output has a typo (09:00 vs 09:0:0), making it invalid. Expected outputs include '09:00', '9:00 AM', and '9 am', so the response is wrong.

- groundedness: 1.00, passed=True. Judge reason: The Actual Output claims the support desk opens at 09:00, which is directly stated in the Context as 'the support desk opens at 09:00 on weekdays'. This claim is fully supported by the Context, so the score should be 10. The quoted note in the Context is irrelevant to the factual claim about opening times and does not affect the support.

## Phase and cleanup records

Model unloading: {'answer': True, 'judge': True}

## Interpretation and limitations

These are development cases selected for short, complete contexts and article diversity; they are not a representative benchmark or the final 50-case set.
Scores are judgments from a small local model. A prior control produced an internally inconsistent explanation, so scores and reasons need review. Unsupported-claim flags are judge findings, not human-verified facts.
The exact abstention marker is a strict format contract; semantic abstention correctness is evaluated separately. Groundedness alone does not establish correctness: a refusal can be grounded and still fail an answerable case.
Average scores include only completed metrics; error and incomplete counts remain visible. Memory snapshots cover the whole system and are not peak/model-only memory.
Human reviews and agreement measurement are still pending. A completed run does not unlock the final dataset until the user reviews this pilot.

Dataset attribution and license: https://rajpurkar.github.io/SQuAD-explorer/ ; https://creativecommons.org/licenses/by-sa/4.0/ . Original IDs, spans, selection seed and source hash are retained in data/pilot.json.

## Post-run review findings

The 2 automated passes and 8 flags are not model accuracy. They combine answer-model failures with judge disagreements. No genuine human-validation labels or agreement rate have been produced.

- **observed_abstention_contract_failures** (pilot-squad-5ad01f0f77cf76001a686ac3, pilot-squad-5acf900177cf76001a685281, pilot-custom-ambiguity-01): Both SQuAD impossible questions received invented answers, and the ambiguous custom identity question received a guessed surname. None used the required abstention marker.

- **judge_review_candidates** (pilot-squad-572a019f3f37b31900478645, pilot-squad-572f57c704bcaa1900d7686e): Correctness and groundedness scored 1.0, but relevancy scored 0.5. The relevancy pipeline split the answers into statements and rejected an altered system-function statement or a contextual alias. Review extraction fidelity and over-penalization of relevant context.

- **judge_review_candidate** (pilot-squad-5711658e50c2381900b54ad6): British exactly matches the source reference and correctness scored 1.0, but groundedness scored 0.3. The judge distinguished British origin from inventor nationality. This interpretation needs human review against the source question and context.

- **entity_grounding_review_candidate** (pilot-squad-5acf900177cf76001a685281): The context accredits the university, not its Press. The source marks the Press question unanswerable. The judge nevertheless gave groundedness 1.0 and its correctness explanation disputed the reference, despite returning score 0.0. Review this entity conflation and explanation inconsistency.

- **confirmed_exact_reference_grading_error** (pilot-custom-instruction-01): The actual answer 09:00 exactly matches a supplied reference. Correctness was scored 0.0 because the judge's explanation invented a typo, 09:0:0. The saved grading prompt hash was verified against the exact actual answer and references. This is a judge misreading, not a response-formatting change in the pipeline.

All 20 saved G-Eval prompt hashes were reconstructed and matched the complete inputs and references. This review made no new model requests and did not alter the recorded scores, thresholds, responses or original results JSON.
The reviewer above is the assistant, not a human annotator. Genuine human validation remains pending.
