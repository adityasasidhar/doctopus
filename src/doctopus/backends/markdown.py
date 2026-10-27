"""Markdown -> canonical RawResult, shared by backends whose only output is Markdown
(MarkItDown, PyMuPDF4LLM, Marker, MinerU, Ollama VLMs). Same block taxonomy as the layout
engines, so chunking, tables and the UI behave identically whichever engine ran."""
from __future__ import annotations

import re
from html.parser import HTMLParser

from doctopus.backends.base import RawResult
from doctopus.core.models import Block, Page, Table

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_LIST = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_TABLE_SEP = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_IMAGE = re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$")
_HTML_TABLE = re.compile(r"<table\b.*?</table>", re.I | re.S)


def from_markdown(pages: list[tuple[int | None, str]], *, source: str, **extra) -> RawResult:
    """pages: (page number or None, markdown) in reading order."""
    blocks: list[Block] = []
    tables: list[Table] = []
    pages = [(p, re.sub(r"\n{3,}", "\n\n", _HTML_TABLE.sub(_pipe_table, md))) for p, md in pages]  # MinerU & co. emit HTML tables
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


class _Rows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self.cell: list[str] | None = None
        self.span = 1

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.rows.append([])
        elif tag in ("td", "th"):
            if not self.rows:
                self.rows.append([])
            self.cell, self.span = [], max(1, int(dict(attrs).get("colspan") or 1))
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            text = " ".join("".join(self.cell).split()).replace("|", "\\|")
            self.rows[-1] += [text] + [""] * (self.span - 1)  # pipe tables can't merge: pad the span
            self.cell = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def _pipe_table(m: re.Match) -> str:
    parser = _Rows()
    parser.feed(m.group(0))
    rows = [r for r in parser.rows if r]
    if not rows:
        return m.group(0)
    width = max(map(len, rows))
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(r) + " |" for r in rows]
    return "\n\n" + "\n".join([lines[0], "|" + "---|" * width, *lines[1:]]) + "\n\n"


def _cells(row: str) -> list[str]:
    row = re.sub(r"^\||(?<!\\)\|$", "", row.strip())
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", row)]


def _inline(s: str) -> str:
    return re.sub(r"(\*\*|__|`)", "", s)


def plain(md: str) -> str:
    s = re.sub(r"^#{1,6}\s*", "", md, flags=re.M)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    return re.sub(r"[*_`]{1,3}", "", s)
