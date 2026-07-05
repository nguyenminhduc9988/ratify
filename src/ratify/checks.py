"""Built-in deterministic checks — the *hard* half of the enforcement layer.

Every function here is a *factory*: it returns a ``check`` callable suitable
for a ``HARD`` or ``PROOF`` clause. Checks return a :class:`CheckResult` with a
human-readable ``detail`` so violation reports explain themselves.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from ratify.context import CheckContext, CheckResult

Predicate = Callable[[CheckContext], CheckResult]


def _text_of(ctx: CheckContext, field: str) -> str:
    value = getattr(ctx, field, None)
    return "" if value is None else str(value)


# -- trivial -----------------------------------------------------------------


def always_pass() -> Predicate:
    """A check that always passes (useful as a placeholder)."""
    return lambda ctx: CheckResult(True, "always passes")


def always_fail(detail: str = "always fails") -> Predicate:
    """A check that always fails."""
    return lambda ctx: CheckResult(False, detail, score=0.0)


def predicate(fn: Callable[[CheckContext], bool], detail: str = "") -> Predicate:
    """Wrap an arbitrary ``fn(ctx) -> bool`` as a check."""

    def _check(ctx: CheckContext) -> CheckResult:
        ok = bool(fn(ctx))
        return CheckResult(
            ok,
            detail or ("predicate passed" if ok else "predicate failed"),
            score=1.0 if ok else 0.0,
        )

    return _check


# -- text / regex ------------------------------------------------------------


def matches(pattern: str, *, field: str = "output", flags: int = 0) -> Predicate:
    """Pass if ``field`` (``"output"`` or ``"input"``) matches ``pattern``."""
    rx = re.compile(pattern, flags)

    def _check(ctx: CheckContext) -> CheckResult:
        text = _text_of(ctx, field)
        ok = rx.search(text) is not None
        return CheckResult(
            ok,
            f"{field} {'matches' if ok else 'does not match'} /{pattern}/",
            score=1.0 if ok else 0.0,
        )

    return _check


def excludes(*substrings: str, field: str = "output", ignore_case: bool = True) -> Predicate:
    """Pass if ``field`` contains *none* of ``substrings`` (a deny-list)."""

    def _check(ctx: CheckContext) -> CheckResult:
        text = _text_of(ctx, field)
        hay = text.lower() if ignore_case else text
        hits = [s for s in substrings if (s.lower() if ignore_case else s) in hay]
        ok = not hits
        return CheckResult(
            ok,
            "no forbidden substrings" if ok else f"forbidden substring(s) present: {hits}",
            score=1.0 if ok else 0.0,
        )

    return _check


def includes(*substrings: str, field: str = "output", ignore_case: bool = True) -> Predicate:
    """Pass if ``field`` contains *all* of ``substrings``."""

    def _check(ctx: CheckContext) -> CheckResult:
        text = _text_of(ctx, field)
        hay = text.lower() if ignore_case else text
        missing = [s for s in substrings if (s.lower() if ignore_case else s) not in hay]
        ok = not missing
        return CheckResult(
            ok,
            "all required substrings present" if ok else f"missing substring(s): {missing}",
            score=1.0 if ok else 0.0,
        )

    return _check


def max_length(n: int, *, field: str = "output") -> Predicate:
    """Pass if ``len(str(field)) <= n``."""

    def _check(ctx: CheckContext) -> CheckResult:
        length = len(_text_of(ctx, field))
        ok = length <= n
        return CheckResult(ok, f"{field} length {length} (limit {n})", score=1.0 if ok else 0.0)

    return _check


def min_length(n: int, *, field: str = "output") -> Predicate:
    """Pass if ``len(str(field)) >= n``."""

    def _check(ctx: CheckContext) -> CheckResult:
        length = len(_text_of(ctx, field))
        ok = length >= n
        return CheckResult(ok, f"{field} length {length} (min {n})", score=1.0 if ok else 0.0)

    return _check


# -- structured output -------------------------------------------------------


def is_json(*, field: str = "output") -> Predicate:
    """Pass if ``field`` parses as JSON (or is already a dict/list)."""

    def _check(ctx: CheckContext) -> CheckResult:
        value = getattr(ctx, field, None)
        if isinstance(value, (dict, list)):
            return CheckResult(True, f"{field} is already structured")
        try:
            json.loads(_text_of(ctx, field))
        except (ValueError, TypeError) as exc:
            return CheckResult(False, f"{field} is not valid JSON: {exc}", score=0.0)
        return CheckResult(True, f"{field} is valid JSON")

    return _check


def has_keys(*keys: str, field: str = "output") -> Predicate:
    """Pass if ``field`` is a JSON object (or dict) containing all ``keys``."""

    def _check(ctx: CheckContext) -> CheckResult:
        value = getattr(ctx, field, None)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                return CheckResult(False, f"{field} is not JSON", score=0.0)
        if not isinstance(value, dict):
            return CheckResult(False, f"{field} is not an object", score=0.0)
        missing = [k for k in keys if k not in value]
        ok = not missing
        return CheckResult(
            ok, "all keys present" if ok else f"missing keys: {missing}", score=1.0 if ok else 0.0
        )

    return _check


def json_schema(schema: dict[str, Any], *, field: str = "output") -> Predicate:
    """Validate ``field`` against a JSON Schema (requires ``jsonschema``).

    Install with ``pip install ratify-agents[schema]``.
    """

    def _check(ctx: CheckContext) -> CheckResult:
        try:
            import jsonschema
        except ImportError as exc:  # pragma: no cover - exercised only w/o extra
            raise RuntimeError(
                "json_schema() requires the 'jsonschema' package; install ratify-agents[schema]"
            ) from exc
        value = getattr(ctx, field, None)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                return CheckResult(False, f"{field} is not JSON", score=0.0)
        try:
            jsonschema.validate(value, schema)
        except jsonschema.ValidationError as exc:
            return CheckResult(False, f"schema violation: {exc.message}", score=0.0)
        return CheckResult(True, "matches schema")

    return _check


# -- tools (ON_TOOL) ---------------------------------------------------------


def tool_allowed(*allowed: str) -> Predicate:
    """ON_TOOL: pass if the current tool call's name is in ``allowed``."""
    allow = set(allowed)

    def _check(ctx: CheckContext) -> CheckResult:
        call = ctx.tool_call
        if call is None:
            return CheckResult(True, "no tool call in context")
        ok = call.name in allow
        return CheckResult(
            ok,
            f"tool '{call.name}' {'allowed' if ok else 'not in allow-list'}",
            score=1.0 if ok else 0.0,
        )

    return _check


