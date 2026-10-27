"""Xberg (formerly Kreuzberg): Rust-core, CPU-only, fast. The 'light' backend."""
from __future__ import annotations

import json
from importlib import metadata
from pathlib import Path

from doctopus.backends.base import RawResult, pkg_licence
from doctopus.core.errors import BackendUnavailable, ExtractionFailed
from doctopus.core.models import BackendInfo, Bbox, Block, Page, Table

FORMATS = ["pdf", "docx", "pptx", "xlsx", "html", "htm", "md", "txt", "csv", "png", "jpg", "jpeg", "tiff", "epub", "rtf", "eml"]


def _bbox(bb) -> Bbox | None:
    if bb is None:
        return None
    try:
        return Bbox(x0=bb.x0, y0=bb.y0, x1=bb.x1, y1=bb.y1)
    except Exception:
        return None


class XbergBackend:
    id = "xberg"

    def _mod(self):
        try:
            import xberg
            return xberg
        except ImportError as e:  # pragma: no cover
            raise BackendUnavailable(f"xberg not installed: {e}") from e

    def info(self) -> BackendInfo:
        try:
            ver = metadata.version("xberg")
            ok, why = True, None
        except metadata.PackageNotFoundError:
            ver, ok, why = None, False, "pip install xberg"
        return BackendInfo(
            id=self.id, version=ver, available=ok, reason_unavailable=why, formats=FORMATS,
            capabilities={"ocr": True, "tables": True, "layout_model": False, "office": True, "bbox": True},
            weight="light", ram_mb=None, licence=pkg_licence("xberg"),
        )

    def supports(self, ext: str) -> bool:
        return ext.lower().lstrip(".") in FORMATS

    async def process(self, path: Path, *, ocr: bool | None = None) -> RawResult:
        x = self._mod()
        cfg = x.ExtractionConfig(
            output_format="markdown", use_cache=False, include_document_structure=True,
            pages=x.PageConfig(extract_pages=True), force_ocr=bool(ocr),
        )
        try:
            res = await x.extract(x.ExtractInput(uri=str(path)), cfg)
        except Exception as e:
            raise ExtractionFailed(f"xberg: {e}") from e
        if res.errors:
            raise ExtractionFailed(f"xberg: {res.errors[0]}")
        d = res.results[0]

        blocks: list[Block] = []
        if d.document is not None:
            for n in d.document.nodes:
                try:
                    c = json.loads(str(n.content))
                except Exception:
                    continue
                t = c.get("node_type")
                txt = c.get("text")
                if t in (None, "group") or not txt:
                    continue
                blocks.append(Block(
                    id=n.id, type=t, text=txt, page=n.page, bbox=_bbox(n.bbox),
                    level=c.get("level"), source=self.id,
                ))

        tables = [
            Table(
                id=str(t.table_id) if getattr(t, "table_id", None) is not None else f"t{i}",
                page=t.page_number, markdown=t.markdown,
                rows=[list(map(str, r)) for r in t.cells] if getattr(t, "cells", None) else None,
                bbox=_bbox(getattr(t, "bounding_box", None)), source=self.id,
            )
            for i, t in enumerate(d.tables or [])
        ]
        pages = [Page(page=p.page_number, text=p.content) for p in (d.pages or [])]
        meta = d.metadata
        return RawResult(
            markdown=d.content, text=_plain(d.content), blocks=blocks, tables=tables, pages=pages,
            page_count=len(pages) or None, title=getattr(meta, "title", None),
            mime_type=d.mime_type, ocr_used=getattr(meta, "ocr_used", None),
            quality=d.quality_score if isinstance(d.quality_score, (int, float)) else None,
            warnings=[f"{w.source}: {w.message}" if w.source else w.message
                      for w in (d.processing_warnings or [])],
        )


def _plain(md: str) -> str:
    import re
    s = re.sub(r"^#{1,6}\s*", "", md, flags=re.M)
    return re.sub(r"[*_`]{1,3}", "", s)
