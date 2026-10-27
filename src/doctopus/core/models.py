"""Canonical, versioned output contract. Unknown values stay None -- never fabricated."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"
Mode = Literal["fast", "balanced", "accurate", "manual"]


class Bbox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class Block(BaseModel):
    id: str
    type: str  # heading | paragraph | list_item | code | caption | ...
    text: str
    page: int | None = None
    bbox: Bbox | None = None
    level: int | None = None  # heading level when known
    source: str  # backend that produced it


class Table(BaseModel):
    id: str
    page: int | None = None
    markdown: str
    rows: list[list[str]] | None = None
    bbox: Bbox | None = None
    source: str


class Page(BaseModel):
    page: int
    text: str


class DocMeta(BaseModel):
    document_id: str
    filename: str
    format: str  # extension, lower-case
    mime_type: str | None = None
    page_count: int | None = None
    size_bytes: int
    content_hash: str  # sha256 of the input bytes
    title: str | None = None
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Decision(BaseModel):
    """Why the router chose what it chose -- shown in CLI, API, MCP and the UI."""
    backend: str
    mode: Mode
    reasons: list[str]
    inspection: dict[str, Any] = Field(default_factory=dict)


class Processing(BaseModel):
    backend: str
    backend_version: str | None = None
    mode: Mode
    elapsed_ms: int
    peak_rss_mb: float | None = None
    ocr_used: bool | None = None
    fallback_from: str | None = None
    warnings: list[str] = Field(default_factory=list)
    decision: Decision | None = None


class Document(BaseModel):
    schema_version: str = SCHEMA_VERSION
    meta: DocMeta
    markdown: str
    text: str
    blocks: list[Block] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    pages: list[Page] = Field(default_factory=list)
    processing: Processing


class BackendInfo(BaseModel):
    id: str
    version: str | None = None
    available: bool
    reason_unavailable: str | None = None
    formats: list[str]
    capabilities: dict[str, bool]
    weight: Literal["light", "heavy"]
    ram_mb: int | None = None  # free RAM the router requires before choosing it (measured peak + headroom)
    licence: str | None = None
    runtime: Literal["in-process", "sidecar", "service"] = "in-process"
