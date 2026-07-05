"""The :class:`Clause` — one obligation within a contract."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ratify.context import CheckContext, CheckReturn
from ratify.enums import Enforcement, Lifecycle, Scope, Severity
from ratify.exceptions import ContractDefinitionError

CheckFn = Callable[[CheckContext], CheckReturn]


@dataclass
class Clause:
    """A single, independently-checkable obligation.

    A clause is decided in exactly one of three ways (:class:`Enforcement`):

    * ``HARD`` / ``PROOF`` — supply ``check``, a deterministic predicate.
    * ``JUDGE`` — supply ``criterion``, a natural-language rule scored by a
      :class:`~ratify.judge.Judge`. ``threshold`` is the minimum satisfaction
      score to pass; ``samples`` and ``pass_rate`` implement ``(p, δ, k)``
      probabilistic satisfaction (run the judge ``samples`` times, require
      ``pass_rate`` of them to clear ``threshold``).
    """

    id: str
    description: str
    scope: Scope
    enforcement: Enforcement
    when: Lifecycle
    severity: Severity = Severity.BLOCK
    check: CheckFn | None = None
    criterion: str | None = None
    threshold: float = 0.5
    samples: int = 1
    pass_rate: float = 1.0
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.id:
            raise ContractDefinitionError("clause id must be non-empty")
        if self.enforcement is Enforcement.JUDGE:
            if self.criterion is None:
                raise ContractDefinitionError(
                    f"clause '{self.id}': JUDGE clauses require a `criterion`"
                )
            if self.check is not None:
                raise ContractDefinitionError(
                    f"clause '{self.id}': JUDGE clauses must not set `check`"
                )
        else:
            if self.check is None:
                raise ContractDefinitionError(
                    f"clause '{self.id}': {self.enforcement.value.upper()} clauses "
                    "require a `check` callable"
                )
            if self.criterion is not None:
                raise ContractDefinitionError(
                    f"clause '{self.id}': non-JUDGE clauses must not set `criterion`"
                )
        if not 0.0 <= self.threshold <= 1.0:
            raise ContractDefinitionError(f"clause '{self.id}': threshold must be in [0, 1]")
        if not 0.0 <= self.pass_rate <= 1.0:
            raise ContractDefinitionError(f"clause '{self.id}': pass_rate must be in [0, 1]")
        if self.samples < 1:
            raise ContractDefinitionError(f"clause '{self.id}': samples must be >= 1")

    @property
    def blocking(self) -> bool:
        """True if a violation of this clause fails the contract."""
        return self.severity is Severity.BLOCK

    def runs_in(self, phase: Lifecycle) -> bool:
        """Whether this clause is evaluated during ``phase``.

        ``INVARIANT`` clauses run in both ``PRE`` and ``POST`` phases.
        """
        if self.when is phase:
            return True
        return self.when is Lifecycle.INVARIANT and phase in (
            Lifecycle.PRE,
            Lifecycle.POST,
        )
