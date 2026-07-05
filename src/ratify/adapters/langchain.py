"""LangChain / LangGraph adapter.

This module is *duck-typed*: it never imports ``langchain``. It provides a
callback handler compatible with LangChain's ``BaseCallbackHandler`` protocol
that records tool calls into a Ratify :class:`~ratify.trace.Trajectory`, plus a
helper to guard any LangChain ``Runnable`` (anything with ``.invoke``).

Usage::

    from ratify.adapters.langchain import RatifyCallbackHandler, guard_runnable

    handler = RatifyCallbackHandler()
    result = chain.invoke(prompt, config={"callbacks": [handler]})
    report = ratify.evaluate(contract, input=prompt, output=result,
                             trajectory=handler.trajectory, judge=judge)
"""

from __future__ import annotations

from typing import Any

from ratify.contract import Contract
from ratify.engine import Report, evaluate
from ratify.judge import Judge
from ratify.trace import Trajectory


class RatifyCallbackHandler:
    """A LangChain-compatible callback handler that builds a Trajectory.

    Implements the subset of ``BaseCallbackHandler`` needed to capture tool
    usage. Attach it via ``config={"callbacks": [handler]}`` on any LangChain
    or LangGraph invocation; read :attr:`trajectory` afterwards.
    """

    def __init__(self) -> None:
        self.trajectory = Trajectory()
        self._pending: list[str] = []

    # -- LangChain callback protocol (subset) --------------------------------

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        name = (serialized or {}).get("name", "tool")
        self._pending.append(name)
        self.trajectory.record_tool(name, args={"input": input_str})

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        if self.trajectory.tool_calls:
            self.trajectory.tool_calls[-1].result = output

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        if self.trajectory.tool_calls:
            call = self.trajectory.tool_calls[-1]
            call.ok = False
            call.error = str(error)

    # ignore the rest of the callback surface gracefully
    def __getattr__(self, name: str) -> Any:
        if name.startswith("on_"):
            return lambda *a, **k: None
        raise AttributeError(name)


def guard_runnable(
    runnable: Any,
    contract: Contract,
    input: Any,  # noqa: A002
    *,
    judge: Judge | None = None,
    resources: Any = None,
) -> tuple[Any, Report]:
    """Invoke a LangChain ``Runnable`` and evaluate its output against ``contract``.

    Returns ``(output, report)``. Raises nothing on violation — inspect
    ``report.passed`` yourself, or wrap with :func:`ratify.guard` for raising
    behavior. A :class:`RatifyCallbackHandler` is attached automatically so
    trajectory clauses work out of the box.
    """
    handler = RatifyCallbackHandler()
    try:
        output = runnable.invoke(input, config={"callbacks": [handler]})
    except TypeError:
        # Runnables that don't accept a config kwarg
        output = runnable.invoke(input)
    text = getattr(output, "content", output)
    report = evaluate(
        contract,
        input=input,
        output=text,
        trajectory=handler.trajectory,
        judge=judge,
        resources=resources,
    )
    return output, report
