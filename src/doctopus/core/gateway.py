from __future__ import annotations

import hashlib
import resource
import time
import uuid
from pathlib import Path

from doctopus.backends import registry
from doctopus.core.errors import DoctopusError, ExtractionFailed, InputRejected, UnsupportedFormat
from doctopus.core.models import Decision, DocMeta, Document, Mode, Processing
from doctopus.routing.inspect import inspect_file
from doctopus.routing.router import decide, fits

MAX_BYTES = 200 * 1024 * 1024


class Gateway:
    """The single entry point. CLI, REST and MCP are thin wrappers around this."""

    def __init__(self, max_bytes: int = MAX_BYTES):
        self.max_bytes = max_bytes

    def list_backends(self):
        return registry.list_info()

    def plan(self, path: str | Path, *, backend: str = "auto", mode: Mode = "balanced") -> Decision:
        """Routing decision only -- nothing is extracted."""
        p = self._check(path)
        eff_mode: Mode = "manual" if backend != "auto" else mode
        return decide(inspect_file(p), mode=eff_mode, available=registry.available_ids(),
                      preferred=None if backend == "auto" else backend)

    async def parse(self, path: str | Path, *, backend: str = "auto", mode: Mode = "balanced",
                    fallback: bool | None = None, ocr: bool | None = None) -> Document:
        p = self._check(path)
        manual = backend != "auto"
        decision = self.plan(p, backend=backend, mode=mode)
        allow_fallback = (not manual) if fallback is None else fallback

        order = [decision.backend]
        if allow_fallback and mode != "fast":
            alt = [b for b in registry.available_ids() if b != decision.backend and fits(b, decision.inspection)[0]]
            order += alt[:1]  # bounded: at most one retry

        errors: list[str] = []
        held = None  # first result that looked wrong; kept in case escalation does no better
        for i, bid in enumerate(order):
            be = registry.get(bid)
            if not be.info().available:
                errors.append(f"{bid}: not available")
                continue
            if not be.supports(p.suffix):
                errors.append(f"{bid}: does not support .{p.suffix.lstrip('.')}")
                continue
            t0 = time.perf_counter()
            try:
                raw = await be.process(p, ocr=ocr)
            except DoctopusError as e:
                errors.append(str(e))
                continue
            except Exception as e:  # adapters must not crash the gateway
                errors.append(f"{bid}: {type(e).__name__}: {e}")
                continue
            warnings = list(raw.warnings)
            elapsed = int((time.perf_counter() - t0) * 1000)
            if i == 0 and len(order) > 1 and (why := _looks_wrong(raw, decision.inspection)):
                errors.append(f"{bid}: {why}")
                held = (raw, be, elapsed)
                continue
            if held and (why := _looks_wrong(raw, decision.inspection)) \
                    and len(raw.text.strip()) <= len(held[0].text.strip()):
                # escalation did not help: never return a worse answer than we already had
                h_raw, h_be, h_ms = held
                return self._wrap(p, h_raw, h_be, decision, mode, h_ms, None,
                                  list(h_raw.warnings) + [f"escalated to {bid} but it did no better ({why}); "
                                                          f"kept {h_be.id} output"])
            fallback_from = order[0] if i > 0 else None
            if fallback_from:
                warnings.append(f"fell back from {fallback_from}: {errors[-1]}")
            return self._wrap(p, raw, be, decision, mode if not manual else "manual",
                              elapsed, fallback_from, warnings)
        if held:  # escalation target failed outright; the suspicious result beats nothing
            h_raw, h_be, h_ms = held
            return self._wrap(p, h_raw, h_be, decision, mode, h_ms, None,
                              list(h_raw.warnings) + [f"escalation failed ({errors[-1]}); kept {h_be.id} output"])
        raise ExtractionFailed("; ".join(errors) or "no backend could process this document")

    # -- internals ---------------------------------------------------------
    def _check(self, path) -> Path:
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            raise InputRejected(f"not a file: {p}")
        if p.stat().st_size > self.max_bytes:
            raise InputRejected(f"file exceeds {self.max_bytes // 1024 // 1024} MB limit")
        if not p.suffix:
            raise UnsupportedFormat("file has no extension")
        return p

    def _wrap(self, p: Path, raw, be, decision, mode, elapsed_ms, fallback_from, warnings) -> Document:
        data = p.read_bytes()
        h = hashlib.sha256(data).hexdigest()
        return Document(
            meta=DocMeta(document_id=f"doc_{h[:12]}_{uuid.uuid4().hex[:6]}", filename=p.name,
                         format=p.suffix.lstrip(".").lower(), mime_type=raw.mime_type,
                         page_count=raw.page_count or decision.inspection.get("pages"),
                         size_bytes=len(data), content_hash=h, title=raw.title),
            markdown=raw.markdown, text=raw.text, blocks=raw.blocks, tables=raw.tables, pages=raw.pages,
            processing=Processing(
                backend=be.id, backend_version=be.info().version, mode=mode, elapsed_ms=elapsed_ms,
                peak_rss_mb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
                ocr_used=raw.ocr_used, fallback_from=fallback_from, warnings=warnings, decision=decision,
            ),
        )


def _looks_wrong(raw, info: dict) -> str | None:
    """Evidence-based escalation triggers; returns a human-readable reason or None."""
    pages = info.get("pages") or 1
    if info.get("kind") in {"pdf", "image"} and len(raw.text.strip()) < 20 * pages:
        return f"output suspiciously small ({len(raw.text.strip())} chars for {pages} page(s))"
    if raw.quality is not None and raw.quality < 0.5:
        return f"engine-reported quality {raw.quality:.2f} < 0.50"
    return None
