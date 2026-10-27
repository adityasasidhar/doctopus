"""PyMuPDF4LLM: MuPDF text layer + (in PyMuPDF 2.x) a small layout model, RapidOCR where text is missing.

Since PyMuPDF 2.0 the 4llm code ships inside `pymupdf` (the `pymupdf4llm` 2.0 wheel is an empty shim);
`import pymupdf4llm` works with both 1.x and 2.x. AGPL-3.0 -- optional extra, never part of the Lite install."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import sys
from importlib import metadata, util
from pathlib import Path

from doctopus.backends.base import RawResult, pkg_licence
from doctopus.backends.markdown import plain
from doctopus.core.errors import BackendUnavailable, ExtractionFailed
from doctopus.core.models import BackendInfo, Bbox, Block, Page, Table

FORMATS = ["pdf", "xps", "epub", "mobi", "fb2", "cbz", "svg"]
_CLASS = {"section-header": "heading", "text": "paragraph", "list-item": "list_item", "caption": "caption",
          "footnote": "footnote", "formula": "formula", "page-header": "page_header", "page-footer": "page_footer"}


class PyMuPDF4LLMBackend:
    id = "pymupdf4llm"

    def info(self) -> BackendInfo:
        ok = util.find_spec("pymupdf4llm") is not None
        try:
            ver = f"pymupdf {metadata.version('pymupdf')}"
        except metadata.PackageNotFoundError:
            ver = None
        return BackendInfo(
            id=self.id, version=ver, available=ok, reason_unavailable=None if ok else 'pip install "doctopus-ai[pymupdf4llm]"',
            formats=FORMATS, capabilities={"ocr": True, "tables": True, "layout_model": True, "office": False,
                                           "bbox": True},
            weight="light", licence=pkg_licence("pymupdf") or "AGPL-3.0",
        )

    def supports(self, ext: str) -> bool:
        return ext.lower().lstrip(".") in FORMATS

    async def process(self, path: Path, *, ocr: bool | None = None) -> RawResult:
        try:
            import pymupdf
            with contextlib.redirect_stdout(sys.stderr):  # 2.x OCR modules print() at import time
                import pymupdf4llm
                with contextlib.suppress(ImportError):
                    import pymupdf4llm.ocr.rapidocr_api  # noqa: F401
        except ImportError as e:
            raise BackendUnavailable(f"pymupdf4llm not installed: {e}") from e
        # its parser prints progress to stdout, which would corrupt CLI output and the MCP stdio stream
        pymupdf.set_messages(pylogging=True, pylogging_name="pymupdf")
        logging.getLogger("pymupdf").setLevel(logging.WARNING)
        try:
            chunks = await asyncio.to_thread(pymupdf4llm.to_markdown, str(path), page_chunks=True)
        except Exception as e:
            raise ExtractionFailed(f"pymupdf4llm: {e}") from e
        return _normalise(chunks, self.id)


def _normalise(chunks: list[dict], source: str) -> RawResult:
    blocks: list[Block] = []
    tables: list[Table] = []
    pages: list[Page] = []
    for c in chunks:
        n, text = c["metadata"].get("page_number"), c["text"]
        pages.append(Page(page=n, text=plain(text)))
        for box in c.get("page_boxes") or []:
            s, e = box.get("pos") or (0, 0)
            frag = text[s:e].strip()
            bbox = Bbox(x0=box["bbox"][0], y0=box["bbox"][1], x1=box["bbox"][2], y1=box["bbox"][3])
            if not frag:
                continue
            if box["class"] == "table":
                tables.append(Table(id=f"t{len(tables)}", page=n, markdown=frag, bbox=bbox, source=source,
                                    rows=[[x.strip() for x in r.strip().strip("|").split("|")]
                                          for r in frag.splitlines() if r.strip() and not re.match(r"^\|?[-|: ]+$", r.strip())]))
            elif kind := _CLASS.get(box["class"]):
                level = len(m.group(1)) if kind == "heading" and (m := re.match(r"^(#+)\s", frag)) else None
                blocks.append(Block(id=f"p{len(blocks)}", type=kind, text=re.sub(r"^#+\s*|\*\*", "", frag).strip(),
                                    page=n, bbox=bbox, level=level, source=source))
    md = "\n\n".join(c["text"].strip() for c in chunks)
    meta = chunks[0]["metadata"] if chunks else {}
    return RawResult(markdown=md, text=plain(md), blocks=blocks, tables=tables, pages=pages,
                     page_count=meta.get("page_count") or len(pages) or None, title=meta.get("title") or None)
