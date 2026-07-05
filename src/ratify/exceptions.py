"""Exception hierarchy for Ratify."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ratify.engine import Report


class RatifyError(Exception):
    """Base class for every error raised by Ratify."""


class ContractDefinitionError(RatifyError):
    """A contract or clause was defined incorrectly (bad params, duplicate id)."""


class BindingError(RatifyError):
    """A contract template was bound with missing or invalid parameters."""


class BudgetExceeded(RatifyError):  # noqa: N818 - intentional public API name
    """A resource budget was exceeded, or a child budget violated conservation."""


class ContractViolation(RatifyError):  # noqa: N818 - intentional public API name
    """A blocking clause failed while running under :func:`ratify.guard`.

    Carries the full :class:`~ratify.engine.Report` so callers can inspect
    every clause result, not just the first failure.
    """

    def __init__(self, report: Report) -> None:
        self.report = report
        violated = ", ".join(r.clause_id for r in report.violations) or "unknown"
        super().__init__(f"Contract '{report.contract}' violated by clause(s): {violated}")
