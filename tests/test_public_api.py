"""Guard the public API surface: every __all__ name must import."""

from __future__ import annotations

import importlib

import ratify


def test_version() -> None:
    assert isinstance(ratify.__version__, str)
    assert ratify.__version__.count(".") == 2


def test_all_exports_present() -> None:
    for name in ratify.__all__:
        assert hasattr(ratify, name), f"missing export: {name}"


def test_submodules_import() -> None:
    for mod in [
        "ratify.enums",
        "ratify.clause",
        "ratify.contract",
        "ratify.engine",
        "ratify.checks",
        "ratify.judge",
        "ratify.guard",
        "ratify.resources",
        "ratify.trace",
        "ratify.context",
        "ratify.exceptions",
        "ratify.adapters",
        "ratify.adapters.generic",
    ]:
        assert importlib.import_module(mod)
