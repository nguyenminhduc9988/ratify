"""Tests for the evaluation engine."""

from __future__ import annotations

from collections.abc import Callable

from ratify import (
    Contract,
    Judge,
    Lifecycle,
    Scope,
    Severity,
    Trajectory,
    checks,
    evaluate,
)


def test_hard_pass_and_fail() -> None:
    c = Contract("c").hard("no-at", "no @", scope=Scope.OUTPUT, check=checks.excludes("@"))
    assert evaluate(c, output="clean").passed
    r = evaluate(c, output="a@b.com")
    assert not r.passed
    assert r.violations[0].clause_id == "no-at"


def test_phase_filtering() -> None:
    c = (
        Contract("c")
        .hard("pre", "d", scope=Scope.INPUT, check=checks.always_fail(), when=Lifecycle.PRE)
        .hard("post", "d", scope=Scope.OUTPUT, check=checks.always_pass(), when=Lifecycle.POST)
    )
    # Only POST clause evaluated -> passes despite failing PRE clause
    assert evaluate(c, phase=Lifecycle.POST).passed
    assert not evaluate(c, phase=Lifecycle.PRE).passed
    # No phase -> both evaluated
    assert not evaluate(c).passed


def test_warn_does_not_block() -> None:
    c = Contract("c").hard(
        "soft", "d", scope=Scope.OUTPUT, check=checks.always_fail(), severity=Severity.WARN
    )
    r = evaluate(c, output="x")
    assert r.passed  # warnings don't fail
    assert len(r.warnings) == 1
    assert not r.violations


def test_judge_pass_and_fail(always_judge: Judge, never_judge: Judge) -> None:
    c = Contract("c").judge("j", "be good", scope=Scope.BEHAVIORAL, threshold=0.5)
    assert evaluate(c, output="x", judge=always_judge).passed
    assert not evaluate(c, output="x", judge=never_judge).passed


def test_judge_missing_fails_closed() -> None:
    c = Contract("c").judge("j", "be good", scope=Scope.BEHAVIORAL)
    r = evaluate(c, output="x")  # no judge supplied
    assert not r.passed
    assert r.violations[0].error == "missing_judge"


def test_probabilistic_satisfaction(scripted_judge: Callable[[list[float]], Judge]) -> None:
    # threshold 0.5, need 3/5 samples to pass. Scores: 3 pass, 2 fail.
    c = Contract("c").judge(
        "j",
        "grounded",
        scope=Scope.OUTPUT,
        threshold=0.5,
        samples=5,
        pass_rate=0.6,
    )
    j = scripted_judge([0.9, 0.9, 0.9, 0.1, 0.1])  # 3/5 = 0.6 >= 0.6
    assert evaluate(c, output="x", judge=j).passed

    j2 = scripted_judge([0.9, 0.9, 0.1, 0.1, 0.1])  # 2/5 = 0.4 < 0.6
    assert not evaluate(c, output="x", judge=j2).passed


def test_criterion_template_filled() -> None:
    seen: list[str] = []

    class Recorder:
        def evaluate(self, criterion: str, ctx: object):  # type: ignore[no-untyped-def]
            from ratify import JudgeVerdict

            seen.append(criterion)
            return JudgeVerdict(1.0)

    c = (
        Contract("c")
        .param("brand", type=str)
        .judge("j", "mentions {brand}", scope=Scope.BEHAVIORAL)
    )
    evaluate(c.bind(brand="Acme"), output="x", judge=Recorder())
    assert seen == ["mentions Acme"]


def test_check_exception_fails_closed() -> None:
    def boom(ctx: object):  # type: ignore[no-untyped-def]
        raise RuntimeError("kaboom")

    c = Contract("c").hard("x", "d", scope=Scope.OUTPUT, check=boom)
    r = evaluate(c, output="x")
    assert not r.passed
    assert r.violations[0].error == "RuntimeError"
    assert "kaboom" in r.violations[0].detail


def test_report_to_dict_is_serializable() -> None:
    import json

    c = Contract("c").hard("x", "d", scope=Scope.OUTPUT, check=checks.always_pass())
    d = evaluate(c, output="x").to_dict()
    assert d["passed"] is True
    assert d["results"][0]["scope"] == "output"
    json.dumps(d)  # must not raise


def test_report_bool_and_summary() -> None:
    c = Contract("c").hard("x", "d", scope=Scope.OUTPUT, check=checks.always_fail())
    r = evaluate(c, output="x")
    assert not bool(r)
    assert "FAIL" in r.summary()


def test_trajectory_clause_via_engine() -> None:
    c = Contract("c").hard("kb", "use kb", scope=Scope.TRAJECTORY, check=checks.used_tool("search"))
    t = Trajectory()
    t.record_tool("search")
    assert evaluate(c, trajectory=t).passed
    assert not evaluate(c, trajectory=Trajectory()).passed
