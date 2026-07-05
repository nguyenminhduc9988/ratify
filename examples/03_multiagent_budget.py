"""Multi-agent delegation with budget conservation.

An orchestrator delegates to two workers. Ratify guarantees each child budget
fits within the parent's remaining headroom — runaway spend is impossible.

Run:  python examples/03_multiagent_budget.py
"""

from __future__ import annotations

from ratify import BudgetExceeded, ResourceBudget


def main() -> None:
    root = ResourceBudget(tokens=100_000, cost_usd=5.0, label="orchestrator")
    print("Start:", root)

    researcher = root.child(label="researcher", tokens=40_000, cost_usd=2.0)
    writer = root.child(label="writer", tokens=30_000, cost_usd=1.5)
    print("Delegated:", researcher, "|", writer)

    # Workers consume from their own budgets.
    researcher.consume(tokens=38_000, cost_usd=1.8)
    writer.consume(tokens=12_000, cost_usd=0.6)
    print("After work:", researcher, "|", writer)

    # A rogue delegation that exceeds the orchestrator's remaining budget is rejected.
    try:
        root.child(label="rogue", tokens=90_000)
    except BudgetExceeded as exc:
        print("Blocked rogue delegation:", exc)

    # Overspending a child's own ceiling is also blocked.
    try:
        writer.consume(tokens=25_000)
    except BudgetExceeded as exc:
        print("Blocked overspend:", exc)


if __name__ == "__main__":
    main()
