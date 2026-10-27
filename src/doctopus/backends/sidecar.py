"""Sidecar backends: engines that run as their own CLI in an isolated `uv tool` environment.

Why: Marker pins pillow<11 and MinerU needs pillow>=11, so they cannot share a venv with each other
(or comfortably with Docling). Running them out of process also means their GBs of RAM are returned
to the OS as soon as a job ends. Install with `uv tool install marker-pdf` / `uv tool install mineru`.
"""
from __future__ import annotations

import asyncio
import os
import re
import shutil
import tempfile
from pathlib import Path

from doctopus.backends.base import RawResult
from doctopus.backends.markdown import from_markdown
from doctopus.core.errors import BackendUnavailable, ExtractionFailed
from doctopus.core.models import BackendInfo

TIMEOUT_S = int(os.environ.get("DOCTOPUS_SIDECAR_TIMEOUT", "900"))


class SidecarBackend:
    id: str
    exe: str
    dist: str  # package name inside the tool env, for version lookup
    formats: list[str]
    ram_mb: int
    licence: str
    install: str
    capabilities: dict[str, bool]

    def missing_models(self) -> str | None:
        """Why the engine can't run offline yet (weights not downloaded), or None. The CLI alone is not enough."""
        return None

    def _unavailable(self) -> str | None:
        return self.install if not shutil.which(self.exe) else self.missing_models()

    def info(self) -> BackendInfo:
        path = shutil.which(self.exe)
        reason = self._unavailable()
        return BackendInfo(
            id=self.id, version=_tool_version(path, self.dist) if path else None, available=reason is None,
            reason_unavailable=reason, formats=self.formats,
            capabilities=self.capabilities, weight="heavy", ram_mb=self.ram_mb, licence=self.licence,
            runtime="sidecar",
        )

    def supports(self, ext: str) -> bool:
        return ext.lower().lstrip(".") in self.formats

    def command(self, src: Path, out: Path, ocr: bool | None) -> list[str]:
        raise NotImplementedError

    def collect(self, out: Path, src: Path) -> RawResult:
        raise NotImplementedError

    async def process(self, path: Path, *, ocr: bool | None = None) -> RawResult:
        if reason := self._unavailable():
            raise BackendUnavailable(f"{self.id}: {reason}")
        with tempfile.TemporaryDirectory(prefix=f"doctopus-{self.id}-") as tmp:
            out = Path(tmp)
            proc = await asyncio.create_subprocess_exec(
                *self.command(path, out, ocr), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                _, err = await asyncio.wait_for(proc.communicate(), TIMEOUT_S)
            except TimeoutError:
                proc.kill()
                raise ExtractionFailed(f"{self.id}: timed out after {TIMEOUT_S} s") from None
            if proc.returncode != 0:
                tail = err.decode(errors="replace").strip().splitlines()[-3:]
                raise ExtractionFailed(f"{self.id}: exit {proc.returncode}: {' | '.join(tail)}")
            return self.collect(out, path)


def _tool_version(exe: str, dist: str) -> str | None:
    """Read the version from the tool env's dist-info -- no need to import torch just to print it."""
    env = Path(exe).resolve().parent.parent
    hits = sorted(env.glob(f"lib/python*/site-packages/{dist.replace('-', '_')}-*.dist-info"))
    return hits[-1].name.split("-")[1].removesuffix(".dist") if hits else None


def _hf_cache() -> Path:
    if os.environ.get("HF_HUB_CACHE"):
        return Path(os.environ["HF_HUB_CACHE"])
    return Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface")) / "hub"


def _single(out: Path, pattern: str) -> Path:
    hits = sorted(out.rglob(pattern))
    if not hits:
        raise ExtractionFailed(f"no {pattern} in sidecar output")
    return hits[0]


class MarkerBackend(SidecarBackend):
    id, exe, dist = "marker", "marker_single", "marker-pdf"
    formats = ["pdf", "png", "jpg", "jpeg", "tiff", "webp"]
    ram_mb = 1500  # measured peak ~0.9 GB RSS in fast mode (layout model on the 4 GB GPU)
    licence = "Apache-2.0 code; model weights modified OpenRAIL-M (commercial limits)"
    install = "uv tool install --python 3.12 marker-pdf"
    capabilities = {"ocr": True, "tables": True, "layout_model": True, "office": False, "bbox": False,
                    "formulas": True}
    _SEP = re.compile(r"\n*\{(\d+)\}-{48}\n*")

    def missing_models(self):
        # fast mode's layout detector; the two small s3 checkpoints it also needs are fetched on first run
        if not any((_hf_cache() / "models--datalab-to--surya_layout2/snapshots").glob("*/rfdetr_layout.pth")):
            return "models not downloaded: hf download datalab-to/surya_layout2"
        return None

    def command(self, src, out, ocr):
        cmd = [self.exe, str(src), "--output_dir", str(out), "--output_format", "markdown", "--paginate_output",
               "--disable_image_extraction", "--disable_tqdm"]
        # marker's own GPU default ("balanced") serves its VLM from a vLLM docker container (needs the nvidia
        # container runtime); "fast" runs CPU layout/table detectors in-process. Opt in with DOCTOPUS_MARKER_MODE.
        cmd += ["--mode", os.environ.get("DOCTOPUS_MARKER_MODE", "fast")]
        return cmd + (["--force_ocr"] if ocr else [])

    def collect(self, out, src):
        md = _single(out, "*.md").read_text(encoding="utf-8")
        parts = self._SEP.split(md)  # ['', '0', page0, '1', page1, ...]
        if len(parts) < 3:
            return from_markdown([(None, md)], source=self.id)
        pages = [(int(parts[i]) + 1, parts[i + 1]) for i in range(1, len(parts) - 1, 2)]
        return from_markdown(pages, source=self.id)


class MinerUBackend(SidecarBackend):
    id, exe, dist = "mineru", "mineru-kit", "mineru"
    formats = ["pdf", "png", "jpg", "jpeg", "docx", "pptx", "xlsx", "html", "epub", "csv"]
    ram_mb = 2000  # measured peak ~1.6 GB RSS, basic tier, onnx backend
    licence = "MinerU Open Source License (Apache-2.0 + conditions)"
    install = "uv tool install --python 3.12 mineru"
    capabilities = {"ocr": True, "tables": True, "layout_model": True, "office": True, "bbox": False,
                    "formulas": True}

    _MODELS = ["Layout/PP-DocLayoutV2/inference.onnx", "MFR/pp_formulanet_plus_m/PP-FormulaNet_plus-M.onnx",
               "OCR/paddleocr/ch_PP-OCRv6_small_rec_infer.onnx", "Table/slanet-plus.onnx"]

    def missing_models(self):
        root = Path(os.environ.get("DOCTOPUS_MINERU_MODELS", Path.home() / ".mineru/models")) / "MinerU-4_models_onnx"
        if not all((root / m).is_file() for m in self._MODELS):
            return "models not downloaded: mineru-kit models download --tier basic --small-backend onnx"
        return None

    def command(self, src, out, ocr):
        tier = os.environ.get("DOCTOPUS_MINERU_TIER", "basic")  # standard/advanced need a local VLM runtime
        # never --remote: documents stay on this machine
        return [self.exe, "parse", str(src), "-o", str(out), "--tier", tier, "--format", "markdown",
                "--ocr-mode", "ocr" if ocr else "auto"]

    def collect(self, out, src):
        return from_markdown([(None, _single(out, "*.md").read_text(encoding="utf-8"))], source=self.id)
