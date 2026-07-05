"""Runtime enforcement — wrap an agent call so its contract is checked live.

Three ergonomic entry points, all built on :func:`ratify.engine.evaluate`:

* :class:`Guard` — explicit control (``precheck`` / ``postcheck`` / ``tool_check``).
* :func:`guard` — a decorator for a function-style agent.
* :func:`guarded` — a context manager for imperative agent loops.

In ``"enforce"`` mode a blocking violation raises
:class:`~ratify.exceptions.ContractViolation`; in ``"monitor"`` mode reports
are collected but nothing is raised.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Literal

from ratify.contract import Contract
from ratify.engine import Report, evaluate
from ratify.enums import Lifecycle
from ratify.exceptions import ContractViolation
from ratify.judge import Judge
from ratify.trace import ToolCall, Trajectory

Mode = Literal["enforce", "monitor"]


class Guard:
    """Stateful contract enforcer for a single agent invocation.

    Collects every :class:`Report` it produces in :attr:`reports`, so a
    ``"monitor"``-mode guard doubles as an audit log.
    """

    def __init__(
        self,
        contract: Contract,
        *,
        judge: Judge | None = None,
        resources: Any = None,
        mode: Mode = "enforce",
        on_violation: Callable[[Report], None] | None = None,
    ) -> None:
        self.contract = contract
        self.judge = judge
        self.resources = resources
        self.mode = mode
        self.on_violation = on_violation
        self.reports: list[Report] = []

    def _handle(self, report: Report) -> Report:
        self.reports.append(report)
        if not report.passed:
            if self.on_violation is not None:
                self.on_violation(report)
            if self.mode == "enforce":
                raise ContractViolation(report)
        return report

    def precheck(self, input: Any, **ctx: Any) -> Report:  # noqa: A002
        report = evaluate(
            self.contract,
            input=input,
            phase=Lifecycle.PRE,
            judge=self.judge,
            resources=self.resources,
            **ctx,
        )
        return self._handle(report)

    def postcheck(
        self,
        input: Any,  # noqa: A002
        output: Any,
        *,
        trajectory: Trajectory | None = None,
        **ctx: Any,
    ) -> Report:
        report = evaluate(
            self.contract,
            input=input,
            output=output,
            trajectory=trajectory,
            phase=Lifecycle.POST,
            judge=self.judge,
            resources=self.resources,
            **ctx,
        )
        return self._handle(report)

    def tool_check(self, tool_call: ToolCall, **ctx: Any) -> Report:
        report = evaluate(
            self.contract,
            tool_call=tool_call,
            phase=Lifecycle.ON_TOOL,
            judge=self.judge,
            resources=self.resources,
            **ctx,
        )
        return self._handle(report)


def _extract_input(args: tuple[Any, ...], kwargs: dict[str, Any], input_from: str | None) -> Any:
    if input_from is not None:
        if input_from in kwargs:
            return kwargs[input_from]
        raise KeyError(f"guard input_from='{input_from}' not found in kwargs")
    if args:
        return args[0]
    return dict(kwargs)


def guard(
    contract: Contract,
    *,
    judge: Judge | None = None,
    resources: Any = None,
    mode: Mode = "enforce",
    input_from: str | None = None,
    on_violation: Callable[[Report], None] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: enforce ``contract`` around a function-style agent.

    The agent's input is taken from the first positional argument (or the
    keyword named by ``input_from``); its output is the return value.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            g = Guard(
                contract,
                judge=judge,
                resources=resources,
                mode=mode,
                on_violation=on_violation,
            )
            agent_input = _extract_input(args, kwargs, input_from)
            g.precheck(agent_input)
            output = fn(*args, **kwargs)
            g.postcheck(agent_input, output)
            return output

        wrapper.__ratify_contract__ = contract  # type: ignore[attr-defined]
        return wrapper

    return decorator


@dataclass
class _OutputBox:
    """Mutable handle for a :func:`guarded` block's result and trajectory."""

    value: Any = None
    trajectory: Trajectory | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def record(self, value: Any, *, trajectory: Trajectory | None = None) -> None:
        self.value = value
        if trajectory is not None:
            self.trajectory = trajectory


@contextmanager
def guarded(
    contract: Contract,
    input: Any,  # noqa: A002
    *,
    judge: Judge | None = None,
    resources: Any = None,
    mode: Mode = "enforce",
    on_violation: Callable[[Report], None] | None = None,
) -> Iterator[_OutputBox]:
    """Context manager: precheck ``input``, run the block, postcheck the result.

    Assign the agent's result via the yielded box::

        with ratify.guarded(contract, prompt, judge=j) as box:
            box.record(agent.run(prompt), trajectory=traj)
    """
    g = Guard(contract, judge=judge, resources=resources, mode=mode, on_violation=on_violation)
    g.precheck(input)
    box = _OutputBox()
    yield box
    g.postcheck(input, box.value, trajectory=box.trajectory)
