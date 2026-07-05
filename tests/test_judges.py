"""Tests for provider judge adapters using fake clients (no network)."""

from __future__ import annotations

from typing import Any

from ratify import CheckContext
from ratify.judges import AnthropicJudge, OpenAIJudge, _parse


def test_parse_valid_json() -> None:
    v = _parse('{"score": 0.8, "rationale": "mostly good"}')
    assert v.score == 0.8 and v.rationale == "mostly good"


def test_parse_embedded_json() -> None:
    v = _parse('Here is my verdict: {"score": 0.3, "rationale": "weak"} done')
    assert v.score == 0.3


def test_parse_clamps_out_of_range() -> None:
    assert _parse('{"score": 5}').score == 1.0
    assert _parse('{"score": -2}').score == 0.0


def test_parse_unparseable() -> None:
    assert _parse("no json here").score == 0.0
    assert _parse('{"score": "not-a-number"}').score == 0.0


# -- fake clients ------------------------------------------------------------


class _FakeOpenAI:
    def __init__(self, content: str) -> None:
        self._content = content

        class _Choices:
            def __init__(self, c: str) -> None:
                self.message = type("M", (), {"content": c})()

        class _Completions:
            def create(inner_self, **kwargs: Any) -> Any:  # noqa: N805
                return type("R", (), {"choices": [_Choices(content)]})()

        self.chat = type("Chat", (), {"completions": _Completions()})()


class _FakeAnthropic:
    def __init__(self, text: str) -> None:
        class _Messages:
            def create(inner_self, **kwargs: Any) -> Any:  # noqa: N805
                return type("R", (), {"content": [type("B", (), {"text": text})()]})()

        self.messages = _Messages()


def test_openai_judge_with_fake_client() -> None:
    client = _FakeOpenAI('{"score": 0.9, "rationale": "great"}')
    judge = OpenAIJudge(client=client)
    v = judge.evaluate("be helpful", CheckContext(output="I can help!"))
    assert v.score == 0.9 and v.rationale == "great"


def test_anthropic_judge_with_fake_client() -> None:
    client = _FakeAnthropic('{"score": 0.2, "rationale": "off-topic"}')
    judge = AnthropicJudge(client=client)
    v = judge.evaluate("stay on topic", CheckContext(output="weather is nice"))
    assert v.score == 0.2
