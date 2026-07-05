"""Framework adapters.

The *generic* adapter (:mod:`ratify.adapters.generic`) works with any agent
that is, or can be wrapped as, a callable. Framework-specific adapters live in
sibling modules and import their framework lazily, so ``ratify`` itself keeps
zero required dependencies.
"""

from __future__ import annotations

from ratify.adapters.generic import RatifiedAgent, wrap

__all__ = ["RatifiedAgent", "wrap"]
