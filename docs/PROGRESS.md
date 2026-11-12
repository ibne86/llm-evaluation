# Project progress

Updated: 12 November 2026. Current status: both manual reviews are complete. The ten-case pilot has 30 written reasons and 25/30 judge matches; the nine consistency responses have 27 written reasons and 24/27 judge matches. Their observations overlap, so the results are reported separately. Final evaluation has not started. Earlier entries are historical checkpoints.

## Completed

- Reviewed the project requirements and documented the proposed architecture.
- Confirmed Python 3.12.1 and 3.14.2, Git 2.56.0, and PyCharm 2024.3.4 are installed.
- Reviewed user-supplied hardware details and Task Manager screenshots.
- Confirmed the existing `llm-evaluation` project folder was empty before initialization.
- Initialized a local Git repository on `codex/setup`.
- Created an isolated Python 3.12 virtual environment in `.venv`.
- Added the README, Git exclusions, project plan, and Windows setup notes.

## Step 1 verified: PyCharm and terminal

- Open `C:\Users\khani\Projects\llm-evaluation` in PyCharm.
- Select the existing interpreter `C:\Users\khani\Projects\llm-evaluation\.venv\Scripts\python.exe`.
- Verify its version and interpreter path using the commands in [setup-windows.md](setup-windows.md).
- Complete: user screenshots show both PyCharm Python Console and PowerShell using the project .venv interpreter. Step 1 is verified.

## Remaining work

1. Inspect and publish the completed consistency human-review evidence and updated documentation using manual Git steps.
2. Record the pilot calibration decision before freezing final evaluation settings.
3. Prepare the separate final 50-case set with pilot source IDs and contexts excluded, then run the final evaluation.
4. Complete remaining real-model regression coverage, reporting and final analysis.
5. Finish portfolio documentation and publication. Independent blinded review remains an additional validation option; the present manual review's prior exposure is disclosed.

## Hardware constraints

The screenshots show 16 GB installed RAM (15.7 GB usable) with 1.9 GB available at capture. Iris Xe uses shared system RAM. Begin with CPU inference and one loaded model at a time; both original models have now completed bounded sequential CPU setup checks. Broader context windows, QA behavior, and judge accuracy remain to be validated.

## Publication status

