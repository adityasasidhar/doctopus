"""Layout-aware chunking for RAG and dataset export. A pure function over the canonical Document.

Rules: a heading closes the current chunk and becomes context (heading_path) for the next ones;
text blocks are packed up to max_chars and over-long ones split at sentence boundaries; tables are
always whole chunks placed in page order; page headers/footers are dropped. Chunk ids are
deterministic (content hash + ordinal), so re-running over the same file gives the same ids.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from doctopus.core.models import SCHEMA_VERSION, Document

MAX_CHARS = 1500
SKIP_TYPES = {"page_header", "page_footer"}
_SENT = re.compile(r"(?<=[.!?])\s+")
_PARA = re.compile(r"\n\s*\n")


class ChunkSource(BaseModel):
    filename: str
    document_id: str
    content_hash: str
    backend: str
    schema_version: str = SCHEMA_VERSION


class Chunk(BaseModel):
    id: str
    kind: Literal["text", "table"]
    text: str
    n_chars: int
    heading_path: list[str]
    pages: list[int]
    block_ids: list[str] = Field(default_factory=list)
    table_id: str | None = None
    source: ChunkSource


def chunk(doc: Document, *, max_chars: int = MAX_CHARS) -> list[Chunk]:
    src = ChunkSource(filename=doc.meta.filename, document_id=doc.meta.document_id,
                      content_hash=doc.meta.content_hash, backend=doc.processing.backend)
    out: list[Chunk] = []
    path: list[tuple[int, str]] = []  # (heading level, title)
    buf: list[tuple[str, int | None, str | None]] = []  # (text, page, block id)
    tables = sorted(doc.tables, key=lambda t: (t.page is None, t.page or 0))

    def emit(kind, text, pages, block_ids=(), table_id=None):
        out.append(Chunk(id=f"{doc.meta.content_hash[:12]}-{len(out):04d}", kind=kind, text=text,
                         n_chars=len(text), heading_path=[t for _, t in path],
                         pages=sorted({p for p in pages if p is not None}),
                         block_ids=list(dict.fromkeys(i for i in block_ids if i)), table_id=table_id, source=src))

    def flush():
        if buf:
            emit("text", "\n\n".join(t for t, _, _ in buf), [p for _, p, _ in buf], [i for _, _, i in buf])
            buf.clear()

    def tables_before(page):
        while tables and tables[0].page is not None and (page is None or tables[0].page < page):
            flush()
            t = tables.pop(0)
            emit("table", t.markdown.strip(), [t.page], table_id=t.id)

    def add(text, page, bid):
        tables_before(page)
        for piece in _split(text, max_chars):
            size = sum(len(t) for t, _, _ in buf) + 2 * len(buf)  # length once joined with "\n\n"
            if buf and size + len(piece) > max_chars:
                flush()
            buf.append((piece, page, bid))

    blocks = [b for b in doc.blocks if b.type not in SKIP_TYPES and b.text.strip()]
    if blocks:
        for b in blocks:
            if b.type == "heading":
                tables_before(b.page)
                flush()
                level = b.level or 1
                while path and path[-1][0] >= level:
                    path.pop()
                path.append((level, b.text.strip()))
            else:
                add(b.text.strip(), b.page, b.id)
    else:  # engine gave no layout blocks: fall back to per-page paragraphs, then plain text
        units = [(p.text, p.page) for p in doc.pages] or [(doc.text, None)]
        in_tables = [_norm(t.markdown) for t in doc.tables]
        for text, page in units:
            for para in _PARA.split(text):
                # page text repeats table content; it is already emitted as a table chunk
                if para.strip() and not any(_norm(para) in t for t in in_tables):
                    add(para.strip(), page, None)
    tables_before(None)
    flush()
    for t in tables:  # tables with unknown page go last
        emit("table", t.markdown.strip(), [], table_id=t.id)
    return out


def _norm(s: str) -> str:
    return " ".join(s.split())


def _split(text: str, limit: int) -> list[str]:
    """Split at sentence boundaries, then at spaces, so no piece exceeds limit."""
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    for s in _SENT.split(text):
        while len(s) > limit:
            cut = s.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            parts.append(s[:cut])
            s = s[cut:].lstrip()
        parts.append(s)
    out, cur = [], ""
    for s in parts:
        if cur and len(cur) + 1 + len(s) > limit:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}" if cur else s
    return out + ([cur] if cur else [])
