"""Smoke-test that every example script runs without error."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

EXAMPLES = sorted((Path(__file__).parent.parent / "examples").glob("*.py"))


@pytest.mark.parametrize("script", EXAMPLES, ids=lambda p: p.name)
def test_example_runs(script: Path) -> None:
    runpy.run_path(str(script), run_name="__main__")
