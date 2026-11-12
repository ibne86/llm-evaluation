# Local LLM Evaluation — project plan and progress

Prepared: 10 November 2026. Updated: 12 November 2026. Current status: the ten-case pilot, repeated-response experiment and manual pilot review are complete. Ibne supplied 30/30 verdicts, with 25/30 matching the original local judge. The manual review was non-blinded; a separate follow-up now includes all 30 written human rationales while preserving the initial version without reasons. Independent blinded validation and the final 50-case evaluation remain outstanding. The original model pair is unchanged; earlier setup/checkpoint sections below are historical records.

## Objective and boundaries

Build a Python, pytest, DeepEval and Ollama portfolio project evaluating an existing local language model on context-based question answering. Both generation and judging must run locally, without paid LLM APIs. No training, retrieval pipeline, database, chatbot application or frontend is required.

Proceed one step at a time, with user verification between steps. Do not generate the final 50-case evaluation set before the 10-case pilot executes successfully. Publish or push to GitHub only after explicit user approval.

The currently open folder is an existing football analytics Git repository. It was inspected read-only and must remain separate. Its two pre-existing untracked screenshot files were left untouched.

## Step 1: environment inspection

| Item | Observed state |
| --- | --- |
| Default Python | 3.14.2, C:\Python314\python.exe |
| Recommended project Python | 3.12.1, C:\Python312\python.exe, 64-bit |
| Python 3.12 pip | 25.2; available through py -3.12 -m pip |
| Git | 2.56.0.windows.4; user name and email configured |
| Git branches | Global default is master; project working branch is codex/setup. Agree the public default branch before publication. |
| PyCharm | 2024.3.4, build 243.25659.43; Toolbox launcher available |
| Ollama application | Installed at the default user location; version 0.40.16 |
| Ollama service | http://127.0.0.1:11434/api/version verified; version 0.40.16 |
| Project packages | DeepEval 4.3.3, ollama 0.6.3, pytest 9.2.0; installed and verified in .venv. datasets is not installed. |
| pytest | 7.4.4 in the existing Python 3.12 environment; the new project will use isolated dependencies |
| Free disk space on C: | Approximately 264 GB at inspection |
| CPU | User-reported Intel Core i7-1255U, 1.70 GHz base speed; screenshot shows 10 cores and 12 logical processors |
| Installed RAM | User reports 16.0 GB, 15.7 GB usable; screenshot shows 3200 MT/s memory |
| Available RAM at screenshot | 1.9 GB available, 13.8 GB in use; recheck after closing unused applications before model tests |
| Graphics | Intel Iris Xe integrated graphics; screenshot shows shared system memory, not additional dedicated model memory |
| Windows | User-reported Windows 11 Home, version 26H2, 64-bit on an x64 processor |
| Storage type | Screenshot shows NVMe SSD |

Use Python 3.12 because it is already installed and is a conservative match for this PyCharm version and the dependency ecosystem. This is not a claim that DeepEval cannot run on Python 3.14. A virtual environment will isolate the project's packages from existing projects.

Confirmed project name: `llm-evaluation`. The folder `C:\Users\khani\Projects\llm-evaluation` exists and was empty at the pre-initialization inspection. Local Git, the isolated Python 3.12 environment, and setup documentation have been initialized after filesystem approval. No remote or commit has been created.

After the manual hardware checkpoint, initialize only the basic project: initialize Git on the working branch `codex/setup`, create `.venv` with Python 3.12, add a README, `.gitignore`, this plan and progress notes, and verify the isolated interpreter and Git state. Ignore `.venv`, `.idea`, `.env` files, caches, downloaded models, raw dataset downloads and generated runs; retain a deliberate example-results folder for later publication. No Git remote or push is part of Step 1. Agree the public repository's default branch before publication.

In PyCharm, open that folder and select its existing `.venv\Scripts\python.exe` through the Python Interpreter settings. Verify `sys.executable` from its terminal or Python console before continuing. The exact UI labels may differ from the latest JetBrains documentation because the installed IDE is 2024.3.4.

## Proposed architecture

```text
Versioned dataset JSON
  -> Python runner -> local Ollama answer model
  -> saved raw responses and performance metadata
  -> unload answer model
  -> DeepEval metrics -> local Ollama judge
  -> deterministic checks + metric scores/reasons + evaluator errors
  -> JSON/CSV results and Markdown report
  -> human review JSON -> agreement/disagreement report
```

