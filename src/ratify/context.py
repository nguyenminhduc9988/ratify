"""The context passed to every clause check, and the result it returns."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ratify.resources import ResourceBudget
from ratify.trace import ToolCall, Trajectory


@dataclass
class CheckContext:
    """Everything a clause check may inspect about a run.

    Which fields are populated depends on the lifecycle phase: ``PRE`` checks
    see ``input``; ``POST`` checks see ``input`` and ``output``; ``ON_TOOL``
    checks see the current ``tool_call``. ``params`` carries the bound values
    of a contract template.
    """

    input: Any = None
    output: Any = None
    trajectory: Trajectory | None = None
    resources: ResourceBudget | None = None
    tool_call: ToolCall | None = None
    params: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class CheckResult:
    """The outcome of evaluating a single clause check.

    ``score`` is a confidence in ``[0, 1]`` used by fuzzy (judge) clauses and
    probabilistic satisfaction; deterministic checks use ``1.0`` for pass and
    ``0.0`` for fail.
    """

    passed: bool
    detail: str = ""
    score: float = 1.0

    @classmethod
    def coerce(cls, value: CheckReturn) -> CheckResult:
        """Normalize a check's return value into a :class:`CheckResult`."""
        if isinstance(value, CheckResult):
            return value
        if isinstance(value, bool):
            return cls(passed=value, score=1.0 if value else 0.0)
        raise TypeError(f"clause check must return bool or CheckResult, got {type(value).__name__}")


# A check may return a bare bool for convenience or a full CheckResult.
CheckReturn = bool | CheckResult
