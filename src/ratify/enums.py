"""Enumerations that classify contract clauses.

The three axes that make Ratify a *unified* contract layer:

* :class:`Scope` — *what* aspect of the agent a clause governs.
* :class:`Enforcement` — *how* a clause is checked (deterministic code,
  an LLM judge, or a strict proof gate).
* :class:`Lifecycle` — *when* a clause is evaluated during a run.
"""

from __future__ import annotations

from enum import Enum


class Scope(str, Enum):
    """The dimension of agent behavior a clause constrains."""

    INPUT = "input"
    """A precondition on what the agent is asked to do."""
    OUTPUT = "output"
    """A postcondition on the agent's final result."""
    BEHAVIORAL = "behavioral"
    """An invariant on how the agent conducts itself (tone, refusals, ...)."""
    TOOL = "tool"
    """A constraint on tool / function invocations."""
    RESOURCE = "resource"
    """A budget on tokens, cost, latency, or tool-call count."""
    POLICY = "policy"
    """An organizational or regulatory rule."""
    TRAJECTORY = "trajectory"
    """A constraint on the *path* the agent took (a "pathcondition")."""


class Enforcement(str, Enum):
    """How a clause is decided."""

    HARD = "hard"
    """Deterministic Python predicate — regex, schema, budget, allow-list."""
    JUDGE = "judge"
    """Fuzzy LLM-as-judge evaluation of a natural-language criterion."""
    PROOF = "proof"
    """A strict gate that must be provably true; failure always blocks."""


class Severity(str, Enum):
    """What happens when a clause is violated."""

    BLOCK = "block"
    """Violation fails the contract (and raises under ``guard``)."""
    WARN = "warn"
    """Violation is recorded but does not fail the contract."""


class Lifecycle(str, Enum):
    """When a clause is evaluated relative to the agent run."""

    PRE = "pre"
    """Before the agent runs, against its input."""
    POST = "post"
    """After the agent runs, against its output."""
    INVARIANT = "invariant"
    """Any time — evaluated in both pre and post phases."""
    ON_TOOL = "on_tool"
    """Each time the agent invokes a tool."""
    ON_STEP = "on_step"
    """Each reasoning/execution step recorded in the trace."""
