# Original judge setup: qwen3:4b

The planned model pair is unchanged: `qwen2.5:1.5b` for answers and `qwen3:4b` for judging.

## First check: can the original judge run and return structured output?

The judge catalog lists a roughly 2.5 GB Q4_K_M download. Its actual runtime memory must be measured separately. The answer model is unloaded before this test.

Run the setup diagnostic with:

```powershell
& 'C:\Users\khani\Projects\llm-evaluation\.venv\Scripts\python.exe' 'C:\Users\khani\Projects\llm-evaluation\scripts\check_judge.py' --pull
```

This downloads only the originally proposed judge if it is absent. It requests CPU inference, a 1024-token context, a 160-token response cap, a batch size of 16, four CPU threads, temperature zero, seed 42, and `think=false`.

Two synthetic controls ask the judge to distinguish a correct answer from an incorrect one. The required JSON has a binary `score` and a nonempty brief `reason`. Pydantic validates the structure and allowed values. The script records timings, model digest, control decisions, memory snapshots, errors, and cleanup status under the ignored `results/runs` directory.

If the original model cannot load, the test records the error and stops before DeepEval evaluation. It does not select a smaller judge, change Windows memory settings, stop unrelated models, or close applications. The judge is unloaded after the diagnostic where possible, with a short keep-alive as a fallback.

To read the latest saved result without running a model:

```powershell
& 'C:\Users\khani\Projects\llm-evaluation\.venv\Scripts\python.exe' 'C:\Users\khani\Projects\llm-evaluation\scripts\check_judge.py' --summary
```

## DeepEval integration comes after feasibility

The installed DeepEval 4.3.3 Ollama adapter already supports JSON-schema responses. Inspection of its actual implementation showed that generation options are passed through `options`, but the top-level `think` and `keep_alive` request fields are not exposed. Do not pass those fields inside `generation_kwargs` and assume they work.

If the native feasibility check passes, verify an actual DeepEval metric using the same local judge and bounded settings. Extend the built-in integration only where necessary to preserve thinking control, timeouts, output validation, and model cleanup.

Valid JSON and two setup controls do not establish judge accuracy. Broader controls, the separate 10-case pilot, and genuine human review remain required. The 50-case dataset gate is unchanged.

Official references:

- https://ollama.com/library/qwen3:4b
- https://docs.ollama.com/capabilities/structured-outputs
- https://docs.ollama.com/capabilities/thinking
- https://deepeval.com/integrations/models/ollama
