"""Deterministic, explainable routing. Every decision carries human-readable reasons.

Policy (derived from measurements on this repo's fixtures, see bench/):
  * Xberg is the default: ~0.1-0.4 s, built-in OCR, tables, typed blocks with page+bbox.
  * Docling is ~50-100x slower and needs ~3.2 GB RAM, so it is used when asked for (accurate / manual),
    or as the one bounded escalation when the light result looks wrong -- and only if it fits in memory.
"""
from __future__ import annotations

from doctopus.core.models import Decision, Mode

DOCLING_NEEDS_MB = 4000  # measured peak RSS ~3.2 GB + headroom


def fits(backend: str, info: dict) -> tuple[bool, str]:
    if backend != "docling":
        return True, ""
    free = info.get("mem_available_mb")
    if free is not None and free < DOCLING_NEEDS_MB:
        return False, f"docling needs ~{DOCLING_NEEDS_MB // 1000} GB RAM but only {free / 1000:.1f} GB is free"
    return True, ""


def decide(info: dict, *, mode: Mode, available: list[str], preferred: str | None = None) -> Decision:
    r: list[str] = []

    def done(backend: str) -> Decision:
        r.append(f"→ {backend}")
        return Decision(backend=backend, mode=mode, reasons=r, inspection=info)

    if mode == "manual" and preferred:
        r.append(f"manual: user selected {preferred}")
        return done(preferred)
    if not available:
        r.append("no backend installed")
        return done("xberg")

    pages = info.get("pages")
    if pages:
        r.append(f"{info.get('ext')} · {pages} pages · {info.get('size_kb')} KB")
    else:
        r.append(f"{info.get('ext')} · {info.get('size_kb')} KB")

    if mode == "accurate" and "docling" in available:
        ok, why = fits("docling", info)
        if ok:
            r.append("mode=accurate: layout-model engine requested")
            return done("docling")
        r.append(f"mode=accurate wanted docling, but {why}")
    elif mode == "fast":
        r.append("mode=fast: light engine only, no escalation")
    else:
        r.append("light engine first (built-in OCR, tables, bbox); escalates only if output looks wrong")
    return done("xberg" if "xberg" in available else available[0])