Generate all answers before loading the judge. Process one request at a time, including metric calls; explicitly disable metric concurrency. Unload models between phases using Ollama's supported lifecycle controls. Save responses so that judging can resume without repeating generation.

Start with temperature zero, a fixed seed where supported, bounded output lengths and a modest context window (initial target 4096 tokens; increase only after measurement). Check full prompt size, including metric instructions, before evaluation; reject or adjust overlong inputs rather than silently truncate them. Record model digests, package versions, dataset hash, prompt/rubric versions, configuration, timings and errors. Temperature zero and a seed do not guarantee identical outputs on every platform.

Explicitly pass the local judge to every DeepEval metric, opt out of telemetry, and avoid hosted reporting/login. Downloads require internet during setup; evaluation should run offline after installation, model downloads and dataset preparation.

## Proposed model baseline

| Role | Ollama tag | Listed download size | Quantization | Rationale |
| --- | --- | --- | --- | --- |
| System under test | qwen2.5:1.5b | 986 MB | Q4_K_M | Small instruction-following baseline for CPU execution |
| Local judge | qwen3:4b | 2.5 GB | Q4_K_M | Larger, different model checkpoint for rubric evaluation |

These are proposed starting points, not benchmarked recommendations for this particular CPU. Both model pages list Apache 2.0 licenses. Quantization stores model weights at reduced precision to reduce memory and download requirements, with possible quality tradeoffs. Runtime memory exceeds model download size.

Initial sizing used the user's screenshot showing 1.9 GB available RAM and suggested more headroom before testing. Subsequent measurements showed that both original models could run sequentially under the available, changing Windows memory conditions with bounded settings. The answer setup used a 1024-token context; the DeepEval judge check used 2048 tokens. These observations replace the initial untested memory assumption. Keep one model loaded at a time and measure again as prompt lengths and workloads grow. Do not count shared GPU memory as extra RAM or treat system snapshots as peak/model-only memory measurements.

Qwen3 has a thinking mode; validate disabled-thinking behavior with the installed DeepEval/Ollama integration before adopting it for routine scoring. Prefer the built-in DeepEval OllamaModel adapter. Only add a small schema-aware adapter if the tested built-in integration cannot provide the required behavior. Do not change models silently if structured-output or speed checks fail; report evidence and agree the change with the user. Using two Qwen generations still leaves shared-family bias.

Before the pilot, check valid structured outputs and score/reason fields using known correct, incorrect, unsupported and abstaining responses. JSON validity is an integration check, not evidence that the judge's decisions are accurate. Malformed judge responses, timeouts and truncation are evaluator errors, never passing tests.

## Dataset design

- Pilot: 10 development cases, proposed composition 6 answerable, 2 unanswerable and 2 custom behavior cases. Reserve separate cases for the final evaluation.
- Final set, created only after pilot verification: exactly 30 answerable SQuAD 2.0 cases, 10 unanswerable SQuAD 2.0 cases and 10 custom cases.
- Use a documented fixed seed, source snapshot/hash and category sampling method; spread SQuAD selections across articles where practical. Preserve original IDs and all reference answer variants.
- Loading a source-provided split is only a selection convenience. We are not creating training/validation/test partitions to train a model.
- Inputs include case ID, original source ID, question, complete context, expected answers or abstention expectation, category, source, and answerability. Store actual responses and scores in run outputs linked by case ID; keep test inputs unchanged.
- Custom cases cover ambiguity, conflicting facts, instructions embedded in context, misleading questions and unsupported claims. Define expected behavior and rubric before execution.
- Final cases are held fixed and are not used for repeated prompt, model or judge tuning. Use development cases for that work.
- SQuAD 2.0 is distributed under CC BY-SA 4.0. Retain attribution, original IDs, a source/license link and a record of selection/transformations. Keep the dataset license explicit and separate from the code license; preserve share-alike obligations for distributed adapted dataset material.

## Evaluation design

| Area | Proposed method |
| --- | --- |
| Relevancy | DeepEval AnswerRelevancyMetric |
| Semantic correctness | DeepEval G-Eval comparing question, context, actual response and acceptable reference answers |
| Groundedness | G-Eval rubric requiring every factual claim to be supported by the supplied context |
| Context contradictions | DeepEval HallucinationMetric as a supplementary check; confirm the installed version's score direction and behavior with known examples |
| Unanswerable handling | A clear requested abstention phrase with a deterministic contract assertion, plus rubric checks for invented claims or contradictory answers |
| Consistency | Repeat a representative subset, reporting correctness/grounding pass rate across runs and semantic disagreement; identical wording alone is insufficient |
| Human validation | Blind human review of 10–15 representative responses using the frozen rubric, then compare decisions with judge decisions |

