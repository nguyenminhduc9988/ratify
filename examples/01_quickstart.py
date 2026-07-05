"""Quickstart: declare a contract, bind a template param, guard an agent.

Run:  python examples/01_quickstart.py
"""

from __future__ import annotations

import ratify
from ratify import KeywordJudge, Scope


def build_contract() -> ratify.Contract:
    return (
        ratify.Contract("support-reply", version="1.0")
        .param("brand", type=str)
        .hard("no-pii", "Must not leak an email address.", scope=Scope.OUTPUT,
              check=ratify.checks.excludes("@"))
        .hard("bounded", "Reply <= 280 chars.", scope=Scope.OUTPUT,
              check=ratify.checks.max_length(280))
        .judge("on-brand", "The reply mentions {brand} and stays positive.",
               scope=Scope.BEHAVIORAL, threshold=0.6)
    )


def main() -> None:
    acme = build_contract().bind(brand="Acme")
    judge = KeywordJudge(required=["Acme"])  # swap for OpenAIJudge in production

    @ratify.guard(acme, judge=judge, mode="monitor")
    def agent(question: str) -> str:
        return "Thanks for reaching out to Acme — happy to help you reset your password!"

    answer = agent("How do I reset my password?")
    print("Answer:", answer)

    # Inspect the last report by evaluating directly:
    report = ratify.evaluate(acme, output=answer, judge=judge)
    print(report.summary())
    for r in report.results:
        flag = "✅" if r.passed else "❌"
        print(f"  {flag} [{r.scope.value}/{r.enforcement.value}] {r.clause_id}: {r.detail}")


if __name__ == "__main__":
    main()
