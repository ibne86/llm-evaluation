"""Verify that malformed or incomplete judge outputs cannot become scores."""

import asyncio
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, Field, ValidationError

from llm_eval.judge import LocalOllamaJudge


class Score(BaseModel):
    score: float = Field(ge=0, le=1)


class FakeClient:
    def __init__(self, content='{"score": 1}', done_reason="stop", error=None, thinking=None):
        self.content = content
        self.done_reason = done_reason
        self.error = error
        self.thinking = thinking
        self.closed = False
        self.request = None

    def chat(self, **kwargs):
        self.request = kwargs
        if self.error:
            raise self.error
        return SimpleNamespace(
            done=True,
            done_reason=self.done_reason,
            message=SimpleNamespace(content=self.content, thinking=self.thinking),
            prompt_eval_count=20,
            eval_count=8,
        )

    def close(self):
        self.closed = True


@pytest.fixture
def judge():
    instance = LocalOllamaJudge()
    yield instance
    instance.close()


def test_valid_schema_uses_local_bounded_policy(judge, monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(judge, "load_model", lambda: client)
    result, cost = judge.generate("Score the supplied answer.", Score)
    assert result.score == 1
    assert cost == 0
    assert client.request["model"] == "qwen3:4b"
    assert client.request["think"] is False
    assert client.request["keep_alive"] == "30s"
    assert client.request["format"] == Score.model_json_schema()
    assert client.request["options"]["temperature"] == 0
    assert client.request["options"]["num_gpu"] == 0
    assert client.closed


@pytest.mark.parametrize("content", ['{"score":', '{"score": 2}'])
def test_invalid_json_or_out_of_range_score_is_an_error(judge, monkeypatch, content):
    client = FakeClient(content=content)
    monkeypatch.setattr(judge, "load_model", lambda: client)
    with pytest.raises(ValidationError):
        judge.generate("Score the supplied answer.", Score)
    assert client.closed
    assert judge.request_log[-1]["status"] == "error"
    assert judge.request_log[-1]["response_content"] == content


def test_truncated_response_is_rejected_even_if_json_parses(judge, monkeypatch):
    client = FakeClient(done_reason="length")
    monkeypatch.setattr(judge, "load_model", lambda: client)
    with pytest.raises(ValueError, match="incomplete"):
        judge.generate("Score the supplied answer.", Score)
    assert client.closed


@pytest.mark.parametrize("content,thinking", [("", None), ('{"score": 1}', "unexpected reasoning")])
def test_empty_or_unexpected_thinking_output_is_an_error(judge, monkeypatch, content, thinking):
    client = FakeClient(content=content, thinking=thinking)
    monkeypatch.setattr(judge, "load_model", lambda: client)
    with pytest.raises(ValueError):
        judge.generate("Score the supplied answer.", Score)
    assert client.closed


def test_network_error_is_not_replaced_with_a_score(judge, monkeypatch):
    client = FakeClient(error=TimeoutError("request timed out"))
    monkeypatch.setattr(judge, "load_model", lambda: client)
    with pytest.raises(TimeoutError):
        judge.generate("Score the supplied answer.", Score)
    assert client.closed
    assert judge.request_log[-1]["status"] == "error"


def test_overlong_prompt_is_rejected_before_client_request(judge, monkeypatch):
    def unexpected_client():
        pytest.fail("The overlong prompt must not reach the client.")
    monkeypatch.setattr(judge, "load_model", unexpected_client)
    with pytest.raises(ValueError, match="context budget"):
        judge.generate("x" * 2048, Score)


def test_async_path_preserves_schema_and_thinking_policy(judge, monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(judge, "load_model", lambda: client)
    result, _ = asyncio.run(judge.a_generate("Score the supplied answer.", Score))
    assert result.score == 1
    assert client.request["think"] is False
    assert client.closed