The hallucination metric's current documentation describes context consistency/contradiction; lack of contradiction alone does not establish that every added claim is supported. The explicit groundedness rubric addresses that difference. Retrieval precision/recall and similar retrieval-specific metrics are outside scope.

Start the MVP with semantic correctness, explicit grounding and abstention checks; add the remaining metrics incrementally. Choose and record thresholds before final evaluation. Always distinguish an execution success (the harness completed) from a quality pass (the model met the rubric). The 10-case gate requires valid completed evaluation results, not ten passing model answers.

Human agreement is the number of matching pass/fail decisions divided by the number of paired completed reviews. Report the denominator, sampling method, per-criterion disagreements and a small confusion table. Human labels must be entered by the user, not generated by the same judge. A small, selected sample and high agreement do not establish general judge accuracy. Discuss shared-family bias, prompt sensitivity, small-model reasoning limits and variability.

## Proposed repository structure

```text
llm-evaluation/
  README.md
  LICENSE                         # code license to agree before publication
  .gitignore
  pyproject.toml                  # basic pytest/project settings
  requirements.txt               # pinned, tested direct dependencies
  requirements-lock.txt          # tested full dependency snapshot
  config.toml
  src/llm_eval/
    __init__.py
    config.py
    dataset.py
    ollama_client.py
    metrics.py
    runner.py
    reporting.py
    human_validation.py
  scripts/
    prepare_dataset.py
    run_evaluation.py
    compare_human_reviews.py
  tests/
    unit/
    integration/
  data/
    pilot.json
    evaluation.json              # added after the pilot gate
    DATASET_CARD.md
    LICENSE-SQUAD.txt
  results/
    examples/                    # deliberate verified example, later
  docs/
    PROJECT_PLAN.md
    PROGRESS.md
    setup-windows.md
    human-review-rubric.md
    limitations.md
  .venv/                         # local only; ignored by Git
```

This is the intended final structure; create files only when their implementation step arrives. Unit tests cover meaningful dataset, result and reporting behavior without a running model. Explicit opt-in integration tests exercise Ollama and the real judge. Later, a lightweight GitHub workflow can run offline unit tests; local model evaluation remains local.

## Numbered implementation checklist and effort

### Milestone 1 — MVP, 6–9 hours

1. Inspect environment, confirm folder and proposed design, initialize Git and isolated Python, select the interpreter in PyCharm, verify together. **0.5–1 hour.** Complete: software and hardware reviewed, Git and isolated Python initialized, and user screenshots verify the project interpreter in both PyCharm and PowerShell.
2. Install and verify Ollama and project dependencies; download proposed quantized models. **1–1.5 hours.** Both originally proposed models are downloaded. The original qwen3:4b judge passed structured-output controls and actual DeepEval relevancy controls, and was unloaded. The 10-case pilot is next after review.
3. Prepare and validate the 10-case pilot with attribution. **0.5–1 hour.** Complete; data/pilot.json contains the documented 6/2/2 development sample.
4. Implement context-based generation, abstention instructions, response capture and a performance baseline. **1–1.5 hours.** Complete for the pilot; generated answers are saved separately from immutable inputs.
5. Integrate the local DeepEval judge, validate structured output and rubric smoke checks, then run the 10-case pilot. **2–2.5 hours.** Complete for the pilot; all 30 metrics executed with zero execution errors.
6. Produce the first report, verify saved outputs and review the pilot with the user. **1–1.5 hours.** JSON/CSV/Markdown reports and examples saved; user review pending. **Do not prepare the final set before this review.**

### Milestone 2 — completion, 9–16 additional hours

7. Freeze configuration/rubrics and prepare the separate 50-case final dataset with the required composition and custom behaviors. **1.5–2.5 hours.** Pending.
8. Add remaining metrics, consistency runs and automated regression checks. **2–3.5 hours.** Pending.
9. Prepare the human review sheet and analyze agreement/disagreements. Completed for all ten pilot cases: 30 non-blinded human verdicts, 25/30 local-judge matches, and 30 written human rationales in a follow-up version. The initial version without reasons is preserved. Independent blinded review remains outstanding.
10. Complete reporting, failure analysis and reproducible example artifacts. **1.5–2.5 hours.** Pending.
11. Finish README, setup/reproduction instructions, dataset documentation and limitations. **1.5–3 hours.** Pending.
12. Review the exact publication contents with the user; publish to GitHub only when approved. **0.5–1.5 hours.** Pending.

