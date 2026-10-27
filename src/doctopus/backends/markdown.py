"""Markdown -> canonical RawResult, shared by backends whose only output is Markdown
(MarkItDown, PyMuPDF4LLM, Marker, MinerU, Ollama VLMs). Same block taxonomy as the layout
engines, so chunking, tables and the UI behave identically whichever engine ran."""
from __future__ import annotations

import re

from doctopus.backends.base import RawResult
from doctopus.core.models import Block, Page, Table

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_LIST = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_TABLE_SEP = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_IMAGE = re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$")


def from_markdown(pages: list[tuple[int | None, str]], *, source: str, **extra) -> RawResult:
    """pages: (page number or None, markdown) in reading order."""
    blocks: list[Block] = []
    tables: list[Table] = []
    for page, md in pages:
        _parse(md, page, source, blocks, tables)
    numbered = [(p, md) for p, md in pages if p is not None]
    full = "\n\n".join(md.strip() for _, md in pages if md.strip())
    return RawResult(
        markdown=full, text=plain(full), blocks=blocks, tables=tables,
        pages=[Page(page=p, text=plain(md)) for p, md in numbered],
        page_count=extra.pop("page_count", None) or (len(numbered) or None), **extra,
    )


def _parse(md: str, page, source, blocks, tables):
    lines = md.splitlines()
    para: list[str] = []
    i = 0

    def add(type_, text, level=None):
        blocks.append(Block(id=f"{source[0]}{len(blocks)}", type=type_, text=text, page=page,
                            level=level, source=source))

    def end_para():
        if para:
            add("paragraph", "\n".join(para).strip())
            para.clear()

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s or _IMAGE.match(s):
            end_para()
        elif s.startswith("```"):
            end_para()
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            if code := "\n".join(lines[i + 1:j]).strip():
                add("code", code)
            i = j
        elif m := _HEADING.match(s):
            end_para()
            add("heading", _inline(m.group(2)), level=len(m.group(1)))
        elif s.startswith("|") and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1].strip()):
            end_para()
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            rows = [_cells(r) for k, r in enumerate(lines[i:j]) if k != 1]
            tables.append(Table(id=f"t{len(tables)}", page=page, markdown="\n".join(lines[i:j]).strip(),
                                rows=rows, source=source))
            i = j - 1
        elif m := _LIST.match(line):
            end_para()
            add("list_item", _inline(m.group(1)))
        else:
            para.append(_inline(s))
        i += 1
    end_para()


def _cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _inline(s: str) -> str:
    return re.sub(r"(\*\*|__|`)", "", s)


def plain(md: str) -> str:
    s = re.sub(r"^#{1,6}\s*", "", md, flags=re.M)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    return re.sub(r"[*_`]{1,3}", "", s)
