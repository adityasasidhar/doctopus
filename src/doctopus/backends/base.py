from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from doctopus.core.models import BackendInfo, Block, Page, Table


@dataclass
class RawResult:
    """What an adapter returns; the Gateway wraps it into a canonical Document."""
    markdown: str
    text: str
    blocks: list[Block] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    pages: list[Page] = field(default_factory=list)
    page_count: int | None = None
    title: str | None = None
    mime_type: str | None = None
    ocr_used: bool | None = None
    quality: float | None = None
    warnings: list[str] = field(default_factory=list)


class Backend(Protocol):
    id: str

    def info(self) -> BackendInfo: ...

    def supports(self, ext: str) -> bool: ...

    async def process(self, path: Path, *, ocr: bool | None = None) -> RawResult: ...
