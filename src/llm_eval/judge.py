"""Extend DeepEval's Ollama adapter with bounded local request settings."""

import asyncio
import hashlib
import os
import time

# Apply the project's local diagnostic settings before importing DeepEval.
os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "1"
os.environ["DEEPEVAL_DISABLE_DOTENV"] = "1"

from deepeval.models import OllamaModel

JUDGE_MODEL = "qwen3:4b"
OLLAMA_HOST = "http://127.0.0.1:11434"
JUDGE_OPTIONS = {
    "num_gpu": 0,
    "num_ctx": 2048,
    "num_predict": 256,
    "num_batch": 16,
    "num_thread": 4,
    "temperature": 0,
    "seed": 42,
}


class LocalOllamaJudge(OllamaModel):
    """Keep DeepEval's model integration while explicitly controlling each call."""

    def __init__(self, options=None, timeout=120):
        self.request_log = []
        active_options = {**JUDGE_OPTIONS, **(options or {})}
        super().__init__(
            model=JUDGE_MODEL,
            base_url=OLLAMA_HOST,
            temperature=active_options["temperature"],
            generation_kwargs=active_options,
            timeout=timeout,
            trust_env=False,
        )

    def generate(self, prompt, schema=None, audio=None):
        if not isinstance(prompt, str) or audio:
            raise ValueError("This project evaluates text-only prompts.")
        # Qwen uses byte-level tokenization. This conservative bound reserves
        # the output cap plus template overhead; it is not an exact token count.
        budget = len(prompt.encode("utf-8")) + self.generation_kwargs["num_predict"] + 64
        if budget > self.generation_kwargs["num_ctx"]:
            raise ValueError("Judge prompt exceeds the conservative context budget; it was not sent or truncated.")

        client = self.load_model()
        start = time.perf_counter()
        response = None
        status = "error"
        try:
            response = client.chat(
                model=self.name,
                messages=[{"role": "user", "content": prompt}],
                format=schema.model_json_schema() if schema else None,
                options={**self.generation_kwargs, "temperature": self.temperature},
                think=False,
                keep_alive="30s",
            )
            if not response.done or response.done_reason == "length":
                raise ValueError("Judge response was incomplete or reached its output limit.")
            if response.message.thinking:
                raise ValueError("Judge returned unexpected thinking output despite think=False.")
            content = response.message.content or ""
            if not content.strip():
                raise ValueError("Judge returned an empty answer.")
            result = schema.model_validate_json(content) if schema else content
            status = "completed"
            # DeepEval 4.3.3's native Ollama adapter returns output and API cost.
            return result, 0.0
        finally:
            self.request_log.append({
                "status": status,
                "schema": schema.__name__ if schema else None,
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "prompt_bytes": len(prompt.encode("utf-8")),
                "wall_seconds": round(time.perf_counter() - start, 6),
                "prompt_tokens": response.prompt_eval_count if response else None,
                "output_tokens": response.eval_count if response else None,
                "done_reason": response.done_reason if response else None,
                "response_content": response.message.content if response else None,
            })
            client.close()

    async def a_generate(self, prompt, schema=None, audio=None):
        # Preserve exactly the same validation and request policy in this path.
        return await asyncio.to_thread(self.generate, prompt, schema, audio)

    def close(self):
        """Close the base adapter's HTTP client; the runner unloads the model."""
        self.model.close()
