# Continuous integration: offline unit tests

The workflow in [ci.yml](../.github/workflows/ci.yml) is configured to check every push and pull request. After the workflow is merged into the default branch, it can also be started manually through **Actions → Offline unit tests → Run workflow**.

## What the job checks

The job runs on GitHub's `windows-2025` image with Python 3.12 and pip 26.3. It:

1. Checks out the source for the triggering commit or pull request.
2. Installs the third-party versions from `requirements-lock.txt`, using a pip download cache keyed by that file.
3. Installs the local project without resolving extra dependencies or using build isolation, as in the Windows installation guide.
4. Runs `python -m pip check`.
5. Runs `python -m pytest tests/unit -m "not integration" -q` and creates a JUnit XML test report.
6. Uploads that report as `unit-test-results-windows-python312`, retained for 14 days. Upload is attempted even after a failure; if installation failed before tests could run, the absent report produces a warning.

Each native command has its own workflow step so a failed installation or test command fails the job. The job has a 15-minute timeout, and a newer run cancels an older run in the same event/ref group.

The unit tests use fake model clients, synthetic fixtures and saved pilot data. This workflow runs the unit-test folder and excludes tests marked `integration`. Actual model evaluation is performed separately with the documented local Ollama commands. Dependency installation and artifact upload use the network; the test cases themselves need no inference service or API credentials.

DeepEval telemetry and dotenv loading are disabled before pytest imports plugins or application modules. The workflow grants read access to repository contents, and checkout does not persist its token for later commands. The three official actions are pinned to verified full commit SHAs, with version comments for maintenance.

## Read a result on GitHub

Open **Actions → Offline unit tests**, select a run, and open **Windows / Python 3.12**. The step logs show installation, dependency checks and pytest's result. A failing test produces a failed check; the job does not suppress its exit code.

After a run, the run page's **Artifacts** area contains the JUnit XML report when pytest produced one. The check also appears on the pull request. Branch-protection rules are a separate repository setting; adding this workflow does not make the check mandatory for merging.

## Reproduce the checks locally

With the project virtual environment activated in PowerShell:

```powershell
$env:DEEPEVAL_TELEMETRY_OPT_OUT = '1'
$env:DEEPEVAL_DISABLE_DOTENV = '1'
python -m pip check
python -m pytest tests/unit -m "not integration" -q
```

Run these commands separately and inspect each result. For a clean installation, follow the README's environment and pinned-dependency instructions first.

The existing dependency snapshot was originally tested on Windows/Python 3.12.1. CI uses the available stable patch release in the Python 3.12 series and a GitHub-hosted Windows Server image. A successful local check is not a substitute for inspecting the first GitHub run.

## Maintenance references

- [GitHub: building and testing Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).
- [GitHub: workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).
- [GitHub: secure use of actions](https://docs.github.com/en/actions/reference/security/secure-use).
- Official action releases used: [checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1), [setup-python v7.1.0](https://github.com/actions/setup-python/releases/tag/v7.1.0), and [upload-artifact v7.0.2](https://github.com/actions/upload-artifact/releases/tag/v7.0.2).
