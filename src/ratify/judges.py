"""Production LLM-judge adapters (OpenAI, Anthropic).

These are thin, lazily-imported wrappers around real model providers. They are
*not* exercised in the hermetic test suite (they need network + credentials);
they are covered by their construction contract and documented usage. For CI
and unit tests, use :class:`ratify.KeywordJudge` or
:class:`ratify.CallableJudge`.

The judge asks the model to score a criterion in ``[0, 1]`` and return strict
JSON ``{"score": float, "rationale": str}``.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ratify.context import CheckContext
from ratify.judge import JudgeVerdict

_PROMPT = """You are a strict contract auditor. Given a CRITERION and an \
agent's OUTPUT, decide how well the output satisfies the criterion.

Return ONLY minified JSON: {{"score": <float 0..1>, "rationale": "<short>"}}
- 1.0 = fully satisfies, 0.0 = clearly violates.

CRITERION:
{criterion}

AGENT INPUT:
{input}

AGENT OUTPUT:
{output}
"""


def _parse(text: str) -> JudgeVerdict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return JudgeVerdict(0.0, f"unparseable judge response: {text[:120]}")
    try:
        data = json.loads(match.group(0))
        score = float(data.get("score", 0.0))
        score = max(0.0, min(1.0, score))
        return JudgeVerdict(score, str(data.get("rationale", "")))
    except (ValueError, TypeError) as exc:
        return JudgeVerdict(0.0, f"bad judge JSON: {exc}")


def _render(criterion: str, ctx: CheckContext) -> str:
    return _PROMPT.format(
        criterion=criterion,
        input=str(ctx.input)[:2000],
        output=str(ctx.output)[:4000],
    )


class OpenAIJudge:
    """LLM judge backed by the OpenAI Chat Completions API.

    Install with ``pip install ratify-agents[openai]``. Example::

        judge = OpenAIJudge(model="gpt-4o-mini")
        report = ratify.evaluate(contract, output=answer, judge=judge)
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        *,
        client: Any = None,
        temperature: float = 0.0,
    ) -> None:
        if client is None:
            try:
                import openai
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError(
                    "OpenAIJudge requires the 'openai' package; install ratify-agents[openai]"
                ) from exc
            client = openai.OpenAI()
        self._client = client
        self.model = model
        self.temperature = temperature

    def evaluate(self, criterion: str, ctx: CheckContext) -> JudgeVerdict:
        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[{"role": "user", "content": _render(criterion, ctx)}],
        )
        return _parse(resp.choices[0].message.content or "")


class AnthropicJudge:
    """LLM judge backed by the Anthropic Messages API.

    Install with ``pip install ratify-agents[anthropic]``. Example::

        judge = AnthropicJudge(model="claude-3-5-haiku-latest")
    """

    def __init__(
        self,
        model: str = "claude-3-5-haiku-latest",
        *,
        client: Any = None,
        max_tokens: int = 512,
    ) -> None:
        if client is None:
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError(
                    "AnthropicJudge requires the 'anthropic' package; "
                    "install ratify-agents[anthropic]"
                ) from exc
            client = anthropic.Anthropic()
        self._client = client
        self.model = model
        self.max_tokens = max_tokens

    def evaluate(self, criterion: str, ctx: CheckContext) -> JudgeVerdict:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": _render(criterion, ctx)}],
        )
        return _parse(resp.content[0].text)
