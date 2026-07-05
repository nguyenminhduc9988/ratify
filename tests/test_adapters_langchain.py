"""Tests for the duck-typed LangChain adapter (no langchain dependency)."""

from __future__ import annotations

from typing import Any

from ratify import Contract, Scope, checks
from ratify.adapters.langchain import RatifyCallbackHandler, guard_runnable


class FakeMessage:
    """Stand-in for a LangChain AIMessage with a `.content` attribute."""

    def __init__(self, content: str) -> None:
        self.content = content


class FakeRunnable:
    """Minimal Runnable that drives callbacks like LangChain would."""

    def __init__(self, *, tools: list[str], answer: str, fail_tool: str | None = None) -> None:
        self.tools = tools
        self.answer = answer
        self.fail_tool = fail_tool

    def invoke(self, input: Any, config: dict[str, Any] | None = None) -> FakeMessage:
        handlers = (config or {}).get("callbacks", [])
        for name in self.tools:
            for h in handlers:
                h.on_tool_start({"name": name}, f"{input}")
                if name == self.fail_tool:
                    h.on_tool_error(RuntimeError("boom"))
                else:
                    h.on_tool_end(f"{name}-result")
        return FakeMessage(self.answer)


def test_callback_handler_records_tools() -> None:
    handler = RatifyCallbackHandler()
    handler.on_tool_start({"name": "search"}, "query")
    handler.on_tool_end("some result")
    assert handler.trajectory.tool_names == ["search"]
    assert handler.trajectory.tool_calls[0].result == "some result"


def test_callback_handler_records_errors() -> None:
    handler = RatifyCallbackHandler()
    handler.on_tool_start({"name": "flaky"}, "x")
    handler.on_tool_error(RuntimeError("nope"))
    call = handler.trajectory.tool_calls[0]
    assert call.ok is False and call.error == "nope"


def test_callback_handler_ignores_unknown_callbacks() -> None:
    handler = RatifyCallbackHandler()
    # unknown on_* callbacks should be no-ops, not errors
    handler.on_llm_start({}, ["prompt"])  # type: ignore[attr-defined]
    handler.on_chain_end({})  # type: ignore[attr-defined]
    assert handler.trajectory.tool_names == []


def test_guard_runnable_pass() -> None:
    contract = (
        Contract("c")
        .hard("kb", "must search", scope=Scope.TRAJECTORY, check=checks.used_tool("search"))
        .hard("no-at", "no @", scope=Scope.OUTPUT, check=checks.excludes("@"))
    )
    runnable = FakeRunnable(tools=["search"], answer="clean answer")
    output, report = guard_runnable(runnable, contract, "question")
    assert output.content == "clean answer"
    assert report.passed


def test_guard_runnable_detects_missing_tool() -> None:
    contract = Contract("c").hard(
        "kb", "must search", scope=Scope.TRAJECTORY, check=checks.used_tool("search")
    )
    runnable = FakeRunnable(tools=["calculator"], answer="answer")
    _, report = guard_runnable(runnable, contract, "q")
    assert not report.passed
    assert report.violations[0].clause_id == "kb"


def test_guard_runnable_extracts_content() -> None:
    contract = Contract("c").hard(
        "long", "min length", scope=Scope.OUTPUT, check=checks.min_length(3)
    )
    runnable = FakeRunnable(tools=[], answer="hello world")
    _, report = guard_runnable(runnable, contract, "q")
    assert report.passed  # content extracted from FakeMessage, not repr
