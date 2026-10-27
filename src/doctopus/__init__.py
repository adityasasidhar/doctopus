"""Doctopus 🐙 -- many arms, one API.

    import doctopus
    doc = doctopus.parse("paper.pdf")          # -> doctopus.core.models.Document
    print(doc.markdown, doc.processing.decision.reasons)
"""
from __future__ import annotations

__version__ = "0.1.0"


def parse(path, *, backend: str = "auto", mode: str = "balanced", fallback: bool | None = None,
          ocr: bool | None = None):
    """Synchronous convenience wrapper around ``Gateway().parse``."""
    import asyncio

    from doctopus.core.gateway import Gateway

    return asyncio.run(Gateway().parse(path, backend=backend, mode=mode, fallback=fallback, ocr=ocr))


def chunk(path, *, max_chars: int = 1500, backend: str = "auto", mode: str = "balanced"):
    """Parse then split into layout-aware chunks (list of ``doctopus.core.chunk.Chunk``)."""
    from doctopus.core.chunk import chunk as make_chunks

    return make_chunks(parse(path, backend=backend, mode=mode), max_chars=max_chars)


def plan(path, *, backend: str = "auto", mode: str = "balanced"):
    """Routing decision only (no extraction)."""
    from doctopus.core.gateway import Gateway

    return Gateway().plan(path, backend=backend, mode=mode)
