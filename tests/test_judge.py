"""Tests for the judge abstraction."""

from __future__ import annotations

import pytest

from ratify import CallableJudge, CheckContext, Judge, JudgeVerdict, KeywordJudge


def test_verdict_score_bounds() -> None:
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        JudgeVerdict(1.5)
    with pytest.raises(ValueError):
        JudgeVerdict(-0.1)


def test_keyword_judge_required() -> None:
    j = KeywordJudge(required=["sources", "citation"])
    assert j.evaluate("x", CheckContext(output="sources and citation")).score == 1.0
    assert j.evaluate("x", CheckContext(output="sources only")).score == 0.5
    assert j.evaluate("x", CheckContext(output="nothing")).score == 0.0


def test_keyword_judge_forbidden() -> None:
    j = KeywordJudge(forbidden=["password"])
    v = j.evaluate("x", CheckContext(output="here is your password"))
    assert v.score == 0.0 and "forbidden" in v.rationale


def test_keyword_judge_no_required_passes() -> None:
    j = KeywordJudge()
    assert j.evaluate("x", CheckContext(output="anything")).score == 1.0


def test_keyword_judge_uses_input_when_no_output() -> None:
    j = KeywordJudge(required=["hi"])
    assert j.evaluate("x", CheckContext(input="hi there")).score == 1.0


def test_keyword_judge_case_sensitive() -> None:
    j = KeywordJudge(required=["Acme"], case_sensitive=True)
    assert j.evaluate("x", CheckContext(output="acme")).score == 0.0
    assert j.evaluate("x", CheckContext(output="Acme")).score == 1.0


def test_callable_judge_from_float() -> None:
    j = CallableJudge(lambda criterion, ctx: 0.7)
    assert j.evaluate("x", CheckContext()).score == 0.7


def test_callable_judge_from_verdict() -> None:
    j = CallableJudge(lambda criterion, ctx: JudgeVerdict(0.9, "good"))
    v = j.evaluate("x", CheckContext())
    assert v.score == 0.9 and v.rationale == "good"


def test_judge_protocol_runtime_checkable() -> None:
    assert isinstance(KeywordJudge(), Judge)
    assert isinstance(CallableJudge(lambda c, x: 1.0), Judge)
    assert not isinstance(object(), Judge)
