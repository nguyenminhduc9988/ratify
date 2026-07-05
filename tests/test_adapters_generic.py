"""Tests for the framework-agnostic adapter."""

from __future__ import annotations

import pytest

from ratify import Contract, ContractViolation, Lifecycle, Scope, Trajectory, checks
from ratify.adapters import RatifiedAgent, wrap


def contract() -> Contract:
    return Contract("c").hard(
        "no-at", "no @", scope=Scope.OUTPUT, check=checks.excludes("@"), when=Lifecycle.POST
    )


def test_wrap_enforces() -> None:
    agent = wrap(lambda q: "leak a@b.com", contract())
    with pytest.raises(ContractViolation):
        agent("hi")


def test_wrap_passes_and_records_report() -> None:
    agent = wrap(lambda q: "clean", contract())
    assert agent("hi") == "clean"
    assert agent.last_report is not None
    assert agent.last_report.passed


def test_wrap_monitor_mode() -> None:
    agent = RatifiedAgent(lambda q: "a@b.com", contract(), mode="monitor")
    out = agent("hi")
    assert out == "a@b.com"
    assert agent.last_report is not None and not agent.last_report.passed


def test_wrap_trajectory_from() -> None:
    c = Contract("c").hard("kb", "use kb", scope=Scope.TRAJECTORY, check=checks.used_tool("search"))

    def run(q: str) -> dict[str, object]:
        return {"answer": "done", "tools": ["search"]}

    def traj_from(output: dict[str, object]) -> Trajectory:
        t = Trajectory()
        for name in output["tools"]:  # type: ignore[union-attr]
            t.record_tool(str(name))
        return t

    agent = wrap(run, c, trajectory_from=traj_from)
    result = agent("q")
    assert result["answer"] == "done"
    assert agent.last_report is not None and agent.last_report.passed


def test_wrap_forwards_extra_args() -> None:
    agent = wrap(lambda q, suffix="": f"clean{suffix}", contract())
    assert agent("hi", suffix="!") == "clean!"
