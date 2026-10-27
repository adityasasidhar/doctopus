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


def pkg_licence(dist: str) -> str | None:
    """Licence as declared in the installed package's metadata (None if not installed / not declared)."""
    from importlib import metadata

    try:
        m = metadata.metadata(dist)
    except metadata.PackageNotFoundError:
        return None
    lic = m.get("License-Expression")
    if not lic:  # legacy field often holds the whole licence text; keep it only if it is a short name
        first = (m.get("License") or "").strip().splitlines()[:1]
        lic = first[0] if first and len(first[0]) < 40 else None
    if not lic:
        lic = next((c.rsplit("::", 1)[-1].strip() for c in m.get_all("Classifier") or [] if c.startswith("License ::")), None)
    return lic


class Backend(Protocol):
    id: str

    def info(self) -> BackendInfo: ...

    def supports(self, ext: str) -> bool: ...

    async def process(self, path: Path, *, ocr: bool | None = None) -> RawResult: ...
