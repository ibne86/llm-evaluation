# Step 1: Windows and PyCharm setup

The project uses Python 3.12.1, which is already installed. `.venv` is its virtual environment: a separate location for this project's Python packages.

## Open the project

1. Start PyCharm.
2. Choose **File > Open** (or **Open** on the welcome screen).
3. Select `C:\Users\khani\Projects\llm-evaluation`.
4. Open it in a new window if PyCharm asks, so your football project can remain separate.

## Select the existing Python environment

1. Press **Ctrl+Alt+S** to open Settings.
2. Find **Project: llm-evaluation > Python Interpreter**. You can also search Settings for **Python Interpreter**.
3. If the project's `.venv` is already selected, retain it. Otherwise choose **Add Interpreter > Add Local Interpreter**.
4. Choose the existing environment/interpreter option. Browse to:

   `C:\Users\khani\Projects\llm-evaluation\.venv\Scripts\python.exe`

5. Apply the selection. Keep package inheritance from the global Python disabled.

PyCharm 2024.3.4 may label these options differently from newer versions. The important outcome is that the selected executable is the project's `.venv\Scripts\python.exe`.

## Verify in PyCharm's terminal

Open the **Terminal** tool window in the project. These PowerShell commands use the environment directly, so they do not depend on activation or changes to Windows execution policy:

```powershell
Set-Location -LiteralPath 'C:\Users\khani\Projects\llm-evaluation'
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable); print('Isolated environment:', sys.prefix != sys.base_prefix)"
.\.venv\Scripts\python.exe -m pip --version
git status --short --branch
```

Expected observations:

- Python version is `3.12.1`.
- Executable path ends with `llm-evaluation\.venv\Scripts\python.exe`.
- `Isolated environment: True`.
- pip's location is inside the project's `.venv`.
- Git reports branch `codex/setup` with no commits yet and the new documentation files as untracked. `.venv` is ignored.

The initial documentation files will remain uncommitted until reviewed. No GitHub remote has been configured.

## Pause here

Confirm the interpreter in PyCharm and share the verification output before proceeding to Ollama and dependency installation. No model or evaluation implementation is required for this checkpoint.

Before later model tests, save your work and close unused applications. Recheck Task Manager's available RAM; the hardware screenshot showed only 1.9 GB free. The GPU's shared-memory limit is part of system RAM, not extra capacity.

Official interpreter guidance: https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html
