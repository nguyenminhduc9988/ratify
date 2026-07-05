"""RAG grounding: a pathcondition (must retrieve) + probabilistic judging.

Demonstrates:
* a TRAJECTORY clause requiring the agent to call a retrieval tool before answering
* probabilistic (p, delta, k) satisfaction for a noisy "is it grounded?" judge

Run:  python examples/02_rag_grounding.py
"""

from __future__ import annotations

import ratify
from ratify import CallableJudge, JudgeVerdict, Scope, Trajectory


def build_contract() -> ratify.Contract:
    return (
        ratify.Contract("rag-answer", version="1.0")
        # Pathcondition: the agent MUST consult the retriever.
        .hard("must-retrieve", "Consulted the vector store before answering.",
              scope=Scope.TRAJECTORY, check=ratify.checks.used_tool("retrieve"))
        # Cost guard: don't over-retrieve.
        .hard("retrieve-budget", "At most 3 retrievals.",
              scope=Scope.TRAJECTORY, check=ratify.checks.max_tool_calls(3, name="retrieve"))
        # Probabilistic: 5 judge samples, at least 4 must clear 0.7.
        .judge("grounded", "Every claim is supported by the retrieved context.",
               scope=Scope.OUTPUT, threshold=0.7, samples=5, pass_rate=0.8)
    )


def main() -> None:
    # Simulate an agent run trajectory.
    traj = Trajectory()
    traj.record_tool("retrieve", args={"query": "refund policy"}, result="Refunds within 30 days.")
    traj.record_tool("retrieve", args={"query": "exceptions"}, result="No refunds on gift cards.")

    answer = "You can get a refund within 30 days, except on gift cards."

    # A slightly noisy judge: mostly confident, occasionally unsure.
    scores = iter([0.9, 0.85, 0.6, 0.95, 0.8])
    judge = CallableJudge(lambda c, ctx: JudgeVerdict(next(scores, 0.9), "checked grounding"))

    report = ratify.evaluate(
        build_contract(), output=answer, trajectory=traj, judge=judge
    )
    print(report.summary())
    for r in report.results:
        flag = "✅" if r.passed else "❌"
        print(f"  {flag} {r.clause_id}: {r.detail}")


if __name__ == "__main__":
    main()
