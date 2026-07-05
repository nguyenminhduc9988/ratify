"""Tests for the deterministic check library."""

from __future__ import annotations

import pytest

from ratify import CheckContext, ResourceBudget, ToolCall, Trajectory, checks


def ctx(**kw: object) -> CheckContext:
    return CheckContext(**kw)  # type: ignore[arg-type]


# -- trivial -----------------------------------------------------------------


def test_always_pass_fail() -> None:
    assert checks.always_pass()(ctx()).passed
    r = checks.always_fail("nope")(ctx())
    assert not r.passed and r.detail == "nope"


def test_predicate() -> None:
    c = checks.predicate(lambda x: x.output == 42, "is 42")
    assert c(ctx(output=42)).passed
    assert not c(ctx(output=7)).passed


# -- text --------------------------------------------------------------------


def test_matches() -> None:
    c = checks.matches(r"\d{3}-\d{4}")
    assert c(ctx(output="call 555-1234")).passed
    assert not c(ctx(output="no number")).passed


def test_matches_input_field() -> None:
    c = checks.matches("hello", field="input")
    assert c(ctx(input="hello world")).passed


def test_excludes() -> None:
    c = checks.excludes("stupid", "idiot")
    assert c(ctx(output="you are great")).passed
    bad = c(ctx(output="you are STUPID"))
    assert not bad.passed and "stupid" in bad.detail.lower()


def test_excludes_case_sensitive() -> None:
    c = checks.excludes("Secret", ignore_case=False)
    assert c(ctx(output="secret")).passed  # different case -> allowed
    assert not c(ctx(output="Secret")).passed


def test_includes() -> None:
    c = checks.includes("sources", "citation")
    assert c(ctx(output="see sources and citation")).passed
    miss = c(ctx(output="see sources only"))
    assert not miss.passed and "citation" in miss.detail


def test_max_min_length() -> None:
    assert checks.max_length(5)(ctx(output="hi")).passed
    assert not checks.max_length(5)(ctx(output="toolong!")).passed
    assert checks.min_length(3)(ctx(output="abcd")).passed
    assert not checks.min_length(3)(ctx(output="ab")).passed


# -- structured --------------------------------------------------------------


def test_is_json() -> None:
    assert checks.is_json()(ctx(output='{"a": 1}')).passed
    assert checks.is_json()(ctx(output={"a": 1})).passed  # already dict
    assert not checks.is_json()(ctx(output="not json {")).passed


def test_has_keys() -> None:
    c = checks.has_keys("name", "email")
    assert c(ctx(output={"name": "x", "email": "y"})).passed
    assert c(ctx(output='{"name": "x", "email": "y"}')).passed
    miss = c(ctx(output={"name": "x"}))
    assert not miss.passed and "email" in miss.detail


def test_has_keys_non_object() -> None:
    assert not checks.has_keys("a")(ctx(output="[1,2,3]")).passed
    assert not checks.has_keys("a")(ctx(output="not json")).passed


def test_json_schema() -> None:
    schema = {
        "type": "object",
        "properties": {"age": {"type": "integer"}},
        "required": ["age"],
    }
    c = checks.json_schema(schema)
    assert c(ctx(output={"age": 30})).passed
    assert not c(ctx(output={"age": "old"})).passed
    assert not c(ctx(output="not json")).passed


# -- tools -------------------------------------------------------------------


def test_tool_allowed_denied() -> None:
    call = ToolCall(name="search")
    assert checks.tool_allowed("search", "read")(ctx(tool_call=call)).passed
    assert not checks.tool_allowed("read")(ctx(tool_call=call)).passed
    assert checks.tool_denied("delete")(ctx(tool_call=call)).passed
    assert not checks.tool_denied("search")(ctx(tool_call=call)).passed


def test_tool_checks_no_call_pass() -> None:
    # With no tool call in context, tool gate checks are vacuously true.
    assert checks.tool_allowed("x")(ctx()).passed
    assert checks.tool_denied("x")(ctx()).passed


# -- trajectory --------------------------------------------------------------


def traj(*names: str, fail: str | None = None) -> Trajectory:
    t = Trajectory()
    for n in names:
        t.record_tool(n, ok=(n != fail), error=("boom" if n == fail else None))
    return t


def test_used_and_never_used_tool() -> None:
    t = traj("search", "summarize")
    assert checks.used_tool("search")(ctx(trajectory=t)).passed
    assert not checks.used_tool("delete")(ctx(trajectory=t)).passed
    assert checks.never_used_tool("delete")(ctx(trajectory=t)).passed
    assert not checks.never_used_tool("search")(ctx(trajectory=t)).passed


def test_used_tool_no_trajectory() -> None:
    assert not checks.used_tool("x")(ctx()).passed
    assert checks.never_used_tool("x")(ctx()).passed


def test_max_tool_calls() -> None:
    t = traj("a", "a", "b")
    assert checks.max_tool_calls(3)(ctx(trajectory=t)).passed
    assert not checks.max_tool_calls(2)(ctx(trajectory=t)).passed
    assert checks.max_tool_calls(2, name="a")(ctx(trajectory=t)).passed
    assert not checks.max_tool_calls(1, name="a")(ctx(trajectory=t)).passed


def test_tool_order_subsequence() -> None:
    t = traj("auth", "search", "log", "summarize")
    assert checks.tool_order("auth", "summarize")(ctx(trajectory=t)).passed
    assert checks.tool_order("auth", "search", "summarize")(ctx(trajectory=t)).passed
    assert not checks.tool_order("summarize", "auth")(ctx(trajectory=t)).passed


def test_all_tools_succeeded() -> None:
    assert checks.all_tools_succeeded()(ctx(trajectory=traj("a", "b"))).passed
    bad = checks.all_tools_succeeded()(ctx(trajectory=traj("a", "b", fail="b")))
    assert not bad.passed and "b" in bad.detail


# -- resources ---------------------------------------------------------------


def test_within_budget() -> None:
    b = ResourceBudget(tokens=100)
    b.consume(tokens=50)
    assert checks.within_budget()(ctx(resources=b)).passed
    assert checks.within_budget()(ctx()).passed  # no budget -> vacuous pass


def test_within_budget_over() -> None:
    b = ResourceBudget(tokens=100)
    b.used["tokens"] = 150  # force over-limit without raising
    assert not checks.within_budget()(ctx(resources=b)).passed


@pytest.mark.parametrize(
    "factory",
    [checks.always_pass(), checks.excludes("x"), checks.used_tool("t")],
)
def test_checks_return_checkresult(factory: object) -> None:
    from ratify import CheckResult

    assert isinstance(factory(ctx()), CheckResult)  # type: ignore[operator]
