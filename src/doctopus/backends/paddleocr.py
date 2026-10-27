"""Optional PP-StructureV3 document parser. Discovery never imports Paddle or loads models."""
from __future__ import annotations

import asyncio
import mimetypes
import os
import re
import threading
from html.parser import HTMLParser
from importlib import metadata, util
from pathlib import Path

from doctopus.backends.base import RawResult, pkg_licence
from doctopus.core.errors import BackendUnavailable, ExtractionFailed, InputRejected, UnsupportedFormat
from doctopus.core.models import BackendInfo, Bbox, Block, Page, Table

FORMATS = ["pdf", "png", "jpg", "jpeg", "bmp", "tif", "tiff"]
INSTALL = 'pip install "doctopus-ai[paddleocr]"'
_LABELS = {
    "doc_title": "heading", "paragraph_title": "heading", "abstract_title": "heading",
    "reference_title": "heading", "content_title": "heading", "text": "paragraph",
    "abstract": "paragraph", "header": "page_header", "footer": "page_footer",
    "number": "page_footer", "figure_title": "caption", "table_title": "caption",
    "chart_title": "caption", "figure_table_title": "caption", "vision_footnote": "footnote",
    "algorithm": "code",
}


class PaddleOCRBackend:
    id = "paddleocr"

    def __init__(self):
        self._pipeline = None
        self._lock = threading.Lock()  # usable across event loops; protects initialization and inference

    def info(self) -> BackendInfo:
        missing = [name for name in ("paddleocr", "paddle", "paddlex") if util.find_spec(name) is None]
        try:
            version = metadata.version("paddleocr")
        except metadata.PackageNotFoundError:
            version = None
        compatible = version is not None and version.split(".")[0] == "3"
        reason = f"missing {', '.join(missing)}; run {INSTALL}" if missing else (
            None if compatible else f"PP-StructureV3 requires PaddleOCR 3.x; run {INSTALL}"
        )
        return BackendInfo(
            id=self.id, version=version, available=reason is None, reason_unavailable=reason,
            formats=FORMATS, weight="heavy", ram_mb=3500,  # measured peak ~2.8 GB RSS with the mobile model set
            licence=pkg_licence("paddleocr") if version else None,
            capabilities={"ocr": True, "tables": True, "layout_model": True, "office": False, "bbox": True},
        )

    def supports(self, ext: str) -> bool:
        return ext.lower().lstrip(".") in FORMATS

    async def process(self, path: Path, *, ocr: bool | None = None) -> RawResult:
        if not self.supports(path.suffix):
            raise UnsupportedFormat(f"paddleocr: unsupported format {path.suffix}")
        if ocr is False:
            raise InputRejected("paddleocr: PP-StructureV3 requires OCR; omit ocr=False or select another backend")
        try:
            return await asyncio.to_thread(self._process, path)
        except (BackendUnavailable, ExtractionFailed):
            raise
        except Exception as e:
            raise ExtractionFailed(f"paddleocr: {type(e).__name__}: {e}") from e

    def _process(self, path: Path) -> RawResult:
        with self._lock:
            if self._pipeline is None:
                info = self.info()
                if not info.available:
                    raise BackendUnavailable(f"paddleocr: {info.reason_unavailable}")
                try:
                    from paddleocr import PPStructureV3
                    formulas = os.environ.get("DOCTOPUS_PADDLE_FORMULAS") == "1"
                    self._pipeline = PPStructureV3(
                        device="cpu", use_doc_orientation_classify=False, use_doc_unwarping=False,
                        use_textline_orientation=False, use_table_recognition=True,
                        use_formula_recognition=formulas, format_block_content=False,
                        # oneDNN in paddlepaddle 3.3 fails with "ConvertPirAttribute2RuntimeAttribute not support"
                        enable_mkldnn=os.environ.get("DOCTOPUS_PADDLE_MKLDNN") == "1",
                        # the default server OCR models + formula/seal/chart heads peaked >10 GB and got OOM-killed
                        # on a 1-page PDF; the mobile set with them off peaks ~2.9 GB
                        use_seal_recognition=False, use_chart_recognition=False,
                        text_detection_model_name=os.environ.get("DOCTOPUS_PADDLE_DET", "PP-OCRv5_mobile_det"),
                        text_recognition_model_name=os.environ.get("DOCTOPUS_PADDLE_REC", "PP-OCRv5_mobile_rec"),
                    )
                except ImportError as e:
                    raise BackendUnavailable(f"paddleocr: {e}; install document-parsing dependencies with {INSTALL}") from e
            # Some PaddleOCR versions return a generator; consume it entirely in this worker.
            return self._normalise(self._pipeline.predict(input=str(path)), path)

    def _normalise(self, results, path: Path) -> RawResult:
        blocks: list[Block] = []
        tables: list[Table] = []
        pages: list[Page] = []
        markdown_pages: list[str] = []
        warnings: list[str] = []
        title = None
        reported_count = None
        for position, result in enumerate(results):
            # Public JSON representation turns Paddle's LayoutBlock objects into dictionaries.
            data = result.json["res"]
            index = data.get("page_index")
            page_number = int(index) + 1 if index is not None else position + 1
            reported_count = data.get("page_count") or reported_count
            page_text: list[str] = []
            page_markdown: list[str] = []
            for ordinal, item in enumerate(data.get("parsing_res_list", [])):
                content = (item.get("block_content") or "").strip()
                if not content:
                    continue
                label = item.get("block_label") or "text"
                text = _plain_text(content)
                bbox = _bbox(item.get("block_bbox"))
                bid = f"paddle-p{page_number}-b{ordinal}"
                level = 1 if label == "doc_title" else 2 if _LABELS.get(label) == "heading" else None
                if title is None and label == "doc_title":
                    title = text
                blocks.append(Block(id=bid, type=_LABELS.get(label, label), text=text,
                                    page=page_number, bbox=bbox, level=level, source=self.id))
                if label == "table":
                    tables.append(Table(id=bid, page=page_number,
                                        markdown=content, bbox=bbox, source=self.id))
                page_text.append(text)
                page_markdown.append(f"{'#' * level} {content}" if level else content)
            md = result.markdown
            markdown_pages.append(md.get("markdown_texts") or "\n\n".join(page_markdown))
            if md.get("markdown_images") and not warnings:
                warnings.append("paddleocr: extracted image assets are not exported; Markdown image links may be unresolved")
            pages.append(Page(page=page_number, text="\n\n".join(page_text)))
        if not pages:
            raise ExtractionFailed("paddleocr: prediction returned no pages")
        return RawResult(
            markdown="\n\n".join(md for md in markdown_pages if md),
            text="\n\n".join(p.text for p in pages if p.text), blocks=blocks, tables=tables, pages=pages,
            page_count=reported_count or len(pages), title=title,
            mime_type=mimetypes.guess_type(path.name)[0], ocr_used=True, warnings=warnings,
        )


def _bbox(value) -> Bbox | None:
    try:
        x0, y0, x1, y1 = value
        return Bbox(x0=float(x0), y0=float(y0), x1=float(x1), y1=float(y1))
    except (TypeError, ValueError):
        return None


class _HTMLText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {"br", "p", "div", "tr", "td", "th"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"p", "div", "tr", "td", "th"}:
            self.parts.append(" ")


def _plain_text(content: str) -> str:
    if not re.search(r"</?(?:table|tr|td|th|div|p|span|br)\b", content, flags=re.I):
        return content
    parser = _HTMLText()
    parser.feed(content)
    parser.close()
    return " ".join("".join(parser.parts).split())
