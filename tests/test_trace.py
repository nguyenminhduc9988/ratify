"""Tests for Trajectory / Step / ToolCall."""

from __future__ import annotations

from ratify import Step, ToolCall, Trajectory


def test_record_tool_and_query() -> None:
    t = Trajectory()
    t.record_tool("search", args={"q": "hi"}, result=["a"])
    t.record_tool("search", args={"q": "yo"})
    t.record_tool("summarize")
    assert t.tool_names == ["search", "search", "summarize"]
    assert t.used_tool("search")
    assert not t.used_tool("delete")
    assert t.count_tool("search") == 2
    assert len(t) == 3


def test_add_returns_step() -> None:
    t = Trajectory()
    step = t.add(Step(kind="think", content="hmm"))
    assert step.kind == "think"
    assert list(t)[0] is step


def test_tool_calls_property() -> None:
    t = Trajectory()
    call = t.record_tool("x", ok=False, error="boom")
    assert isinstance(call, ToolCall)
    assert t.tool_calls[0].error == "boom"
    assert t.tool_calls[0].ok is False


def test_empty_trajectory() -> None:
    t = Trajectory()
    assert t.tool_names == []
    assert not t.used_tool("anything")
    assert t.count_tool("anything") == 0
