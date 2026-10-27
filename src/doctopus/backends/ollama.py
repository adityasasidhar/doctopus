"""Local vision-language model via Ollama: page images -> Markdown. Fully offline once the model is pulled.

Slow on small GPUs, but it reads what text layers and OCR miss (handwriting, photos of pages, odd layouts).
Model and host are configurable: DOCTOPUS_OLLAMA_MODEL, OLLAMA_HOST.
"""
from __future__ import annotations

import io
import json
import os
import re
import time
import urllib.request
from importlib import metadata, util
from pathlib import Path

from doctopus.backends.base import RawResult
from doctopus.backends.markdown import from_markdown
from doctopus.core.errors import BackendUnavailable, ExtractionFailed
from doctopus.core.models import BackendInfo

FORMATS = ["pdf", "png", "jpg", "jpeg", "tiff", "webp"]
PROMPT = ("Transcribe this document page into Markdown. Keep headings, paragraphs, lists and tables "
          "(as Markdown pipe tables) in reading order. Output only the Markdown, with no commentary.")
_FENCE = re.compile(r"^\s*```(?:markdown|md)?\s*$", re.M)  # small VLMs wrap pages (or parts) in fences
# bounded decode: 2B VLMs can loop on a page; cap it and nudge them off repeats
OPTIONS = {"temperature": 0, "repeat_penalty": 1.1, "num_predict": int(os.environ.get("DOCTOPUS_OLLAMA_MAX_TOKENS", "3000"))}


class OllamaBackend:
    id = "ollama"
    _probe: tuple[float, bool, str | None] = (0.0, False, None)

    def __init__(self):
        self.model = os.environ.get("DOCTOPUS_OLLAMA_MODEL", "qwen3-vl:2b-instruct")  # thinking tags ignore think=False
        self.host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        self.max_pages = int(os.environ.get("DOCTOPUS_OLLAMA_MAX_PAGES", "30"))
        # how long the model stays in (V)RAM after a request; short values free a small GPU for Marker/Docling
        self.keep_alive = os.environ.get("DOCTOPUS_OLLAMA_KEEP_ALIVE")  # None = server default (5m)

    def _status(self) -> tuple[bool, str | None]:
        """Server reachable and model pulled? Cached for 10 s so routing stays cheap."""
        ts, ok, why = OllamaBackend._probe
        if time.monotonic() - ts < 10:
            return ok, why
        if util.find_spec("ollama") is None or util.find_spec("pypdfium2") is None:
            ok, why = False, "uv sync --extra ollama"
        else:
            try:
                with urllib.request.urlopen(f"{self.host}/api/tags", timeout=0.5) as r:
                    names = {m["name"] for m in json.load(r).get("models", [])}
                ok = self.model in names or f"{self.model}:latest" in names
                why = None if ok else f"ollama pull {self.model}"
            except Exception:
                ok, why = False, f"ollama server not reachable at {self.host}"
        OllamaBackend._probe = (time.monotonic(), ok, why)
        return ok, why

    def info(self) -> BackendInfo:
        ok, why = self._status()
        try:
            ver = metadata.version("ollama")
        except metadata.PackageNotFoundError:
            ver = None
        return BackendInfo(
            id=self.id, version=f"{ver} · {self.model}" if ver else None, available=ok, reason_unavailable=why,
            formats=FORMATS, capabilities={"ocr": True, "tables": True, "layout_model": True, "office": False,
                                           "bbox": False, "vlm": True},
            weight="heavy", ram_mb=None, licence="MIT (client); model licence varies", runtime="service",
        )

    def supports(self, ext: str) -> bool:
        return ext.lower().lstrip(".") in FORMATS

    async def process(self, path: Path, *, ocr: bool | None = None) -> RawResult:
        ok, why = self._status()
        if not ok:
            raise BackendUnavailable(f"ollama: {why}")
        from ollama import AsyncClient

        images, total = _page_images(path, self.max_pages)
        client = AsyncClient(host=self.host)
        pages: list[tuple[int | None, str]] = []
        warnings: list[str] = []
        for n, png in images:
            try:
                r = await client.chat(model=self.model, think=False, options=OPTIONS, keep_alive=self.keep_alive,
                                      messages=[{"role": "user", "content": PROMPT, "images": [png]}])
            except Exception as e:  # one bad page (e.g. "token repeat limit reached") must not sink the document
                warnings.append(f"page {n}: {e}")
                continue
            text = _FENCE.sub("", r.message.content).strip()
            if not text:  # a reasoning model can burn the whole budget thinking and return no answer
                warnings.append(f"page {n}: {self.model} returned no text (done_reason={r.done_reason})")
            elif _degenerate(text):
                warnings.append(f"page {n}: output looks repetitive; the model may have looped")
            pages.append((n, text))
        if not any(text for _, text in pages):
            raise ExtractionFailed(f"ollama: no page produced text ({'; '.join(warnings[:3])})")
        warnings += [f"only the first {self.max_pages} of {total} pages were transcribed"] if total > len(images) else []
        return from_markdown(pages, source=self.id, page_count=total, ocr_used=True, warnings=warnings)


def _degenerate(text: str) -> bool:
    words = re.findall(r"\w+", text)
    return len(words) > 150 and len(set(words)) / len(words) < 0.15


def _page_images(path: Path, max_pages: int) -> tuple[list[tuple[int, bytes]], int]:
    if path.suffix.lower() != ".pdf":
        return [(1, path.read_bytes())], 1
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(path))
    out = []
    for i in range(min(len(pdf), max_pages)):
        buf = io.BytesIO()
        pdf[i].render(scale=2).to_pil().save(buf, format="PNG")  # ~144 dpi: legible, small enough for 2-4B VLMs
        out.append((i + 1, buf.getvalue()))
    return out, len(pdf)
