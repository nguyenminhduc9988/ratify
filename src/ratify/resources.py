"""Resource budgets with hierarchical *conservation*.

Inspired by the delegation conservation laws in "Agent Contracts" (Ye & Tan,
2026): a delegated child budget may never let a subtree spend more than its
ancestors permit. Two mechanisms enforce this:

* **Creation check** — a child ceiling cannot exceed the parent's *remaining*
  headroom at the moment of delegation.
* **Propagating consumption** — spending in a child is metered against every
  ancestor atomically, so a parent's hard limit is never exceeded no matter how
  its children are structured. Runaway multi-agent spend becomes structurally
  impossible, not merely discouraged.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from ratify.exceptions import BudgetExceeded

_METRICS = ("tokens", "cost_usd", "wall_time_s", "tool_calls")


@dataclass
class ResourceBudget:
    """A ceiling on the resources an agent (subtree) may consume.

    A value of ``None`` for a metric means "unbounded". Consumption is tracked
    in :attr:`used` and propagates to ancestors; :meth:`remaining` reports
    headroom for new spending or delegation.
    """

    tokens: int | None = None
    cost_usd: float | None = None
    wall_time_s: float | None = None
    tool_calls: int | None = None
    label: str = "root"

    def __post_init__(self) -> None:
        self.used: dict[str, float] = dict.fromkeys(_METRICS, 0.0)
        self._children: list[ResourceBudget] = []
        self._parent: ResourceBudget | None = None
        for m in _METRICS:
            limit = getattr(self, m)
            if limit is not None and limit < 0:
                raise BudgetExceeded(f"{self.label}: {m} limit cannot be negative")

    # -- consumption ---------------------------------------------------------

    def _chain(self) -> list[ResourceBudget]:
        chain: list[ResourceBudget] = []
        node: ResourceBudget | None = self
        while node is not None:
            chain.append(node)
            node = node._parent
        return chain

    def consume(
        self,
        *,
        tokens: float = 0,
        cost_usd: float = 0,
        wall_time_s: float = 0,
        tool_calls: float = 0,
    ) -> None:
        """Record usage against this budget and every ancestor, atomically.

        If any budget in the chain would exceed a ceiling, :class:`BudgetExceeded`
        is raised and *no* budget is mutated.
        """
        delta = {
            "tokens": tokens,
            "cost_usd": cost_usd,
            "wall_time_s": wall_time_s,
            "tool_calls": tool_calls,
        }
        chain = self._chain()
        for node in chain:
            for m, d in delta.items():
                limit = getattr(node, m)
                if limit is not None and node.used[m] + d > limit:
                    raise BudgetExceeded(
                        f"{node.label}: {m} budget exceeded ({node.used[m] + d:g} > {limit:g})"
                    )
        for node in chain:
            for m, d in delta.items():
                node.used[m] += d

    def remaining(self, metric: str) -> float | None:
        """Headroom left for ``metric``; ``None`` if that metric is unbounded."""
        if metric not in _METRICS:
            raise ValueError(f"unknown metric {metric!r}; expected one of {_METRICS}")
        limit: float | None = getattr(self, metric)
        if limit is None:
            return None
        return float(limit) - self.used[metric]

    def within_limits(self) -> bool:
        """True if no metric has exceeded its ceiling."""
        return all(getattr(self, m) is None or self.used[m] <= getattr(self, m) for m in _METRICS)

    # -- delegation ----------------------------------------------------------

    def child(self, *, label: str, **limits: float | None) -> ResourceBudget:
        """Create a delegated sub-budget, enforcing conservation.

        Each requested child ceiling must fit within the parent's *remaining*
        headroom for that metric at delegation time. The child's spending is
        additionally metered against this budget (and its ancestors) via
        :meth:`consume`, so the parent's hard limit can never be exceeded.
        """
        bad = set(limits) - set(_METRICS)
        if bad:
            raise ValueError(f"unknown metric(s): {sorted(bad)}")
        for m, requested in limits.items():
            if requested is None:
                continue
            head = self.remaining(m)
            if head is not None and requested > head:
                raise BudgetExceeded(
                    f"{self.label} -> {label}: requested {m}={requested:g} exceeds "
                    f"parent remaining {head:g}"
                )
        child = ResourceBudget(label=label, **limits)  # type: ignore[arg-type]
        child._parent = self
        self._children.append(child)
        return child

    def snapshot(self) -> dict[str, float]:
        """A copy of current usage keyed by metric."""
        return dict(self.used)

    def __repr__(self) -> str:
        parts = []
        for f in fields(self):
            if f.name == "label":
                continue
            limit = getattr(self, f.name)
            if limit is not None:
                parts.append(f"{f.name}={self.used[f.name]:g}/{limit:g}")
        inner = ", ".join(parts) if parts else "unbounded"
        return f"ResourceBudget({self.label!r}: {inner})"
