"""Tests for runtime enforcement: Guard, guard decorator, guarded context."""

from __future__ import annotations

import pytest

from ratify import (
    Contract,
    ContractViolation,
    Guard,
    Lifecycle,
    Scope,
    ToolCall,
    checks,
    guard,
    guarded,
)


def out_contract() -> Contract:
    return Contract("c").hard(
        "no-at", "no @", scope=Scope.OUTPUT, check=checks.excludes("@"), when=Lifecycle.POST
    )


def in_contract() -> Contract:
    return Contract("c").hard(
        "short-in",
        "short input",
        scope=Scope.INPUT,
        check=checks.max_length(10, field="input"),
        when=Lifecycle.PRE,
    )


# -- Guard object ------------------------------------------------------------


def test_guard_postcheck_raises_on_violation() -> None:
    g = Guard(out_contract())
    with pytest.raises(ContractViolation) as exc:
        g.postcheck("q", "leak a@b.com")
    assert "no-at" in str(exc.value)
    assert exc.value.report.violations[0].clause_id == "no-at"


def test_guard_monitor_mode_records_no_raise() -> None:
    g = Guard(out_contract(), mode="monitor")
    report = g.postcheck("q", "leak a@b.com")
    assert not report.passed
    assert len(g.reports) == 1  # recorded


def test_guard_on_violation_callback() -> None:
    seen = []
    g = Guard(out_contract(), mode="monitor", on_violation=seen.append)
    g.postcheck("q", "a@b.com")
    assert len(seen) == 1


def test_guard_precheck() -> None:
    g = Guard(in_contract())
    g.precheck("short")  # ok
    with pytest.raises(ContractViolation):
        g.precheck("this input is way too long")


def test_guard_tool_check() -> None:
    c = Contract("c").hard(
        "allow",
        "only search",
        scope=Scope.TOOL,
        check=checks.tool_allowed("search"),
        when=Lifecycle.ON_TOOL,
    )
    g = Guard(c)
    g.tool_check(ToolCall(name="search"))  # ok
    with pytest.raises(ContractViolation):
        g.tool_check(ToolCall(name="delete"))


# -- decorator ---------------------------------------------------------------


def test_guard_decorator_enforces() -> None:
    @guard(out_contract())
    def agent(q: str) -> str:
        return "reply with a@b.com"

    with pytest.raises(ContractViolation):
        agent("hi")


def test_guard_decorator_passes_through() -> None:
    @guard(out_contract())
    def agent(q: str) -> str:
        return "clean reply"

    assert agent("hi") == "clean reply"


def test_guard_decorator_input_from_kwarg() -> None:
    @guard(in_contract(), input_from="prompt")
    def agent(*, prompt: str) -> str:
        return "ok"

    agent(prompt="short")
    with pytest.raises(ContractViolation):
        agent(prompt="this is way too long to pass")


def test_guard_decorator_attaches_contract() -> None:
    c = out_contract()

    @guard(c)
    def agent(q: str) -> str:
        return "x"

    assert agent.__ratify_contract__ is c


def test_input_from_missing_key() -> None:
    @guard(in_contract(), input_from="prompt")
    def agent(**kw: str) -> str:
        return "ok"

    with pytest.raises(KeyError):
        agent(other="x")


# -- context manager ---------------------------------------------------------


def test_guarded_context_pass() -> None:
    with guarded(out_contract(), "question") as box:
        box.record("a clean answer")
    assert box.value == "a clean answer"


def test_guarded_context_raises_on_bad_output() -> None:
    with pytest.raises(ContractViolation), guarded(out_contract(), "question") as box:
        box.record("contains a@b.com")


def test_guarded_context_precheck_raises_before_body() -> None:
    entered = False
    with pytest.raises(ContractViolation), guarded(in_contract(), "this input is too long"):
        entered = True  # pragma: no cover - should not run
    assert not entered
