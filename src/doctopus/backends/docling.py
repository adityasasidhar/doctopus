"""Docling: layout-aware, table-structure + OCR models. The 'heavy' backend (optional extra)."""
from __future__ import annotations

import asyncio
import logging
from importlib import metadata, util
from pathlib import Path

from doctopus.backends.base import RawResult, pkg_licence
from doctopus.core.errors import BackendUnavailable, ExtractionFailed
from doctopus.core.models import BackendInfo, Bbox, Block, Page, Table

FORMATS = ["pdf", "docx", "pptx", "xlsx", "html", "md", "png", "jpg", "jpeg", "tiff", "csv"]
_LABEL = {"section_header": "heading", "text": "paragraph", "list_item": "list_item", "caption": "caption",
          "code": "code", "formula": "formula", "footnote": "footnote", "page_header": "page_header",
          "page_footer": "page_footer", "title": "heading"}


class DoclingBackend:
    id = "docling"
    _converter = None

    def info(self) -> BackendInfo:
        # find_spec: report availability without paying the torch import cost
        ok = util.find_spec("docling") is not None
        try:
            ver = metadata.version("docling")
        except metadata.PackageNotFoundError:
            ver = None
        return BackendInfo(
            id=self.id, version=ver, available=ok,
            reason_unavailable=None if ok else "uv sync --extra docling", formats=FORMATS,
            capabilities={"ocr": True, "tables": True, "layout_model": True, "office": True, "bbox": True},
            weight="heavy", ram_mb=4000,  # measured peak RSS ~3.2 GB + headroom
            licence=pkg_licence("docling"),
        )

    def supports(self, ext: str) -> bool:
        return ext.lower().lstrip(".") in FORMATS

    def _get_converter(self):
        if DoclingBackend._converter is None:
            try:
                from docling.document_converter import DocumentConverter
            except ImportError as e:
                raise BackendUnavailable(f"docling not installed: {e}") from e
            logging.getLogger("RapidOCR").setLevel(logging.ERROR)  # per-page "no CUDA" warnings
            DoclingBackend._converter = DocumentConverter()  # models load once, then stay warm
        return DoclingBackend._converter

    async def process(self, path: Path, *, ocr: bool | None = None) -> RawResult:
        try:
            conv = await asyncio.to_thread(self._get_converter)
            res = await asyncio.to_thread(conv.convert, str(path))
        except BackendUnavailable:
            raise
        except Exception as e:
            raise ExtractionFailed(f"docling: {e}") from e
        return self._normalise(res.document)

    def _normalise(self, doc) -> RawResult:
        md = doc.export_to_markdown()
        blocks: list[Block] = []
        for i, t in enumerate(getattr(doc, "texts", [])):
            text = (getattr(t, "text", "") or "").strip()
            if not text:
                continue
            label = getattr(getattr(t, "label", None), "value", str(getattr(t, "label", "text")))
            prov = (getattr(t, "prov", None) or [None])[0]
            blocks.append(Block(
                id=f"d{i}", type=_LABEL.get(label, label), text=text,
                page=getattr(prov, "page_no", None), bbox=_bbox(prov), level=getattr(t, "level", None), source=self.id,
            ))
        tables: list[Table] = []
        for i, t in enumerate(getattr(doc, "tables", [])):
            prov = (getattr(t, "prov", None) or [None])[0]
            rows = None
            try:
                grid = t.data.grid
                rows = [[c.text for c in row] for row in grid]
            except Exception:
                pass
            try:
                tmd = t.export_to_markdown(doc)
            except TypeError:
                tmd = t.export_to_markdown()
            tables.append(Table(id=f"t{i}", page=getattr(prov, "page_no", None), markdown=tmd, rows=rows,
                                bbox=_bbox(prov), source=self.id))
        by_page: dict[int, list[str]] = {}
        for b in blocks:
            if b.page is not None:
                by_page.setdefault(b.page, []).append(b.text)
        pages = [Page(page=p, text="\n".join(v)) for p, v in sorted(by_page.items())]
        n = doc.num_pages() if hasattr(doc, "num_pages") else None
        return RawResult(markdown=md, text=md, blocks=blocks, tables=tables, pages=pages,
                         page_count=n or None, title=getattr(doc, "name", None))


def _bbox(prov) -> Bbox | None:
    bb = getattr(prov, "bbox", None)
    try:
        return Bbox(x0=bb.l, y0=bb.t, x1=bb.r, y1=bb.b) if bb else None
    except Exception:
        return None