Milestone 2 subtotal: **8.5–16 hours**, rounded planning allowance **9–16 hours**. Overall estimate remains **15–25 hours** of active work including learning and human review. Model downloads, CPU-only evaluation wall time, dependency problems and waiting for review may extend elapsed time. Re-estimate model runtime after the pilot instead of promising unmeasured throughput.

## Verified official references

- DeepEval Ollama integration: https://deepeval.com/integrations/models/ollama
- DeepEval custom structured-output guidance: https://deepeval.com/guides/guides-using-custom-llms
- DeepEval G-Eval: https://deepeval.com/docs/metrics-llm-evals
- DeepEval answer relevancy: https://deepeval.com/docs/metrics-answer-relevancy
- DeepEval hallucination semantics: https://deepeval.com/docs/metrics-hallucination
- DeepEval telemetry opt-out: https://deepeval.com/docs/data-privacy
- Ollama Windows installation: https://docs.ollama.com/windows
- Ollama structured outputs: https://docs.ollama.com/capabilities/structured-outputs
- Ollama thinking controls: https://docs.ollama.com/capabilities/thinking
- Ollama model unloading and concurrency: https://docs.ollama.com/faq
- Answer-model details: https://ollama.com/library/qwen2.5:1.5b
- Judge-model details: https://ollama.com/library/qwen3:4b
- SQuAD source and licensing: https://rajpurkar.github.io/SQuAD-explorer/
- Hugging Face dataset: https://huggingface.co/datasets/rajpurkar/squad_v2
- PyCharm virtual environments: https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html

## Next checkpoint

Inspect the [manual pilot findings](pilot-review-findings.md), compatible comparison command and publishable human worksheet/report. Human/local-judge agreement is 25/30 (83.3%), with five disagreements. The follow-up manual review is complete, with 30/30 written reasons and prior exposure explicitly recorded. The initial version without reasons is preserved. Independent blinded validation remains outstanding.

After the manual Git publication steps, record the pilot calibration decision and freeze settings before preparing the separate final 50-case set. Preserve the original model outputs/scores and exclude pilot source IDs and contexts. Git operations remain manual.

## First measured answer-model baseline

User authorized proceeding with available memory. qwen2.5:1.5b completed two synthetic CPU requests using a 1024-token context and 64-token output cap. Cold wall time: 3.365 seconds; warm repeat: 0.241 seconds. Both returned the requested year, 2018. Available system RAM snapshots were 1.430 GiB before inference, 0.484/0.485 GiB after the responses and 1.521 GiB after unloading. Ollama reported zero GPU allocation, and the unload check passed. Detailed files: results/runs/baseline-20261110T052732276625Z.json and its Markdown companion. These results do not validate judge scoring, SQuAD accuracy, a larger context window, or the 10-case pilot. The judge needs a separate feasibility and structured-output check.



## Original judge integration checkpoint

The original qwen3:4b judge passed structured-output controls and actual DeepEval relevancy controls, and was unloaded. The 10-case pilot is next after review. Model pair remains qwen2.5:1.5b and qwen3:4b. The small source extension controls request fields absent from the installed base adapter; it does not replace the model or DeepEval metric logic. See docs/judge-setup.md, docs/deepeval-judge-check.md and the latest results/runs reports. No judge-accuracy claim follows from these setup controls.



## Observed judge limitation

The negative relevancy control scored 0.0 as expected but generated an internally contradictory explanation. The original output is preserved and marked in results/runs/deepeval-judge-20261110T054915543161Z.json and its Markdown companion. This is an integration success with an observed explanation-quality limitation, not evidence of judge accuracy. The next step remains the separate 10-case pilot and later genuine human validation.


## First pilot checkpoint

The 10-case pilot executed all 30 metrics without execution errors. Automated outcomes were 2 passes and 8 flags, including answer-model abstention failures and judge misgrading/review candidates. Read results/examples/pilot-summary.md and its review notes, then collect genuine human labels to assess judge decisions. The original models and original baseline scores are unchanged. The final 50-case set remains gated on user review; no GitHub publication is authorized.
