"""Shared fixtures for the Ratify test suite."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from ratify import CallableJudge, CheckContext, Judge, JudgeVerdict


@pytest.fixture
def always_judge() -> Judge:
    """A judge that always fully satisfies."""
    return CallableJudge(lambda criterion, ctx: JudgeVerdict(1.0, "always ok"))


@pytest.fixture
def never_judge() -> Judge:
    """A judge that never satisfies."""
    return CallableJudge(lambda criterion, ctx: JudgeVerdict(0.0, "always fails"))


@pytest.fixture
def scripted_judge() -> Callable[[list[float]], Judge]:
    """Factory returning a judge that yields the given scores cyclically."""

    def make(scores: list[float]) -> Judge:
        state = {"i": 0}

        def fn(criterion: str, ctx: CheckContext) -> JudgeVerdict:
            score = scores[state["i"] % len(scores)]
            state["i"] += 1
            return JudgeVerdict(score, f"scripted {score}")

        return CallableJudge(fn)

    return make
