# Concepts & Design

## The model: Scope × Enforcement × Lifecycle

Ratify's core claim is that most "agent reliability" needs collapse onto three
orthogonal axes. A **clause** is one point in that space; a **contract** is a
set of clauses.

```
            Scope (what)          Enforcement (how)     Lifecycle (when)
          ┌────────────────┐     ┌──────────────┐      ┌──────────────┐
          │ input          │     │ hard  (code) │      │ pre          │
          │ output         │  ×  │ judge (LLM)  │   ×  │ post         │
          │ behavioral     │     │ proof (gate) │      │ invariant    │
          │ tool           │     └──────────────┘      │ on_tool      │
          │ resource       │                           │ on_step      │
          │ policy         │                           └──────────────┘
          │ trajectory     │
          └────────────────┘
```

Because the axes are independent, one small vocabulary expresses "output must be
valid JSON" (output · hard · post), "must stay on-brand" (behavioral · judge ·
post), "never call `delete_user`" (tool · hard · on_tool), and "must retrieve
before answering" (trajectory · hard · post) — without a bespoke mechanism per
need.

## Templates: one definition, many scenarios

A contract is a **template**. Declare parameters, then `bind()` values to
specialize it. `{param}` placeholders in judge criteria are filled at
evaluation time. This is what lets one `support-reply` contract serve every
client, and one `rag-answer` contract serve every knowledge base.

```python
base = Contract("support").param("brand", type=str).judge(
    "on-brand", "Mentions {brand} positively.", scope=Scope.BEHAVIORAL)
acme  = base.bind(brand="Acme")
globex = base.bind(brand="Globex")
```

Contracts also **compose** (`include` / `+`), so a shared `safety` contract can
be merged into every product contract.

## Probabilistic satisfaction `(p, δ, k)`

Deterministic checks are boolean. LLM judgments are not. A `JUDGE` clause runs
the judge `k` = `samples` times; a single run "passes" at `score ≥ threshold`;
the clause passes if the pass fraction `≥ pass_rate`. This is a practical
encoding of the probabilistic-contract idea shared across the recent literature
(ABC's `(p, δ, k)`-satisfaction; `P_succ`-annotated Hoare triples).

## Trajectory / pathconditions

Classic design-by-contract has pre/postconditions and invariants — none of which
constrain *how* a result was produced. Ratify adds **trajectory** clauses
(a "pathcondition"): assertions over the ordered tool calls an agent made
(`used_tool`, `tool_order`, `max_tool_calls`, `all_tools_succeeded`).

## Budget conservation

`ResourceBudget` enforces conservation two ways: a child ceiling can't exceed
the parent's remaining headroom at delegation, and child spending **propagates**
to every ancestor atomically. A subtree therefore can't outspend its root no
matter how it's structured — runaway multi-agent cost is structurally
impossible, not merely discouraged.

## Fail-closed

If a `HARD` check raises, or a `JUDGE` clause has no judge configured, the
clause **fails** (it does not silently pass). Blocking failures raise under
`guard`. Safety defaults to the safe side.

---

## Prior art & where Ratify differs

Ratify is a synthesis of a fast-moving 2025–2026 body of work. It deliberately
borrows the best idea from each and unifies them:

| Prior work | Contribution Ratify adopts | What it *didn't* unify |
|------------|----------------------------|------------------------|
| **Meyer — Design by Contract** (Eiffel) | pre/postconditions, invariants | pre-LLM; deterministic only |
| **Agent Contracts** — Ye & Tan 2026 (`arXiv:2601.08815`) | resource governance + delegation **conservation laws** | not behavioral / tool-level |
| **Agent Behavioral Contracts (ABC)** — 2026 (`arXiv:2602.22302`) | `(P,I,G,R)` + **probabilistic `(p,δ,k)` satisfaction** | no templating / composition |
| **Neurosymbolic DbC** — ExtensityAI 2025 (`arXiv:2508.03665`) | contracts mediate every LLM call; hard + semantic predicates | position paper; no runtime lib |
| **ToolGate** — 2026 (`arXiv:2601.04688`) | Hoare-style **tool-boundary** pre/postconditions | tools only |
| **FORGE** — 2026 (`arXiv:2602.16708`) | deterministic **policy** reference monitor | policy only, Datalog-specific |
| **relari `agent-contracts`** | **pathconditions** (process constraints) | no LLM-judge / budget layer |
| **`agentcontract/spec`** | hard-by-default + opt-in `judge: llm` | not parameterizable templates |

**Ratify's niche:** a single, dependency-free, strictly-typed Python object that
spans *all* of these scopes, lets each clause choose hard vs. LLM enforcement,
and makes contracts **reusable templates** — a gap none of the above fills on
its own.

## Non-goals

- **Not** a prompt framework or an agent runtime. Ratify observes and gates; it
  never runs your model.
- **Not** a formal verifier. `PROOF` clauses are strict runtime gates, not
  theorem-prover-backed proofs (though you can wire one into a `check`).
- **Not** a safety guarantee for adversarial inputs. A judge is only as good as
  the model behind it; pair fuzzy clauses with hard ones for anything critical.
