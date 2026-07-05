# Contributing to Ratify

Thanks for your interest! Ratify aims to be small, correct, and dependency-free.

## Development setup

```bash
git clone https://github.com/nguyenminhduc9988/ratify
cd ratify
uv venv && source .venv/bin/activate
uv pip install -e ".[dev,schema]"
```

## Before you open a PR

All four gates must pass — CI enforces them across Python 3.10–3.13:

```bash
ruff check src tests          # lint
ruff format --check src tests # format
mypy                          # strict type-check
pytest --cov=src/ratify       # tests (keep coverage ≥ 85%)
```

## Principles

- **Zero required runtime dependencies.** Optional features (schema, providers)
  go behind extras and lazy imports.
- **Fail closed.** A check that errors, or a judge that's missing, must *fail*
  the clause, never silently pass.
- **Hermetic tests.** No network in the default suite. Use `KeywordJudge` /
  `CallableJudge` and fake clients.
- **Typed and documented.** Public APIs need type hints and docstrings.

## Good first contributions

- New deterministic checks in `ratify/checks.py` (with tests).
- New framework adapters in `ratify/adapters/` (duck-typed where possible).
- New provider judges in `ratify/judges.py`.

By contributing you agree your work is licensed under the project's MIT license.
