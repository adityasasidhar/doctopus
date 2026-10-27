"""Near-free document probe: extension, size, page count. (A pypdf text-layer/table probe was
measured at 330-430 ms -- as slow as a full Xberg run -- and its table signal didn't separate
documents, so it was removed.)"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def inspect_file(path: Path) -> dict[str, Any]:
    ext = path.suffix.lower().lstrip(".")
    info: dict[str, Any] = {"ext": ext, "size_kb": round(path.stat().st_size / 1024, 1)}
    info["kind"] = "pdf" if ext == "pdf" else "image" if ext in {"png", "jpg", "jpeg", "tiff", "bmp"} else "office_or_text"
    if ext == "pdf":
        try:
            import xberg
            info["pages"] = xberg.pdf_page_count(path.read_bytes())
        except Exception:
            pass
    info["mem_available_mb"] = mem_available_mb()
    return info


def mem_available_mb() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return None  # non-Linux: unknown, treated as "enough"
