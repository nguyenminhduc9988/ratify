"""Ratify — a unified contract layer for LLM agents.

Declare *what* an agent must do as a parameterizable **contract**; enforce it
with deterministic **checks** and fuzzy **LLM judgment**; verify runs offline
or guard them live.

Quick start::

    import ratify
    from ratify import checks, Scope

    contract = (
        ratify.Contract("greeter")
        .hard("polite", "No rude words.", scope=Scope.OUTPUT,
              check=checks.excludes("stupid", "idiot"))
        .judge("helpful", "The reply actually answers the question.",
               scope=Scope.BEHAVIORAL)
    )

    report = ratify.evaluate(contract, output="Happy to help!",
                             judge=ratify.KeywordJudge(required=["help"]))
    assert report.passed
"""

from __future__ import annotations

from ratify import checks
from ratify.clause import Clause
from ratify.context import CheckContext, CheckResult
from ratify.contract import Contract, ParamSpec
from ratify.engine import ClauseResult, Report, evaluate
from ratify.enums import Enforcement, Lifecycle, Scope, Severity
from ratify.exceptions import (
    BindingError,
    BudgetExceeded,
    ContractDefinitionError,
    ContractViolation,
    RatifyError,
)
from ratify.guard import Guard, guard, guarded
from ratify.judge import CallableJudge, Judge, JudgeVerdict, KeywordJudge
from ratify.resources import ResourceBudget
from ratify.trace import Step, ToolCall, Trajectory

__version__ = "0.1.0"

__all__ = [
    # enums
    "Scope",
    "Enforcement",
    "Severity",
    "Lifecycle",
    # core
    "Clause",
    "Contract",
    "ParamSpec",
    "CheckContext",
    "CheckResult",
    "evaluate",
    "Report",
    "ClauseResult",
    # judge
    "Judge",
    "JudgeVerdict",
    "CallableJudge",
    "KeywordJudge",
    # runtime
    "Guard",
    "guard",
    "guarded",
    # resources & trace
    "ResourceBudget",
    "Trajectory",
    "Step",
    "ToolCall",
    # checks module
    "checks",
    # exceptions
    "RatifyError",
    "ContractDefinitionError",
    "BindingError",
    "BudgetExceeded",
    "ContractViolation",
    "__version__",
]
