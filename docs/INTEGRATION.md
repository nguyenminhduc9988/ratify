# Integration Guide

Ratify sits *beside* your agent framework, not inside it. The contract, the
checks, and the judge are all framework-agnostic; you only need to give Ratify
three things about a run:

| What | Where it comes from |
|------|---------------------|
| **input** | the prompt / task you gave the agent |
| **output** | the agent's final answer |
| **trajectory** (optional) | the tools it called, for `TRAJECTORY` / pathcondition clauses |

Every framework below reduces to *"get those three, then call `ratify.evaluate` or wrap with `ratify.guard`."*

> **Verified vs. example.** The **generic** and **LangChain** adapters are duck-typed and covered by the hermetic test suite. The other snippets are integration *patterns* — correct against each framework's public API but not exercised in CI (they need the third-party package). They are labeled accordingly.

---

## 0. Generic — works with everything ✅ *tested*

If your agent is (or can be) a `callable(input) -> output`, you're done:

```python
from ratify.adapters import wrap

safe_agent = wrap(my_agent.run, contract, judge=judge)         # enforce mode
answer = safe_agent("summarize this ticket")                   # raises on violation

# or non-raising:
safe_agent = wrap(my_agent.run, contract, judge=judge, mode="monitor")
answer = safe_agent("...")
print(safe_agent.last_report.summary())
```

Supply a `trajectory_from=` callback to turn your agent's output into a `Trajectory` so `TRAJECTORY`/`TOOL` clauses can run.

---

## 1. LangChain / LangGraph ✅ *tested (duck-typed)*

Ratify ships a callback handler that records tool calls into a `Trajectory`:

```python
import ratify
from ratify.adapters.langchain import RatifyCallbackHandler, guard_runnable

# Option A — one-liner helper (attaches the handler for you):
output, report = guard_runnable(chain, contract, prompt, judge=judge)
if not report.passed:
    raise ratify.ContractViolation(report)

# Option B — manual, full control:
handler = RatifyCallbackHandler()
result = chain.invoke(prompt, config={"callbacks": [handler]})
report = ratify.evaluate(
    contract, input=prompt, output=getattr(result, "content", result),
    trajectory=handler.trajectory, judge=judge,
)
```

`RatifyCallbackHandler` implements the `on_tool_start` / `on_tool_end` /
`on_tool_error` subset of LangChain's `BaseCallbackHandler`, so it works for
both LangChain agents and **LangGraph** graphs (pass it in the `config`).

**LangGraph state-machine tip:** add an enforcement node that calls
`ratify.evaluate(...)` on the graph state and routes to a `remediate` node when
`report.passed` is `False` — turning a contract into a control-flow guard.

---

## 2. OpenAI Agents SDK ⚠️ *pattern*

```python
import ratify
from agents import Agent, Runner
from ratify import Trajectory

result = Runner.run_sync(agent, prompt)

# Build a trajectory from the SDK's run items.
traj = Trajectory()
for item in result.new_items:
    if item.type == "tool_call_item":
        traj.record_tool(item.raw_item.name)

report = ratify.evaluate(
    contract, input=prompt, output=result.final_output,
    trajectory=traj, judge=judge,
)
```

You can also express a contract as an SDK **output guardrail** by calling
`ratify.evaluate` inside a `@output_guardrail` function and raising when it fails.

---

## 3. CrewAI ⚠️ *pattern*

```python
import ratify

result = crew.kickoff(inputs={"topic": topic})
report = ratify.evaluate(contract, input=topic, output=str(result), judge=judge)
```

For per-task enforcement, wrap each task's callback, or use CrewAI's
`task_callback` to feed `ratify.evaluate` after every task and short-circuit the
crew on a blocking violation.

---

## 4. AutoGen / AG2 ⚠️ *pattern*

```python
import ratify

chat = user.initiate_chat(assistant, message=prompt)
final = chat.summary if hasattr(chat, "summary") else chat.chat_history[-1]["content"]
report = ratify.evaluate(contract, input=prompt, output=final, judge=judge)
```

Register `ratify.evaluate` as a **reply hook** (`register_hook("process_message_before_send", ...)`) to gate every outgoing message.

---

## 5. Pydantic-AI ⚠️ *pattern*

```python
import ratify

result = agent.run_sync(prompt)
report = ratify.evaluate(contract, input=prompt, output=result.output, judge=judge)
```

Pydantic-AI already validates *structural* output types; Ratify adds the
behavioral, policy, and trajectory clauses on top. Use a Ratify `HARD` clause
with `checks.json_schema(...)` if you want the structural check inside the
contract too.

---

## 6. Anthropic API + MCP ⚠️ *pattern*

```python
import anthropic, ratify
from ratify import Trajectory

client = anthropic.Anthropic()
resp = client.messages.create(model="claude-3-5-sonnet-latest", max_tokens=1024,
                              messages=[{"role": "user", "content": prompt}], tools=tools)

traj = Trajectory()
text = ""
for block in resp.content:
    if block.type == "tool_use":
        traj.record_tool(block.name, args=block.input)
    elif block.type == "text":
        text += block.text

report = ratify.evaluate(contract, input=prompt, output=text, trajectory=traj, judge=judge)
```

For **MCP** tool servers, add an `ON_TOOL` clause with
`checks.tool_allowed(...)` and call `guard.tool_check(ToolCall(name=...))`
before dispatching each MCP tool call — a deterministic allow-list at the tool
boundary (à la ToolGate).

---

## Choosing a judge

| Judge | Use when | Network? |
|-------|----------|----------|
| `KeywordJudge` | tests, cheap heuristics | no |
| `CallableJudge` | you already have a scoring function | no |
| `judges.OpenAIJudge` | production, GPT models | yes |
| `judges.AnthropicJudge` | production, Claude models | yes |

```python
from ratify.judges import OpenAIJudge
judge = OpenAIJudge(model="gpt-4o-mini")   # reads OPENAI_API_KEY
report = ratify.evaluate(contract, output=answer, judge=judge)
```

Any object with `evaluate(criterion: str, ctx: CheckContext) -> JudgeVerdict`
is a valid judge — bring your own local model.

---

## CI usage

Ratify is ideal in an **evaluation gate**: replay recorded agent traces and
fail the build if a contract regresses.

```python
for case in load_eval_cases():
    report = ratify.evaluate(contract, input=case.input, output=case.output,
                             trajectory=case.trajectory, judge=judge)
    assert report.passed, report.summary()
```
