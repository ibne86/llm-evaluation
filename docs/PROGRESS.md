# Project progress

Updated: 11 November 2026.

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

1. User review of the completed 10-case pilot and the separate answer-model/judge findings.
2. Collect genuine human labels with a predefined rubric and investigate judge disagreements before trusting larger-run scores.
3. After pilot review and calibration decisions, freeze settings and prepare the separate final 50-case set.
4. Add response consistency tests and the remaining regression/reporting features.
5. Compare human and judge decisions, report agreement with denominators and limitations, and finalize documentation.
6. Review publication contents and publish only with explicit user approval.

## Hardware constraints

The screenshots show 16 GB installed RAM (15.7 GB usable) with 1.9 GB available at capture. Iris Xe uses shared system RAM. Begin with CPU inference and one loaded model at a time; both original models have now completed bounded sequential CPU setup checks. Broader context windows, QA behavior, and judge accuracy remain to be validated.

## Publication status

Local setup only. No GitHub repository, remote, commit, or push was created during initialization. Python dependencies are installed inside .venv. The qwen2.5:1.5b answer model is downloaded into Ollama storage, and two synthetic setup responses are recorded locally. Synthetic setup metric results are recorded. The 10-case pilot is prepared and executed. The final evaluation dataset remains unprepared.


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

## Offline test CI configured — first GitHub execution pending

- Added a GitHub Actions workflow on `codex/ci-tests` for pushes, pull requests and manual runs.
- The job targets Windows Server 2025 and Python 3.12, installs the existing dependency snapshot and local package, checks dependency compatibility and runs the offline unit suite.
- Added a JUnit XML artifact, dependency caching, a job timeout and cancellation of superseded runs. Official actions use verified commit SHA pins and read-only repository contents access.
- Added a CI guide and a README entry explaining scope, results and local reproduction.
- Local verification: a fresh Python 3.12.1 environment installed the locked dependencies and editable package, passed `pip check`, and passed all 56 unit tests with a JUnit report. Parsed the workflow YAML, verified action SHAs and input names against official action definitions, and checked the four run commands with PowerShell's parser. GitHub-hosted execution is still pending.
- Next checkpoint: review the changes, commit and push the branch manually, then inspect the first GitHub execution before merging this feature. Human validation, the final 50-case evaluation and consistency tests remain pending.