def tool_denied(*denied: str) -> Predicate:
    """ON_TOOL: pass if the current tool call's name is *not* in ``denied``."""
    deny = set(denied)

    def _check(ctx: CheckContext) -> CheckResult:
        call = ctx.tool_call
        if call is None:
            return CheckResult(True, "no tool call in context")
        ok = call.name not in deny
        return CheckResult(
            ok, f"tool '{call.name}' {'permitted' if ok else 'is denied'}", score=1.0 if ok else 0.0
        )

    return _check


# -- trajectory / pathconditions --------------------------------------------


def used_tool(name: str) -> Predicate:
    """TRAJECTORY: pass if ``name`` was called at least once."""

    def _check(ctx: CheckContext) -> CheckResult:
        traj = ctx.trajectory
        ok = traj is not None and traj.used_tool(name)
        return CheckResult(
            ok, f"tool '{name}' {'was' if ok else 'was not'} used", score=1.0 if ok else 0.0
        )

    return _check


def never_used_tool(name: str) -> Predicate:
    """TRAJECTORY: pass if ``name`` was never called."""

    def _check(ctx: CheckContext) -> CheckResult:
        traj = ctx.trajectory
        ok = traj is None or not traj.used_tool(name)
        return CheckResult(
            ok, f"tool '{name}' {'was never' if ok else 'was'} used", score=1.0 if ok else 0.0
        )

    return _check


def max_tool_calls(n: int, *, name: str | None = None) -> Predicate:
    """TRAJECTORY: pass if total (or per-``name``) tool calls do not exceed ``n``."""

    def _check(ctx: CheckContext) -> CheckResult:
        traj = ctx.trajectory
        count = 0 if traj is None else (traj.count_tool(name) if name else len(traj.tool_calls))
        ok = count <= n
        label = f"'{name}'" if name else "total"
        return CheckResult(ok, f"{label} tool calls: {count} (limit {n})", score=1.0 if ok else 0.0)

    return _check


def tool_order(*names: str) -> Predicate:
    """TRAJECTORY: pass if ``names`` appear as an ordered subsequence of calls."""

    def _check(ctx: CheckContext) -> CheckResult:
        traj = ctx.trajectory
        sequence = [] if traj is None else traj.tool_names
        it = iter(sequence)
        ok = all(any(n == s for s in it) for n in names)
        return CheckResult(
            ok,
            f"expected order {list(names)} vs actual {sequence}",
            score=1.0 if ok else 0.0,
        )

    return _check


def all_tools_succeeded() -> Predicate:
    """TRAJECTORY: pass if every recorded tool call reported success."""

    def _check(ctx: CheckContext) -> CheckResult:
        traj = ctx.trajectory
        failed = [] if traj is None else [c.name for c in traj.tool_calls if not c.ok]
        ok = not failed
        return CheckResult(
            ok, "all tools ok" if ok else f"failed tools: {failed}", score=1.0 if ok else 0.0
        )

    return _check


# -- resources ---------------------------------------------------------------


def within_budget() -> Predicate:
    """RESOURCE: pass if the attached :class:`ResourceBudget` is within limits."""

    def _check(ctx: CheckContext) -> CheckResult:
        res = ctx.resources
        if res is None:
            return CheckResult(True, "no budget attached")
        ok = res.within_limits()
        return CheckResult(ok, repr(res), score=1.0 if ok else 0.0)

    return _check
