from __future__ import annotations

from doctopus.backends.base import Backend
from doctopus.backends.xberg import XbergBackend
from doctopus.core.errors import BackendUnavailable
from doctopus.core.models import BackendInfo


def _docling():
    from doctopus.backends.docling import DoclingBackend  # lazy: heavy import stays out of Lite
    return DoclingBackend()


def _lazy(module: str, cls: str):
    def make():
        import importlib
        return getattr(importlib.import_module(f"doctopus.backends.{module}"), cls)()
    return make


# order = display order; routing preference lives in routing/router.py
_FACTORIES = {
    "xberg": XbergBackend,
    "docling": _docling,
    "paddleocr": _lazy("paddleocr", "PaddleOCRBackend"),
    "marker": _lazy("sidecar", "MarkerBackend"),
    "mineru": _lazy("sidecar", "MinerUBackend"),
    "ollama": _lazy("ollama", "OllamaBackend"),
    "pymupdf4llm": _lazy("pymupdf4llm", "PyMuPDF4LLMBackend"),
    "markitdown": _lazy("markitdown", "MarkItDownBackend"),
}
_cache: dict[str, Backend] = {}


def get(backend_id: str) -> Backend:
    if backend_id not in _FACTORIES:
        raise BackendUnavailable(f"unknown backend '{backend_id}' (known: {', '.join(_FACTORIES)})")
    if backend_id not in _cache:
        _cache[backend_id] = _FACTORIES[backend_id]()
    return _cache[backend_id]


def list_info() -> list[BackendInfo]:
    return [get(b).info() for b in _FACTORIES]


def available_ids() -> list[str]:
    return [i.id for i in list_info() if i.available]
