# PaddleOCR Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make PaddleOCR PP-StructureV3 available as an optional, explicitly selectable Doctopus backend.

**Architecture:** Implement a lazy Python adapter returning the existing `RawResult`. Expose its backend ID throughout existing interfaces and keep it outside automatic routing until benchmarked.

**Tech Stack:** Python 3.12, PaddleOCR 3.x PPStructureV3, PaddlePaddle CPU, pytest, existing FastAPI/Typer/MCP interfaces.

**Spec:** `docs/superpowers/specs/2026-10-27-paddleocr-design.md`

## Global Constraints

- Public backend ID: `paddleocr`; schema version: `1.0`.
- Keep optional imports lazy and the default installation lightweight.
- Preserve the existing automatic routing policy and one-retry limit.
- Unknown cell grids and confidence remain null.
- All synchronous model execution and prediction iteration run outside the event loop.

## Review Focus

- PaddleOCR installed without a Paddle runtime: discovery must explain the missing dependency without importing either engine.
- A PDF with repeated block IDs across pages: normalized block and table IDs must remain unique.
- Table-only pages: text and table outputs must survive without duplicate table chunks.
- Generator failure midway through prediction: surface a processing error, not silent partial success.
- Concurrent requests: initialize once and serialize access to the shared pipeline.

### Task 1: Adapter and optional installation

**Files:** Create `src/doctopus/backends/paddleocr.py` and `tests/test_paddleocr.py`; modify `pyproject.toml`, `uv.lock`, and `src/doctopus/backends/registry.py`.

**Interfaces:** Implement `PaddleOCRBackend.info() -> BackendInfo`, `supports(ext: str) -> bool`, and `async process(path: Path, *, ocr: bool | None = None) -> RawResult`.

- [x] Write tests for discovery without imports, absent/incomplete installations, case-insensitive input extensions, explicit OCR disabling, pipeline reuse/concurrency, and worker-thread execution.
- [x] Add representative page results covering headings, text, formulas, headers/footers, HTML tables, PDF/image pagination, repeated IDs, empty pages, and a failing prediction iterator. Assert normalized content and table chunk uniqueness.
- [x] Run `uv run pytest tests/test_paddleocr.py -q`; confirm failures identify the missing adapter behavior.
- [x] Implement lazy initialization and locked worker-thread inference; normalize public Paddle result JSON/Markdown into existing models and translate exceptions into Doctopus errors.
- [x] Register a lazy factory. Declare the `paddleocr` optional extra with compatible PaddleOCR 3.x document-parsing dependencies and CPU PaddlePaddle; resolve `uv.lock`.
- [x] Run adapter tests and check backend discovery works without the optional extra installed.

### Task 2: Interfaces and routing boundaries

**Files:** Modify `src/doctopus/routing/router.py`, `src/doctopus/core/gateway.py`, `src/doctopus/interfaces/cli.py`, `src/doctopus/interfaces/mcp_server.py`, `src/doctopus/interfaces/static/index.html`; extend `tests/test_paddleocr.py` and `tests/test_core.py`.

**Interfaces:** Existing `Gateway.plan()` and `Gateway.parse()` accept `backend="paddleocr"`; MCP parse/chunk argument schemas and demo selection expose the same ID.

- [x] Add failing tests proving explicit gateway and REST selection reaches PaddleOCR and preserves normalized provenance.
- [x] Add tests proving automatic selection/fallback do not select PaddleOCR, including when PaddleOCR is the only installed engine; fast mode and the existing retry bound must still hold.
- [x] Verify CLI help/selection and MCP tool schemas accept `paddleocr`.
- [x] Update registry consumers and routing eligibility with the smallest changes needed for these behaviors. Add the demo selector entry.
- [x] Run `uv run pytest tests/test_paddleocr.py tests/test_core.py -q`.

### Task 3: Documentation and final verification

**Files:** Modify `README.md`, `CONTRIBUTING.md`, and optional deployment comments where useful.

**Interfaces:** Document `uv sync --extra paddleocr` and `uv run doctopus parse scan.pdf --backend paddleocr`.

- [x] Document supported inputs, first-run model downloads, CPU defaults, explicit-selection policy, and the OCR requirement; link the official GPU installation guidance rather than bundle incompatible CPU/GPU runtimes.
- [x] Run `uv lock --check`, `uv run pytest`, and `uv run python tests/mcp_smoke.py`.
- [x] Run `uv run doctopus backends list --json` and confirm optional dependency status is actionable.
- [x] Attempt a real sample extraction if Paddle runtime/models are available; record any limitation explicitly without claiming inference passed.
- [x] Review the diff for heavy top-level imports, fabricated metadata, unrelated changes, and unintended routing changes.

## Verification results

- Full suite: 64 passed after integrating the latest main; independent review: approved with no findings.
- MCP stdio smoke: passed, including existing Xberg extraction and chunking.
- `uv lock --check --offline`: passed, 206 packages.
- `uv sync --locked --extra paddleocr --extra dev --dry-run`: passed; no environment changes made.
- Real Paddle inference: not run because the optional runtime and model weights are not installed.
- Table blocks and canonical tables share IDs; the chunker skips only matching table blocks and preserves orphan table content and empty-layout page fallback.

## Integration with current main

- Preserved the existing MarkItDown, PyMuPDF4LLM, Marker, MinerU, and Ollama backends and dependency extras.
- Registered PaddleOCR using the shared lazy factory; extended MCP Engine choices while preserving deployment defaults.
- Retained the dynamic UI selector and generic CLI backend help from main.
- Adapted opt-in routing to metadata-based engine selection and tested that custom heavy-engine order cannot enable PaddleOCR automatically.