The baseline, offline CI, response-consistency experiment, ten-case manual review and consistency human-review tooling are published in [the GitHub repository](https://github.com/ibne86/llm-evaluation); PR #5 was merged into main. The user created `codex/consistency-review-results` to publish the completed consistency review and its findings. Both sets of human judgments and reasons are complete. Commits, pushes, merges and branch cleanup remain manual. Original working reviews and runs remain ignored; the separate final 50-case dataset has not been prepared.

## Step 2a: Ollama application

- Installed/verified the Ollama Windows application, server version 0.40.16.
- Verified http://127.0.0.1:11434/api/version and the command-line client.
- Model count reported by the local service: 0. No model downloads were requested.
- Project Python dependencies are installed and verified; see Step 2b below.
- User confirmed that the local API verification command works. Step 2a is complete.



## Step 2b: Python dependencies

- Installed and verified deepeval 4.3.3, ollama 0.6.3, pytest 9.2.0, and pip 26.3 inside .venv.
- pip check found no incompatible dependencies.
- DeepEval metric imports, schema-aware judge method signatures, pytest startup, and the Python client's local Ollama connection passed.
- Pinned direct dependencies in requirements.txt and saved the tested Windows dependency snapshot in requirements-lock.txt.
- Added scripts/check_environment.py and docs/setup-python-dependencies.md. The diagnostic opts out of DeepEval telemetry before import and makes no inference request.
- The user confirmed the environment diagnostic passed. Step 2b is complete. Real judge output and evaluation tests remain unverified.


## Step 2c authorization

The user asked to proceed with available memory. Run the small answer model first with bounded CPU settings, record fresh memory snapshots and response timings, and unload it afterward. The larger judge remains pending.


## Step 2c: first answer-model benchmark

- Model: qwen2.5:1.5b; manifest digest: 65ec06548149b04c096a120e4a6da9d4017ea809c91734ea5631e89f96ddc57b.
- Execution status: completed; model unloaded: True.
- Initial options: CPU only, 1024-token context, 64-token output limit, prompt batch 32, 4 CPU threads, temperature 0, seed 42.
- Completed response count: 2; exact-year setup checks passed: 2. These are not DeepEval evaluation scores.
- Available physical RAM immediately before inference: 1.43 GiB.
- Report: results/runs/baseline-20261110T052732276625Z.json, with a companion Markdown report.
- The prompt is synthetic setup data, separate from all evaluation datasets. The warm repeat can benefit from caching. Memory readings are system snapshots, not process-only or peak measurements.
- Current checkpoint: review the saved summary. Judge setup, the 10-case DeepEval pilot and the 50-case evaluation are still pending.


## Step 2d: originally planned judge feasibility

- Original judge remains qwen3:4b; no replacement model was selected or downloaded.
- Diagnostic status: structured_controls_passed; judge unloaded/not running after the request: True.
- Available system RAM before the request: 2.02 GiB.
- Structured controls completed: 2.
- DeepEval metric status: not attempted; structured-output feasibility must pass first.
- Report: results/runs/judge-check-20261110T053831329347Z.json, with a Markdown companion.
- Next: inspect the report. Run the DeepEval integration only if the original judge's native structured-output checks succeed; otherwise investigate the recorded failure before proposing a model change.

## Step 2e: DeepEval integration with the unchanged judge

- Judge is still qwen3:4b. The native structured-output controls passed; no alternate model was used.
- Added the local source package and a small extension of DeepEval's OllamaModel for think=False, bounded requests, response validation and conservative prompt budgeting.
- Judge adapter unit tests passed before model evaluation (9 tests).
- Actual DeepEval diagnostic status: passed; judge unloaded: True.
- Controls completed: 2. Metric: answer relevancy; threshold 0.7; explanations included; sequential LLM mode.
- Detailed report: results/runs/deepeval-judge-20261110T054915543161Z.json, plus Markdown.
- Source package installed in editable mode. Third-party requirements-lock.txt excludes the local editable path.
- Next checkpoint: review the saved integration report. The 10-case SQuAD/custom development pilot and human validation remain pending. No final 50-case dataset was prepared.


## Judge integration review

Both original models remain unchanged. The qwen3:4b judge passed two native schema controls and two DeepEval relevancy controls; adapter tests pass (9 tests). The judge was unloaded after the integration run. The negative-control explanation is internally inconsistent and is explicitly flagged in the report, without changing its original score or explanation. Future request logs preserve raw structured responses and metric verdicts for investigation. No real human reviews or SQuAD pilot evaluations have been completed.



## Milestone 1 execution complete — user review pending

- Prepared and validated 10 development cases: 6 answerable SQuAD, 2 impossible SQuAD, 1 ambiguity and 1 context-instruction case.
- Preserved source IDs, answer spans, aliases, source hash, selection rules and CC BY-SA 4.0 attribution.
- Added configuration, dataset validation, context-only generation, deterministic abstention checks, DeepEval metrics, resumable execution and reports.
- Offline checks: 32 passed; pip check passed.
- Original model pair unchanged. All 10 answers and all 30 metrics completed with 0 case execution errors and 0 phase errors. Both models unloaded successfully.
- Automated outcomes: 2 passes and 8 flags. These are not established accuracy figures.
- Exact-abstention checks on SQuAD impossible cases: 0/2.
- Human validation not started; no agreement rate is available.
- Verified all 20 G-Eval prompt hashes. Identified exact-reference judge misgrading on 09:00 and additional judge review candidates; original outputs and scores preserved.
- Reports: results/runs/pilot-20261110T062839549380Z; portable examples are in results/examples.
- Generation request time: 21.907 seconds; metric request time: 584.551 seconds. These exclude some orchestration/cleanup overhead and do not estimate the final suite's runtime.
- Stop at pilot review. No final 50-case set, model change, GitHub repository, push or publication was performed.

## GitHub baseline published

- The user manually created five focused commits for dependencies, local judge diagnostics, dataset/configuration, the evaluation pipeline and documentation/results.
- The user created https://github.com/ibne86/llm-evaluation and pushed the five commits to `main`.
- Baseline head: `76a88ea`; the user then created `codex/judge-validation` from a clean working tree.

## Human review workflow implemented — real labels pending

- Added a fixed human rubric and an offline review-packet command for all ten saved pilot cases; no judge scores or explanations are included in the packet.
- Added validated human labels, declared prior exposure, source/evidence fingerprint checks, paired-decision agreement, per-metric counts and disagreement reports.
- Missing and uncertain ratings do not count as pass/fail pairs; no labels means no agreement rate. Original outputs, scores and reviews are preserved.
- Added a step-by-step human validation guide. Working reviews and comparisons in `results/reviews/` are ignored by Git.
- Offline unit tests: 56 passed, including 24 synthetic/review workflow checks. Synthetic fixture labels are not human validation.
- Both original models and all evaluation prompts/settings remain unchanged. No new inference is needed for this feature.
- Next checkpoint: the user enters genuine human ratings, compares them with the original pilot and investigates disagreements. Final 50-case evaluation and consistency tests remain pending.

## Human-review feature merged

- PR #1 merged into `main`; the user updated local `main` to `fc652ae` and deleted the completed feature branch locally and on GitHub.
- The assistant reviewed all ten pilot cases in separate, clearly attributed local files. These ratings do not complete human validation; genuine human labels remain pending.

## Offline test CI verified and merged

- Added a GitHub Actions workflow on `codex/ci-tests` for pushes, pull requests and manual runs.
- The job targets Windows Server 2025 and Python 3.12, installs the existing dependency snapshot and local package, checks dependency compatibility and runs the offline unit suite.
- Added a JUnit XML artifact, dependency caching, a job timeout and cancellation of superseded runs. Official actions use verified commit SHA pins and read-only repository contents access.
- Added a CI guide and a README entry explaining scope, results and local reproduction.
- Local verification: a fresh Python 3.12.1 environment installed the locked dependencies and editable package, passed `pip check`, and passed all 56 unit tests with a JUnit report. Parsed the workflow YAML, verified action SHAs and input names against official action definitions, and checked the four run commands with PowerShell's parser.
- The [first GitHub run](https://github.com/ibne86/llm-evaluation/actions/runs/42965274154) passed all 56 tests in 2.09 seconds on CPython 3.12.10. Dependency compatibility and JUnit artifact upload succeeded.
- The user merged PR #2. At the user's explicit request, local `main` was fast-forwarded to `a1b23cc` and the completed CI branch was deleted locally and remotely. The user then requested manual Git instructions for future work.

## Response consistency implemented and locally verified

- The user created `codex/response-consistency` from the updated `main`.
- Added a no-inference preview, bounded repeats, per-repeat generation/evaluation, separate text-stability and quality counts, and JSON/CSV/Markdown reports.
- Default coverage: the first answerable, unanswerable and embedded-instruction pilot cases, three repeats each. Nine answer requests and 27 metric evaluations use the existing model pair, seed, prompts, thresholds and CPU settings.
- Added checkpointed resume with case, response, configuration, model/software and source-signature validation. Completed logical trials are retained; failed or unfinished work can be retried.
- Offline unit tests: 85 passed, including 29 new checks for stable wrong answers, acceptable wording variation, failed requests, model cleanup, report integrity, interrupted work and resume behavior. These use fake models and do not establish live-model consistency.
- The user previewed the plan, then ran the actual local experiment: `consistency-20261111T061137670564Z`. All nine answers and 27 metrics completed, with zero execution/phase errors and both models unloaded.
- All three cases repeated the exact same answer on every trial. Automated outcomes: five trial passes, four flags; only one case passed all repeats. The unanswerable county question consistently produced `15`, and the opening-time question consistently produced `09:00` while receiving changing correctness grades.
- Verified the saved summary, all nine answer-prompt hashes, all 18 G-Eval prompt hashes and raw-score normalization. Identical opening-time grading prompts produced different raw scores; this is judge variability rather than changed answer text. No cause is established.
- Prepared portable result/summary copies and separate assistant audit notes in `results/examples`. Preserved the original local experiment and original scores/reasons. Elapsed time: 459.903 seconds, including 11.703 seconds of generation requests and 446.937 seconds of metric evaluations.
- Next checkpoint: review the findings, make focused code/results commits and open a pull request. Genuine human validation and the separate final 50-case evaluation remain pending.

## Earlier AI review examples — retired on 12 November 2026

- The user created `codex/pilot-review-findings` from a clean, up-to-date `main` after merging the response-consistency feature.
- Prepared four portable review/comparison examples and a findings guide. Ibne is the review owner; AI assessment authorship and declared prior exposure are explicit. Local working files and the genuine-human review worksheet are preserved.
- Reviewed coverage: ten cases and 30 metric decisions. Matching AI/local-judge decisions: 25/30 (83.3%); relevancy 8/10, correctness 9/10, groundedness 8/10. Five disagreements include one interpretation-sensitive nationality inference.
- Verified the original source fingerprint, full case evidence, all 30 paired decisions, per-metric counts, the five investigation records, the refreshed review fingerprint and documentation links. No inference, model/configuration change or source-score rewrite was performed. The last verified offline unit suite remains 85 passed; this documentation/example change does not modify executable code.
- Next checkpoint: the user inspects and commits these changes, then pushes and merges manually. Genuine human validation and the final 50-case evaluation remain outstanding.

## Completed manual pilot review aligned across code, reports and documentation

- Ibne confirmed completing the manual check and recorded 30/30 human pass/fail verdicts. Human/local-judge agreement is 25/30 (83.3%); relevancy 8/10, correctness 9/10, groundedness 8/10. Human/earlier-assistant agreement is 30/30. Prior exposure was declared; written human reasons were not collected.
- Added an explicit optional-reason collection policy while preserving the required-reason default and legacy packets. Supported human metadata is validated; completion is derived from verdicts. Source, rubric and case evidence checks remain enforced.
- Added optional secondary AI-reference comparison, per-input content fingerprints, written-reason coverage, all paired decisions and portable evidence links. The optional standalone assistant comparison was later retired after the manual review was completed.
- Prepared publishable human worksheet and JSON/Markdown comparison examples, fixed the findings links and repaired the earlier AI comparison's Markdown tables. Local pre-alignment worksheet/report snapshots are archived under ignored results/reviews/archive.
- Verification: 103 offline unit tests passed, including the real published review reproduction and new checks for metadata, optional reasons, fingerprints, AI-reference validation, denominators and CLI preservation. Report counts, source evidence, relative links and table rendering were checked without model inference.
- The original model pair, settings, original pilot/consistency outputs and raw scores are unchanged. The separate consistency trials have no human ratings. Next: inspect changes, make focused commits and publish manually; then record the calibration decision before freezing final evaluation settings.

## Follow-up manual review with written reasons — 12 November 2026

- Ibne added 30 written human reasons in a separate review copy. All ten cases, source evidence and 30 pass/fail verdicts are unchanged. Human/local-judge agreement remains 25/30 (83.3%); human/earlier-assistant agreement remains 30/30.
- Prepared a new publishable worksheet and JSON/Markdown comparison with reasons, retaining the initial zero-reason version and all original model responses and judge scores. The follow-up keeps the optional-reason policy, with actual coverage of 30/30 written reasons.
- Updated current documentation, evidence links, reproduction commands and per-input fingerprints. Verified every written reason against the local worksheet, all paired decisions, the unchanged historical versions, relative links and rendered report tables. No model inference or executable-code changes were needed; the last offline suite result remains 103 passed.
- The review remains non-blinded because prior AI findings had been seen. Independent blinded validation and separate human ratings for the nine consistency responses remain outstanding.
- Next: inspect and publish this focused update manually, then implement the nine-trial human-review worksheet before final evaluation work.

## Human-versus-judge cleanup — 12 November 2026

- Removed the redundant standalone AI review/comparison files and obsolete local comparison snapshots. Kept the original model results, both versions of the human worksheet, written reasons, and human-versus-local-judge reports.
- Removed the optional assistant-reference argument, secondary-comparison code, report fields, evidence links and obsolete feature tests. Rebuilt the human reports using only source results and the human worksheet; all 30 verdicts, 30 written reasons, original scores and 25/30 agreement remain unchanged.
- Validation: 96 offline tests passed, including reproduction of both published human-review versions. Verified input fingerprints, primary comparison fields, Markdown tables, evidence links and the absence of deleted-file dependencies. No model inference was run.
- Prior exposure to AI findings remains disclosed; the review is non-blinded. Independent blinded validation and separate manual ratings for the nine consistency responses remain outstanding. Git staging, commits, pushes and branch cleanup remain manual.

## Consistency human-review workflow implemented — ratings pending

- The user created `codex/consistency-human-review` from updated main. Extended the offline review command to validate and review saved consistency runs without model inference; existing schema-version-1 pilot packets remain compatible.
- Added schema-version-2 trial worksheets that retain the original case ID, integer repeat and fixed trial ID. Reused the source trial-matrix checks and retained source/evidence fingerprints, thresholds, judgment validation and reason policies.
- Comparisons retain trial identity, distinguish question/trial/rating coverage and exclude uncertain or unreviewed judgments. Fully reviewed questions require all their repeats to be rated. Repeated observations are explicitly described as correlated.
- Prepared the real nine-response local worksheet with 27 null verdicts, empty reasons and declared prior exposure. No human ratings were invented or copied, and no completed human agreement is claimed.
- Validation: 127 offline tests passed, including 31 new checks for repeated identities, duplicated/missing trials, changed evidence, metadata, response hashes, incomplete sources, trial-specific grading, reason policies, reordered reviews and CLI preservation. The original 96 tests still pass.
- Next: the user reviews all nine responses and supplies 27 judgments/reasons, then generates a fresh human-versus-local-judge comparison. Original pilot and consistency measurements and existing manual reviews remain unchanged.

## Consistency human review completed — publication prepared

- Ibne submitted nine trial reviews with 27 pass/fail judgments and 27 written reasons. All trial identities, source evidence, rubric and prior-exposure metadata pass validation. No ratings or reasons were supplied or rewritten by the assistant during publication preparation.
- Human/local-judge agreement is 24/27 (88.9%): relevancy 7/9, correctness 8/9, groundedness 9/9. The three disagreements concern county-answer relevancy on repeats 2 and 3 and opening-time correctness on repeat 1. Original judge scores and explanations are preserved.
- The human review passes all three criteria on six trials and flags three county-answer trials, while the original automated run records five passes and four flags. Completion, agreement and quality outcomes remain distinct. The ten-case pilot's 25/30 agreement is reported separately; overlapping and repeated observations are not pooled into an accuracy estimate.
- Prepared publishable worksheet and JSON/Markdown comparison copies, rebased evidence links and updated current documentation. Verified source/worksheet fingerprints, all paired decisions, written-reason coverage, original local files, relative links and table rendering. Reproduced the report offline; no model inference or executable-code changes were needed. The last offline suite result remains 127 passed.
- The user created codex/consistency-review-results from clean main. Next: inspect and publish this focused update manually, then record the judge-calibration decision and freeze settings before preparing the separate final 50-case set. Both reviews remain non-blinded; independent blinded review would provide additional validation.
