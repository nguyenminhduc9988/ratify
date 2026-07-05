"""Tests for Clause construction and validation."""

from __future__ import annotations

import pytest

from ratify import Clause, Enforcement, Lifecycle, Scope, Severity
from ratify.checks import always_pass
from ratify.exceptions import ContractDefinitionError


def test_hard_clause_requires_check() -> None:
    with pytest.raises(ContractDefinitionError, match="require a `check`"):
        Clause("c", "d", Scope.OUTPUT, Enforcement.HARD, Lifecycle.POST)


def test_judge_clause_requires_criterion() -> None:
    with pytest.raises(ContractDefinitionError, match="require a `criterion`"):
        Clause("c", "d", Scope.OUTPUT, Enforcement.JUDGE, Lifecycle.POST)


def test_judge_clause_rejects_check() -> None:
    with pytest.raises(ContractDefinitionError, match="must not set `check`"):
        Clause(
            "c",
            "d",
            Scope.OUTPUT,
            Enforcement.JUDGE,
            Lifecycle.POST,
            check=always_pass(),
            criterion="x",
        )


def test_hard_clause_rejects_criterion() -> None:
    with pytest.raises(ContractDefinitionError, match="must not set `criterion`"):
        Clause(
            "c",
            "d",
            Scope.OUTPUT,
            Enforcement.HARD,
            Lifecycle.POST,
            check=always_pass(),
            criterion="x",
        )


def test_empty_id_rejected() -> None:
    with pytest.raises(ContractDefinitionError, match="non-empty"):
        Clause("", "d", Scope.OUTPUT, Enforcement.HARD, Lifecycle.POST, check=always_pass())


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_threshold_bounds(bad: float) -> None:
    with pytest.raises(ContractDefinitionError, match="threshold"):
        Clause(
            "c",
            "d",
            Scope.OUTPUT,
            Enforcement.JUDGE,
            Lifecycle.POST,
            criterion="x",
            threshold=bad,
        )


def test_pass_rate_bounds() -> None:
    with pytest.raises(ContractDefinitionError, match="pass_rate"):
        Clause(
            "c",
            "d",
            Scope.OUTPUT,
            Enforcement.JUDGE,
            Lifecycle.POST,
            criterion="x",
            pass_rate=2.0,
        )


def test_samples_must_be_positive() -> None:
    with pytest.raises(ContractDefinitionError, match="samples"):
        Clause(
            "c",
            "d",
            Scope.OUTPUT,
            Enforcement.JUDGE,
            Lifecycle.POST,
            criterion="x",
            samples=0,
        )


def test_blocking_property() -> None:
    c = Clause("c", "d", Scope.OUTPUT, Enforcement.HARD, Lifecycle.POST, check=always_pass())
    assert c.blocking
    w = Clause(
        "c",
        "d",
        Scope.OUTPUT,
        Enforcement.HARD,
        Lifecycle.POST,
        check=always_pass(),
        severity=Severity.WARN,
    )
    assert not w.blocking


def test_invariant_runs_in_pre_and_post() -> None:
    c = Clause(
        "c",
        "d",
        Scope.BEHAVIORAL,
        Enforcement.HARD,
        Lifecycle.INVARIANT,
        check=always_pass(),
    )
    assert c.runs_in(Lifecycle.PRE)
    assert c.runs_in(Lifecycle.POST)
    assert not c.runs_in(Lifecycle.ON_TOOL)


def test_runs_in_exact_phase() -> None:
    c = Clause("c", "d", Scope.TOOL, Enforcement.HARD, Lifecycle.ON_TOOL, check=always_pass())
    assert c.runs_in(Lifecycle.ON_TOOL)
    assert not c.runs_in(Lifecycle.POST)
