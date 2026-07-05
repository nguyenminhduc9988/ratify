"""Tests for ResourceBudget and delegation conservation."""

from __future__ import annotations

import pytest

from ratify import BudgetExceeded, ResourceBudget


def test_consume_within_limits() -> None:
    b = ResourceBudget(tokens=100, cost_usd=1.0)
    b.consume(tokens=30, cost_usd=0.2)
    assert b.remaining("tokens") == 70
    assert b.remaining("cost_usd") == pytest.approx(0.8)
    assert b.within_limits()


def test_consume_exceeds_raises() -> None:
    b = ResourceBudget(tokens=50)
    with pytest.raises(BudgetExceeded, match="tokens budget exceeded"):
        b.consume(tokens=51)


def test_consume_is_atomic() -> None:
    # cost is fine but tokens overflow -> nothing should be recorded
    b = ResourceBudget(tokens=10, cost_usd=100)
    with pytest.raises(BudgetExceeded):
        b.consume(tokens=20, cost_usd=1)
    assert b.snapshot()["tokens"] == 0
    assert b.snapshot()["cost_usd"] == 0


def test_unbounded_metric_returns_none() -> None:
    b = ResourceBudget(tokens=100)
    assert b.remaining("cost_usd") is None
    b.consume(cost_usd=9999)  # unbounded, allowed
    assert b.within_limits()


def test_remaining_unknown_metric() -> None:
    b = ResourceBudget()
    with pytest.raises(ValueError, match="unknown metric"):
        b.remaining("bananas")


def test_negative_limit_rejected() -> None:
    with pytest.raises(BudgetExceeded, match="cannot be negative"):
        ResourceBudget(tokens=-1)


def test_child_fits_within_remaining() -> None:
    root = ResourceBudget(tokens=100, cost_usd=5.0, label="root")
    child = root.child(label="worker", tokens=40)
    assert child.remaining("tokens") == 40
    assert child.label == "worker"


def test_child_exceeds_parent_rejected() -> None:
    root = ResourceBudget(tokens=100)
    with pytest.raises(BudgetExceeded, match="exceeds parent remaining"):
        root.child(label="rogue", tokens=200)


def test_child_conservation_accounts_for_parent_usage() -> None:
    root = ResourceBudget(tokens=100)
    root.consume(tokens=80)  # only 20 left
    with pytest.raises(BudgetExceeded):
        root.child(label="late", tokens=30)
    ok = root.child(label="ok", tokens=20)
    assert ok.remaining("tokens") == 20


def test_child_unknown_metric() -> None:
    root = ResourceBudget(tokens=100)
    with pytest.raises(ValueError, match="unknown metric"):
        root.child(label="x", nonsense=5)


def test_child_unbounded_parent_allows_any() -> None:
    root = ResourceBudget()  # unbounded
    child = root.child(label="c", tokens=10_000)
    assert child.remaining("tokens") == 10_000


def test_child_consumption_propagates_to_parent() -> None:
    root = ResourceBudget(tokens=100, label="root")
    child = root.child(label="c", tokens=80)
    child.consume(tokens=50)
    assert child.remaining("tokens") == 30
    assert root.remaining("tokens") == 50  # propagated up


def test_propagation_blocks_when_ancestor_would_exceed() -> None:
    root = ResourceBudget(tokens=100)
    a = root.child(label="a", tokens=80)
    b = root.child(label="b", tokens=80)  # over-subscription allowed at creation
    a.consume(tokens=70)  # root now at 70
    with pytest.raises(BudgetExceeded, match="root: tokens budget exceeded"):
        b.consume(tokens=40)  # would push root to 110
    assert b.remaining("tokens") == 80  # atomic: nothing consumed on failure


def test_creation_check_accounts_for_propagated_usage() -> None:
    root = ResourceBudget(tokens=100)
    a = root.child(label="a", tokens=60)
    a.consume(tokens=60)  # propagates: root used 60
    with pytest.raises(BudgetExceeded, match="exceeds parent remaining"):
        root.child(label="late", tokens=50)  # only 40 remaining


def test_three_level_propagation() -> None:
    root = ResourceBudget(tokens=100)
    mid = root.child(label="mid", tokens=80)
    leaf = mid.child(label="leaf", tokens=50)
    leaf.consume(tokens=40)
    assert leaf.remaining("tokens") == 10
    assert mid.remaining("tokens") == 40
    assert root.remaining("tokens") == 60


def test_repr_shows_usage() -> None:
    b = ResourceBudget(tokens=100, label="root")
    b.consume(tokens=25)
    assert "tokens=25/100" in repr(b)
    assert "root" in repr(b)
