"""Framework-agnostic adapter: ratify *any* callable agent.

This is the lowest-common-denominator integration. If your agent framework can
expose a ``run(input) -> output`` callable (they all can), you can enforce a
contract around it without any framework-specific code.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ratify.contract import Contract
from ratify.engine import Report
from ratify.guard import Guard, Mode
from ratify.judge import Judge
from ratify.trace import Trajectory


class RatifiedAgent:
    """Wrap a ``callable(input) -> output`` agent with contract enforcement.

    Example::

        agent = RatifiedAgent(my_agent.run, contract, judge=my_judge)
        answer = agent("What is 2 + 2?")     # pre/post checks enforced
        print(agent.last_report.summary())
    """

    def __init__(
        self,
        fn: Callable[..., Any],
        contract: Contract,
        *,
        judge: Judge | None = None,
        resources: Any = None,
        mode: Mode = "enforce",
        trajectory_from: Callable[[Any], Trajectory] | None = None,
    ) -> None:
        self._fn = fn
        self.contract = contract
        self.judge = judge
        self.resources = resources
        self.mode = mode
        self._trajectory_from = trajectory_from
        self.last_report: Report | None = None
        self.reports: list[Report] = []

    def __call__(self, agent_input: Any, *args: Any, **kwargs: Any) -> Any:
        g = Guard(self.contract, judge=self.judge, resources=self.resources, mode=self.mode)
        g.precheck(agent_input)
        output = self._fn(agent_input, *args, **kwargs)
        trajectory = self._trajectory_from(output) if self._trajectory_from else None
        g.postcheck(agent_input, output, trajectory=trajectory)
        self.reports.extend(g.reports)
        self.last_report = g.reports[-1] if g.reports else None
        return output


def wrap(
    fn: Callable[..., Any],
    contract: Contract,
    *,
    judge: Judge | None = None,
    resources: Any = None,
    mode: Mode = "enforce",
    trajectory_from: Callable[[Any], Trajectory] | None = None,
) -> RatifiedAgent:
    """Convenience factory for :class:`RatifiedAgent`."""
    return RatifiedAgent(
        fn,
        contract,
        judge=judge,
        resources=resources,
        mode=mode,
        trajectory_from=trajectory_from,
    )
