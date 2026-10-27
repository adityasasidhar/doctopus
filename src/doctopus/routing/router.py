"""Deterministic, explainable routing. Every decision carries human-readable reasons.

Policy (derived from measurements on this repo's fixtures, see bench/):
  * Xberg is the default: ~0.1-0.4 s, built-in OCR, tables, typed blocks with page+bbox.
  * Heavy engines (layout models, VLMs) are 20-150x slower and need GBs of RAM, so they are used when
    asked for (accurate / manual), or as the one bounded escalation when the light result looks wrong --
    and only if they support the format and fit in free memory. Which heavy engine goes first is
    DOCTOPUS_HEAVY_ORDER (default below).
"""
from __future__ import annotations

import os

from doctopus.core.models import BackendInfo, Decision, Mode
from doctopus.core.errors import BackendUnavailable

HEAVY_ORDER = [b.strip() for b in os.environ.get("DOCTOPUS_HEAVY_ORDER", "docling,marker,mineru,ollama").split(",")]


def fits(b: BackendInfo, info: dict) -> tuple[bool, str]:
    if b.id == "paddleocr":
        return False, "paddleocr requires explicit selection until benchmarked"
    free = info.get("mem_available_mb")
    if b.ram_mb and free is not None and free < b.ram_mb:
        return False, f"{b.id} needs ~{b.ram_mb / 1000:.0f} GB RAM but only {free / 1000:.1f} GB is free"
    return True, ""


def _handles(b: BackendInfo, info: dict) -> bool:
    return b.available and (not info.get("ext") or info["ext"] in b.formats)


def heavy_candidates(backends: list[BackendInfo], info: dict) -> list[BackendInfo]:
    rank = {k: i for i, k in enumerate(HEAVY_ORDER)}
    heavy = [b for b in backends if b.id != "paddleocr" and b.weight == "heavy" and _handles(b, info)]
    return sorted(heavy, key=lambda b: rank.get(b.id, len(rank)))


def escalation_target(current: str, backends: list[BackendInfo], info: dict) -> str | None:
    """The single alternative to try: light result looked wrong -> best heavy engine that fits;
    heavy engine failed -> the light default."""
    cur = next((b for b in backends if b.id == current), None)
    if cur is not None and cur.weight == "heavy":
        light = [b for b in backends if b.weight == "light" and b.id != current and _handles(b, info)]
        return next((b.id for b in light if b.id == "xberg"), light[0].id if light else None)
    return next((b.id for b in heavy_candidates(backends, info) if b.id != current and fits(b, info)[0]), None)


def decide(info: dict, *, mode: Mode, backends: list[BackendInfo], preferred: str | None = None,
           preferred_by: str = "user selected") -> Decision:
    r: list[str] = []

    def done(backend: str) -> Decision:
        r.append(f"→ {backend}")
        return Decision(backend=backend, mode=mode, reasons=r, inspection=info)

    if mode == "manual" and preferred:
        r.append(f"manual: {preferred_by} {preferred}")
        return done(preferred)
    available = [b for b in backends if b.available]
    if any(b.id == "paddleocr" for b in available):
        available = [b for b in available if b.id != "paddleocr"]
        r.append("paddleocr is opt-in: select it explicitly with backend='paddleocr'")
        if not available:
            raise BackendUnavailable("no backend available for automatic routing; select paddleocr explicitly")
    if not available:
        r.append("no backend installed")
        return done("xberg")

    pages = info.get("pages")
    r.append(f"{info.get('ext')} · {pages} pages · {info.get('size_kb')} KB" if pages
             else f"{info.get('ext')} · {info.get('size_kb')} KB")

    if mode == "accurate":
        skipped = []
        for b in heavy_candidates(available, info):
            ok, why = fits(b, info)
            if ok:
                r.append(f"mode=accurate: heavy engine {b.id} requested" + (f" ({'; '.join(skipped)})" if skipped else ""))
                return done(b.id)
            skipped.append(why)
        r.append("mode=accurate wanted a heavy engine, but " + ("; ".join(skipped) or f"none installed handles .{info.get('ext')}"))
    elif mode == "fast":
        r.append("mode=fast: light engine only, no escalation")
    else:
        r.append("light engine first (built-in OCR, tables, bbox); escalates only if output looks wrong")
    light = [b for b in available if b.weight == "light" and _handles(b, info)]
    pick = next((b.id for b in light if b.id == "xberg"), light[0].id if light else available[0].id)
    return done(pick)
