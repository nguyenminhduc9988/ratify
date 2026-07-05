<div align="center">

# Ratify

**A unified contract layer for LLM agents.**

Declare *what* an agent must do as a parameterizable **contract** — then enforce it with
deterministic **checks** *and* fuzzy **LLM judgment**, verify runs offline, or guard them live.

[![CI](https://github.com/nguyenminhduc9988/ratify/actions/workflows/ci.yml/badge.svg)](https://github.com/nguyenminhduc9988/ratify/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/badge/lint-ruff-261230.svg)](https://github.com/astral-sh/ruff)
[![Typed](https://img.shields.io/badge/typing-strict-informational.svg)](https://mypy-lang.org)

</div>

---

## Why Ratify

Every agent framework tells you *how* to run an agent. Almost none let you declare *what it must and must not do* — and enforce that consistently across frameworks.

The 2025–2026 "agent contracts" wave (relari `agent-contracts`, `agentcontract/spec`, AgentAssert/ABC, ToolGate, FORGE) each nailed **one** slice: resource governance, or tool-level pre/postconditions, or policy enforcement, or behavioral invariants. **Ratify unifies them into one declarative object** and adds the two things production teams actually need:

| Axis | What it means | Values |
|------|---------------|--------|
| 🎯 **Scope** | *what* aspect of the agent a clause governs | `input` · `output` · `behavioral` · `tool` · `resource` · `policy` · `trajectory` |
| ⚙️ **Enforcement** | *how* a clause is decided | `hard` (code) · `judge` (LLM) · `proof` (strict gate) |
| ⏱️ **Lifecycle** | *when* a clause runs | `pre` · `post` · `invariant` · `on_tool` · `on_step` |

Plus: **parameterizable templates** (one contract → many scenarios), **composition** (reuse a base policy everywhere), **probabilistic satisfaction** (`(p, δ, k)` — run a judge *k* times, require a pass rate), **pathconditions** (constrain the *trajectory*, not just the output), and **budget conservation** (a delegated child budget can never exceed its parent).

Ratify has **zero required dependencies**, is **strictly typed**, and is **hermetically testable** — the LLM judge is a pluggable protocol, so the whole test suite runs offline.

## Install

```bash
pip install ratify-agents            # core, zero deps
pip install "ratify-agents[schema]"  # + JSON-Schema checks
pip install "ratify-agents[openai]"  # + OpenAI judge adapter
```

## 60-second example

```python
import ratify
from ratify import checks, Scope, Lifecycle

# 1. Declare a contract — a reusable template with a parameter.
support = (
    ratify.Contract("support-reply", version="1.0")
    .param("brand", type=str)
    # HARD: deterministic, runs on the output, no LLM needed
    .hard("no-pii", "Must not leak an email address.",
          scope=Scope.OUTPUT, check=checks.excludes("@"))
    .hard("bounded", "Reply is at most 600 chars.",
          scope=Scope.OUTPUT, check=checks.max_length(600))
    # JUDGE: fuzzy, an LLM scores the natural-language criterion
    .judge("on-brand", "The reply mentions {brand} and stays positive.",
           scope=Scope.BEHAVIORAL, threshold=0.6)
    # TRAJECTORY: a "pathcondition" on how the agent worked
    .hard("used-kb", "Must consult the knowledge base before answering.",
          scope=Scope.TRAJECTORY, check=checks.used_tool("search_kb"))
)

# 2. Specialize the same template for a specific client.
acme = support.bind(brand="Acme")

# 3. Enforce it live around your agent.
from ratify import KeywordJudge  # deterministic stand-in; swap for a real model
judge = KeywordJudge(required=["Acme"])

@ratify.guard(acme, judge=judge)
def agent(question: str) -> str:
    return "Thanks for reaching out to Acme — happy to help!"

print(agent("How do I reset my password?"))
```

If a **blocking** clause fails, `ContractViolation` is raised with a full report; switch to `mode="monitor"` to log instead of raise.

## Three ways to enforce

```python
# a) Offline verification (CI, eval harnesses, replaying traces)
report = ratify.evaluate(acme, output=answer, trajectory=traj, judge=judge)
assert report.passed, report.summary()

# b) Decorator (function-style agents)
@ratify.guard(acme, judge=judge, mode="monitor")
def my_agent(q): ...

# c) Context manager (imperative loops)
with ratify.guarded(acme, prompt, judge=judge) as box:
    box.record(agent.run(prompt), trajectory=traj)
```

## Probabilistic satisfaction — `(p, δ, k)`

LLM judgments are noisy. A clause can require that a criterion hold across *k* samples:

```python
contract.judge(
    "grounded", "Every claim is supported by the retrieved context.",
    scope=Scope.OUTPUT,
    threshold=0.7,   # a single judgment "passes" at score ≥ 0.7
    samples=5,       # k: run the judge 5 times
    pass_rate=0.8,   # p: at least 4/5 must pass
)
```

## Budget conservation for multi-agent delegation

```python
from ratify import ResourceBudget

root = ResourceBudget(tokens=100_000, cost_usd=5.0, label="orchestrator")
worker = root.child(label="researcher", tokens=40_000)   # ✅ fits
root.child(label="rogue", tokens=200_000)                # ❌ BudgetExceeded
```

A child budget that would exceed the parent's *remaining* headroom is rejected at creation — runaway spend becomes structurally impossible, not merely discouraged.

## Integrations

The **generic adapter** ratifies any `callable(input) -> output`, so it works with every framework today:

```python
from ratify.adapters import wrap
safe_agent = wrap(my_agent.run, contract, judge=judge)
```

Framework guides (LangChain / LangGraph, CrewAI, AutoGen, OpenAI Agents SDK, Pydantic-AI, Anthropic + MCP) with copy-paste snippets live in **[`docs/INTEGRATION.md`](docs/INTEGRATION.md)**.

## Documentation

- **[Integration guide](docs/INTEGRATION.md)** — per-framework wiring
- **[Concepts](docs/CONCEPTS.md)** — the scope × enforcement × lifecycle model, prior art, and design rationale
- **[`examples/`](examples/)** — runnable end-to-end scripts

## Status & honesty

`0.1.0`, beta. The **core engine, checks, judge protocol, resources, trajectory, and the generic adapter are fully unit-tested** (see `tests/`, run `pytest`). Framework-specific adapters are provided as **documented, import-light patterns**; those requiring a third-party package are labeled as such and are *not* exercised in the default hermetic test run. Contributions and real-world reports welcome.

## License

MIT © 2026 Duc Nguyen
