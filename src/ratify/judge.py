"""LLM-as-judge abstraction — the *fuzzy* half of the enforcement layer.

Ratify never talks to an LLM directly. A :class:`Judge` is any object with an
``evaluate`` method; the engine routes ``JUDGE`` clauses to it. This keeps the
core hermetic and testable, and lets you plug in OpenAI, Anthropic, a local
model, or a deterministic stub. See :class:`CallableJudge` and
:class:`KeywordJudge` for ready-made options, and ``docs/INTEGRATION.md`` for
provider adapters.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ratify.context import CheckContext


@dataclass
class JudgeVerdict:
    """A judge's assessment of one natural-language criterion.

    ``score`` is a satisfaction probability in ``[0, 1]``; ``rationale``
    explains the decision for audit trails.
    """

    score: float
    rationale: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"judge score must be in [0, 1], got {self.score}")


@runtime_checkable
class Judge(Protocol):
    """Anything that can score a criterion against a context."""

    def evaluate(self, criterion: str, ctx: CheckContext) -> JudgeVerdict:  # noqa: D102
        ...


class CallableJudge:
    """Adapt a plain function ``(criterion, ctx) -> JudgeVerdict | float`` to a Judge."""

    def __init__(self, fn: Callable[[str, CheckContext], JudgeVerdict | float]) -> None:
        self._fn = fn

    def evaluate(self, criterion: str, ctx: CheckContext) -> JudgeVerdict:
        out = self._fn(criterion, ctx)
        if isinstance(out, JudgeVerdict):
            return out
        return JudgeVerdict(score=float(out))


class KeywordJudge:
    """A deterministic, dependency-free judge for tests and offline use.

    Scores 1.0 if the stringified output contains all ``required`` phrases and
    none of the ``forbidden`` phrases, else a partial score. Not a substitute
    for a real model — a fixture that makes fuzzy clauses exercisable in CI.
    """

    def __init__(
        self,
        required: list[str] | None = None,
        forbidden: list[str] | None = None,
        *,
        case_sensitive: bool = False,
    ) -> None:
        self.required = required or []
        self.forbidden = forbidden or []
        self.case_sensitive = case_sensitive

    def evaluate(self, criterion: str, ctx: CheckContext) -> JudgeVerdict:
        text = str(ctx.output if ctx.output is not None else ctx.input)
        hay = text if self.case_sensitive else text.lower()

        def present(phrase: str) -> bool:
            needle = phrase if self.case_sensitive else phrase.lower()
            return needle in hay

        forbidden_hits = [p for p in self.forbidden if present(p)]
        if forbidden_hits:
            return JudgeVerdict(
                score=0.0,
                rationale=f"contains forbidden phrase(s): {forbidden_hits}",
            )
        if not self.required:
            return JudgeVerdict(score=1.0, rationale="no required phrases; passes")
        hits = sum(1 for p in self.required if present(p))
        score = hits / len(self.required)
        return JudgeVerdict(
            score=score,
            rationale=f"matched {hits}/{len(self.required)} required phrases",
        )
