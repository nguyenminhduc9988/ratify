"""The :class:`Contract` — a named, versioned, *parameterizable* set of clauses.

A contract is a **template**: declare parameters once, then :meth:`bind`
concrete values to specialize the same definition to many scenarios. Contracts
**compose** via :meth:`include`, so a base policy can be reused across agents.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from ratify.clause import Clause
from ratify.enums import Enforcement, Lifecycle, Scope, Severity
from ratify.exceptions import BindingError, ContractDefinitionError

_MISSING = object()


@dataclass
class ParamSpec:
    """A declared parameter of a contract template."""

    name: str
    type: type = object
    default: Any = _MISSING
    description: str = ""

    @property
    def required(self) -> bool:
        return self.default is _MISSING


class Contract:
    """A collection of clauses that can be parameterized and composed.

    Build fluently::

        contract = (
            Contract("support-bot", version="1.0")
            .param("brand", type=str)
            .judge("on-brand", "Reply mentions {brand} positively.",
                   scope=Scope.BEHAVIORAL, criterion_param=True)
            .hard("no-pii", "No emails leaked.", scope=Scope.OUTPUT,
                  check=checks.excludes("@"))
        )
        bound = contract.bind(brand="Acme")
    """

    def __init__(
        self,
        name: str,
        *,
        version: str = "0.1.0",
        description: str = "",
        clauses: Iterable[Clause] | None = None,
        params: Iterable[ParamSpec] | None = None,
        bound: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.version = version
        self.description = description
        self._clauses: list[Clause] = []
        self._params: dict[str, ParamSpec] = {}
        self._bound: dict[str, Any] = dict(bound or {})
        for p in params or []:
            self._params[p.name] = p
        for c in clauses or []:
            self._append(c)

    # -- construction --------------------------------------------------------

    def _append(self, clause: Clause) -> None:
        if any(c.id == clause.id for c in self._clauses):
            raise ContractDefinitionError(
                f"contract '{self.name}': duplicate clause id '{clause.id}'"
            )
        self._clauses.append(clause)

    def param(
        self,
        name: str,
        *,
        type: type = object,  # noqa: A002 - deliberate public kwarg name
        default: Any = _MISSING,
        description: str = "",
    ) -> Contract:
        """Declare a template parameter and return ``self`` for chaining."""
        if name in self._params:
            raise ContractDefinitionError(f"contract '{self.name}': duplicate param '{name}'")
        self._params[name] = ParamSpec(name, type, default, description)
        return self

    def add(self, clause: Clause) -> Contract:
        """Append an explicit :class:`Clause` and return ``self``."""
        self._append(clause)
        return self

    def hard(
        self,
        id: str,  # noqa: A002
        description: str,
        *,
        scope: Scope,
        check: Any,
        when: Lifecycle = Lifecycle.POST,
        severity: Severity = Severity.BLOCK,
        proof: bool = False,
        tags: tuple[str, ...] = (),
    ) -> Contract:
        """Add a deterministic clause (``HARD``, or ``PROOF`` if ``proof=True``)."""
        self._append(
            Clause(
                id=id,
                description=description,
                scope=scope,
                enforcement=Enforcement.PROOF if proof else Enforcement.HARD,
                when=when,
                severity=severity,
                check=check,
                tags=tags,
            )
        )
        return self

    def judge(
        self,
        id: str,  # noqa: A002
        description: str,
        criterion: str | None = None,
        *,
        scope: Scope,
        when: Lifecycle = Lifecycle.POST,
        severity: Severity = Severity.BLOCK,
        threshold: float = 0.5,
        samples: int = 1,
        pass_rate: float = 1.0,
        tags: tuple[str, ...] = (),
    ) -> Contract:
        """Add a fuzzy LLM-judged clause and return ``self``.

        ``criterion`` is the natural-language rule handed to the judge; it
        defaults to ``description`` and may contain ``{param}`` placeholders
        filled from bound template parameters at evaluation time.
        """
        self._append(
            Clause(
                id=id,
                description=description,
                scope=scope,
                enforcement=Enforcement.JUDGE,
                when=when,
                severity=severity,
                criterion=criterion if criterion is not None else description,
                threshold=threshold,
                samples=samples,
                pass_rate=pass_rate,
                tags=tags,
            )
        )
        return self

    # -- binding & composition ----------------------------------------------

    def bind(self, **values: Any) -> Contract:
        """Return a *new* contract with template parameters bound to ``values``.

        Raises :class:`BindingError` on unknown params, missing required
        params, or type mismatches.
        """
        unknown = set(values) - set(self._params)
        if unknown:
            raise BindingError(f"contract '{self.name}': unknown param(s) {sorted(unknown)}")
        resolved: dict[str, Any] = dict(self._bound)
        for name, spec in self._params.items():
            if name in values:
                val = values[name]
            elif name in resolved:
                continue
            elif not spec.required:
                val = spec.default
            else:
                raise BindingError(f"contract '{self.name}': missing required param '{name}'")
            if spec.type is not object and not isinstance(val, spec.type):
                raise BindingError(
                    f"contract '{self.name}': param '{name}' expected "
                    f"{spec.type.__name__}, got {type(val).__name__}"
                )
            resolved[name] = val
        return Contract(
            self.name,
            version=self.version,
            description=self.description,
            clauses=self._clauses,
            params=self._params.values(),
            bound=resolved,
        )

    def include(self, other: Contract, *, prefix: str | None = None) -> Contract:
        """Return a new contract merging ``other``'s clauses and params into this one.

        Clause ids from ``other`` may be namespaced with ``prefix`` to avoid
        collisions; otherwise a collision raises :class:`ContractDefinitionError`.
        """
        merged = Contract(
            self.name,
            version=self.version,
            description=self.description,
            clauses=self._clauses,
            params=self._params.values(),
            bound=self._bound,
        )
        for name, spec in other._params.items():
            if name not in merged._params:
                merged._params[name] = spec
        for clause in other._clauses:
            if prefix:
                clause = _rename(clause, f"{prefix}{clause.id}")
            merged._append(clause)
        return merged

    def __add__(self, other: Contract) -> Contract:
        return self.include(other)

    # -- introspection -------------------------------------------------------

    @property
    def clauses(self) -> tuple[Clause, ...]:
        return tuple(self._clauses)

    @property
    def params(self) -> tuple[ParamSpec, ...]:
        return tuple(self._params.values())

    def bound_params(self) -> dict[str, Any]:
        """The parameter values bound so far."""
        return dict(self._bound)

    def clauses_for(self, phase: Lifecycle) -> tuple[Clause, ...]:
        """Clauses that run in ``phase``."""
        return tuple(c for c in self._clauses if c.runs_in(phase))

    def __iter__(self) -> Iterator[Clause]:
        return iter(self._clauses)

    def __len__(self) -> int:
        return len(self._clauses)

    def __repr__(self) -> str:
        return (
            f"Contract({self.name!r}, version={self.version!r}, "
            f"clauses={len(self._clauses)}, params={list(self._params)})"
        )


def _rename(clause: Clause, new_id: str) -> Clause:
    return Clause(
        id=new_id,
        description=clause.description,
        scope=clause.scope,
        enforcement=clause.enforcement,
        when=clause.when,
        severity=clause.severity,
        check=clause.check,
        criterion=clause.criterion,
        threshold=clause.threshold,
        samples=clause.samples,
        pass_rate=clause.pass_rate,
        tags=clause.tags,
    )
