"""Execution traces — the substrate for trajectory / tool clauses.

A :class:`Trajectory` records the ordered steps an agent took so that
*pathconditions* (constraints on the process, not just the result) can be
checked. This mirrors the "pathcondition" concept from relari's
``agent-contracts`` and the symbolic tool state of ToolGate.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """A single tool / function invocation."""

    name: str
    args: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    ok: bool = True
    error: str | None = None


@dataclass
class Step:
    """One step in an agent's execution."""

    kind: str
    """Free-form step type, e.g. ``"think"``, ``"tool"``, ``"message"``."""
    content: Any = None
    tool_call: ToolCall | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Trajectory:
    """An ordered sequence of :class:`Step` objects with convenience queries."""

    steps: list[Step] = field(default_factory=list)

    # -- builders ------------------------------------------------------------

    def add(self, step: Step) -> Step:
        """Append a step and return it."""
        self.steps.append(step)
        return step

    def record_tool(
        self,
        name: str,
        *,
        args: dict[str, Any] | None = None,
        result: Any = None,
        ok: bool = True,
        error: str | None = None,
    ) -> ToolCall:
        """Convenience: append a tool step and return the :class:`ToolCall`."""
        call = ToolCall(name=name, args=args or {}, result=result, ok=ok, error=error)
        self.add(Step(kind="tool", tool_call=call))
        return call

    # -- queries -------------------------------------------------------------

    @property
    def tool_calls(self) -> list[ToolCall]:
        """Every tool call in order."""
        return [s.tool_call for s in self.steps if s.tool_call is not None]

    @property
    def tool_names(self) -> list[str]:
        """The ordered names of tools that were called."""
        return [c.name for c in self.tool_calls]

    def used_tool(self, name: str) -> bool:
        """Whether ``name`` was ever called."""
        return name in self.tool_names

    def count_tool(self, name: str) -> int:
        """How many times ``name`` was called."""
        return self.tool_names.count(name)

    def __iter__(self) -> Iterator[Step]:
        return iter(self.steps)

    def __len__(self) -> int:
        return len(self.steps)
