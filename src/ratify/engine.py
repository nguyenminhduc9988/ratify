"""The evaluation engine — turns a contract + a run into a :class:`Report`.

This is where the two enforcement halves meet: ``HARD``/``PROOF`` clauses run
their deterministic ``check``; ``JUDGE`` clauses are routed to a
:class:`~ratify.judge.Judge` with probabilistic ``(p, δ, k)`` satisfaction.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ratify.clause import Clause
from ratify.context import CheckContext, CheckResult
from ratify.contract import Contract
from ratify.enums import Enforcement, Lifecycle, Scope, Severity
from ratify.judge import Judge
from ratify.trace import ToolCall, Trajectory


@dataclass
class ClauseResult:
    """The outcome of evaluating one clause."""

    clause_id: str
    scope: Scope
    enforcement: Enforcement
    phase: Lifecycle
    passed: bool
    blocking: bool
    severity: Severity
    score: float
    detail: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for key in ("scope", "enforcement", "phase", "severity"):
            d[key] = d[key].value if hasattr(d[key], "value") else d[key]
        return d


@dataclass
class Report:
    """The aggregate result of evaluating a contract."""

    contract: str
    version: str
    results: list[ClauseResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True unless a *blocking* clause failed."""
        return all(r.passed for r in self.results if r.blocking)

    @property
    def violations(self) -> list[ClauseResult]:
        """Failed blocking clauses."""
        return [r for r in self.results if r.blocking and not r.passed]

    @property
    def warnings(self) -> list[ClauseResult]:
        """Failed non-blocking (warn) clauses."""
        return [r for r in self.results if not r.blocking and not r.passed]

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{status}] {self.contract} v{self.version}: "
            f"{len(self.results)} clause(s), "
            f"{len(self.violations)} violation(s), {len(self.warnings)} warning(s)"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract,
            "version": self.version,
            "passed": self.passed,
            "results": [r.to_dict() for r in self.results],
        }

    def __bool__(self) -> bool:
        return self.passed


class _SafeDict(dict):  # type: ignore[type-arg]
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _fill(template: str, params: dict[str, Any]) -> str:
    try:
        return template.format_map(_SafeDict(params))
    except (ValueError, IndexError):
        return template


def _judge_clause(clause: Clause, ctx: CheckContext, judge: Judge | None) -> ClauseResult:
    assert clause.criterion is not None
    criterion = _fill(clause.criterion, dict(ctx.params))
    if judge is None:
        return _result(
            clause,
            passed=False,
            score=0.0,
            detail="no judge configured for JUDGE clause",
            error="missing_judge",
        )
    passes = 0
    scores: list[float] = []
    last_rationale = ""
    for _ in range(clause.samples):
        verdict = judge.evaluate(criterion, ctx)
        scores.append(verdict.score)
        last_rationale = verdict.rationale
        if verdict.score >= clause.threshold:
            passes += 1
    rate = passes / clause.samples
    mean_score = sum(scores) / len(scores)
    passed = rate >= clause.pass_rate
    detail = (
        f"{passes}/{clause.samples} samples >= threshold {clause.threshold} "
        f"(need {clause.pass_rate:.0%}); {last_rationale}".strip()
    )
    return _result(clause, passed=passed, score=mean_score, detail=detail)


def _deterministic_clause(clause: Clause, ctx: CheckContext) -> ClauseResult:
    assert clause.check is not None
    try:
        raw = clause.check(ctx)
        result = CheckResult.coerce(raw)
    except Exception as exc:  # noqa: BLE001 - fail closed, report the error
        return _result(
            clause,
            passed=False,
            score=0.0,
            detail=f"check raised: {exc}",
            error=type(exc).__name__,
        )
    return _result(clause, passed=result.passed, score=result.score, detail=result.detail)


def _result(
    clause: Clause,
    *,
    passed: bool,
    score: float,
    detail: str,
    error: str | None = None,
) -> ClauseResult:
    return ClauseResult(
        clause_id=clause.id,
        scope=clause.scope,
        enforcement=clause.enforcement,
        phase=clause.when,
        passed=passed,
        blocking=clause.blocking,
        severity=clause.severity,
        score=score,
        detail=detail,
        error=error,
    )


def evaluate(
    contract: Contract,
    *,
    input: Any = None,  # noqa: A002
    output: Any = None,
    trajectory: Trajectory | None = None,
    resources: Any = None,
    tool_call: ToolCall | None = None,
    phase: Lifecycle | None = None,
    judge: Judge | None = None,
    metadata: dict[str, Any] | None = None,
) -> Report:
    """Evaluate ``contract`` against a run and return a :class:`Report`.

    If ``phase`` is given, only clauses that run in that phase are evaluated;
    otherwise every clause is evaluated once.
    """
    ctx = CheckContext(
        input=input,
        output=output,
        trajectory=trajectory,
        resources=resources,
        tool_call=tool_call,
        params=contract.bound_params(),
        metadata=metadata or {},
    )
    results: list[ClauseResult] = []
    for clause in contract.clauses:
        if phase is not None and not clause.runs_in(phase):
            continue
        if clause.enforcement is Enforcement.JUDGE:
            results.append(_judge_clause(clause, ctx, judge))
        else:
            results.append(_deterministic_clause(clause, ctx))
    return Report(contract=contract.name, version=contract.version, results=results)
