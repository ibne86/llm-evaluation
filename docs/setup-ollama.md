# Step 2a: Ollama application and local service

Step 1 is verified: the user's screenshots show PyCharm's Python Console and PowerShell both resolving Python to `C:\Users\khani\Projects\llm-evaluation\.venv\Scripts\python.exe`.

Ollama is a native Windows application that runs language models and exposes a local HTTP API. It is separate from the Python `ollama` package, which will be installed inside `.venv` in a later checkpoint so our scripts can talk to this application.

## Installation

Use the Ollama package from the Windows Package Manager community catalog:

```powershell
winget install --id Ollama.Ollama --exact --source winget --scope user --silent --accept-source-agreements --accept-package-agreements --disable-interactivity
```

WinGet downloads the publisher's installer and verifies its manifest hash. Do not bypass installer hash checks. The fallback official installer is available at https://ollama.com/download/windows.

This checkpoint installs only the application. Models, Python dependencies, and evaluation implementation are separate steps.

## Verify in PyCharm's Terminal

Use the **Terminal** tab with the `PS` prompt. Run this PowerShell command:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version'
```

Expected result: a `version` field containing the installed Ollama server version. `127.0.0.1` means this computer; the request goes to the local application.

To check the command-line client without relying on an already-open terminal's PATH:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" --version
```

The `&` asks PowerShell to run the executable at the quoted path. A PyCharm session that was open before installation may need restarting before the shorter `ollama` command is found on PATH.

## Next checkpoint

After the user verifies the local service, install the project-specific Python dependencies in `.venv` and test imports. Download models and measure available memory, response speed, and structured-output behavior in subsequent steps.

Official references:

- https://docs.ollama.com/windows
- https://learn.microsoft.com/en-us/windows/package-manager/winget/install
