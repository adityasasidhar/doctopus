"""MarkItDown (Microsoft): pure-Python Office/HTML/spreadsheet -> Markdown. Light, MIT.
No OCR and no layout model: weak on PDFs, strong breadth on office formats."""
from __future__ import annotations

import asyncio
from importlib import metadata, util
from pathlib import Path

from doctopus.backends.base import RawResult, pkg_licence
from doctopus.backends.markdown import from_markdown
from doctopus.core.errors import BackendUnavailable, ExtractionFailed
from doctopus.core.models import BackendInfo

FORMATS = ["docx", "pptx", "xlsx", "xls", "html", "htm", "csv", "json", "xml", "epub", "msg", "pdf", "txt", "md"]


class MarkItDownBackend:
    id = "markitdown"
    _md = None

    def info(self) -> BackendInfo:
        ok = util.find_spec("markitdown") is not None
        try:
            ver = metadata.version("markitdown")
        except metadata.PackageNotFoundError:
            ver = None
        return BackendInfo(
            id=self.id, version=ver, available=ok, reason_unavailable=None if ok else "uv sync --extra markitdown",
            formats=FORMATS, capabilities={"ocr": False, "tables": True, "layout_model": False, "office": True,
                                           "bbox": False},
            weight="light", licence=pkg_licence("markitdown"),
        )

    def supports(self, ext: str) -> bool:
        return ext.lower().lstrip(".") in FORMATS

    async def process(self, path: Path, *, ocr: bool | None = None) -> RawResult:
        if MarkItDownBackend._md is None:
            try:
                from markitdown import MarkItDown
            except ImportError as e:
                raise BackendUnavailable(f"markitdown not installed: {e}") from e
            MarkItDownBackend._md = MarkItDown(enable_plugins=False)  # no third-party plugins, no LLM calls
        try:
            r = await asyncio.to_thread(MarkItDownBackend._md.convert, str(path))
        except Exception as e:
            raise ExtractionFailed(f"markitdown: {e}") from e
        warnings = ["markitdown does no OCR; scanned pages yield no text"] if ocr else []
        return from_markdown([(None, r.markdown or "")], source=self.id, title=r.title or None,
                             ocr_used=False, warnings=warnings)
