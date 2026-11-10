# Step 2c: first answer-model performance baseline

The user verified the environment diagnostic and asked to proceed with the available memory. The last manually reported available RAM was 1.9 GB. The benchmark reads fresh Windows physical-memory snapshots during execution; it does not require the user to free a fixed amount of RAM first.

## Scope

Download `qwen2.5:1.5b` if needed and run two short sequential requests against the explicit local Ollama service. The model's catalog entry lists a 986 MB Q4_K_M download. Runtime memory can be higher.

The initial options are deliberately modest:

| Option | Value | Purpose |
| --- | ---: | --- |
| num_gpu | 0 | Request CPU inference |
| num_ctx | 1024 | Limit the initial context window |
| num_predict | 64 | Bound the answer length |
| num_batch | 32 | Use a small prompt-processing batch |
| num_thread | 4 | Begin with modest CPU parallelism |
| temperature / seed | 0 / 42 | Record repeatable starting settings, without guaranteeing identical outputs |

The context contains an invented library opening year. It is a setup fixture, separate from SQuAD, the 10-case pilot, and the final evaluation. The exact-year comparison checks a deliberately requested output format; it is not the project's semantic correctness metric.

The second request repeats the prompt and may benefit from caching. It is called a warm repeat, rather than an independent throughput estimate.

## Running and reading the diagnostic

The setup run uses:

```powershell
& 'C:\Users\khani\Projects\llm-evaluation\.venv\Scripts\python.exe' 'C:\Users\khani\Projects\llm-evaluation\scripts\benchmark_model.py' --pull
```

This downloads only the answer model if absent. It refuses to start a cold benchmark while another model is already loaded. It never stops an existing unrelated model.

After the run, read the latest saved summary without loading a model:

```powershell
& 'C:\Users\khani\Projects\llm-evaluation\.venv\Scripts\python.exe' 'C:\Users\khani\Projects\llm-evaluation\scripts\benchmark_model.py' --summary
```

JSON and Markdown reports are saved under the ignored `results/runs` directory. They contain the actual response, options, model digest, wall/load/generation timings, token counts, Windows memory snapshots, Ollama's loaded-model allocation, and cleanup result.

## Memory and cleanup

The script uses Windows `GlobalMemoryStatusEx` to record available system RAM before inference, after each response, and after unloading. These are snapshots of the whole system, not continuous peaks or model-only process memory. Other applications and Windows caching can change the values.

The model is kept alive briefly between requests. A `finally` block requests unloading with `keep_alive=0` even after inference errors. It then checks Ollama's running-model list. A short keep-alive provides a fallback if the script terminates unexpectedly. A timeout or server error is recorded as an incomplete benchmark, not a successful test.

## Next checkpoint

Review actual response speed, memory snapshots, and the unload result before expanding the context window or attempting the larger judge. The judge model and all evaluation datasets are still pending. Passing this small diagnostic does not satisfy the separate 10-case DeepEval pilot gate.

Official references:

- https://ollama.com/library/qwen2.5:1.5b
- https://docs.ollama.com/api/chat
- https://docs.ollama.com/api/generate
- https://docs.ollama.com/api/ps
- https://docs.ollama.com/faq
- https://learn.microsoft.com/windows/win32/api/sysinfoapi/ns-sysinfoapi-memorystatusex
