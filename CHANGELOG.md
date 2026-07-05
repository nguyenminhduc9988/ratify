# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-07-05

### Added
- Initial public release.
- **Core model**: `Clause`, `Contract`, and the `Scope` × `Enforcement` ×
  `Lifecycle` classification.
- **Parameterizable templates**: `Contract.param` / `bind`, `{param}` criterion
  substitution, and composition via `include` / `+`.
- **Deterministic checks** (`ratify.checks`): text/regex, JSON/schema, tool
  allow/deny, trajectory/pathconditions, and resource checks.
- **LLM-as-judge** abstraction: `Judge` protocol, `KeywordJudge`,
  `CallableJudge`, and provider adapters `judges.OpenAIJudge` /
  `judges.AnthropicJudge`.
- **Probabilistic `(p, δ, k)` satisfaction** for judge clauses.
- **Runtime enforcement**: `Guard`, the `@guard` decorator, and the `guarded`
  context manager (enforce / monitor modes).
- **Resource budgets** with hierarchical conservation and propagating
  consumption.
- **Adapters**: framework-agnostic `wrap`, and a duck-typed LangChain /
  LangGraph callback handler.
- 124 tests, 96% coverage, strict mypy, ruff-clean, CI across Python 3.10–3.13.
