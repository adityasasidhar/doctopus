# Contributing to Doctopus

Thanks for your interest in contributing. Doctopus is a self-hosted document-processing gateway: one canonical document schema behind Python, CLI, REST, and MCP interfaces, with backend routing and at most one fallback.

## Getting started

Prerequisites:

- **Python 3.12** (the project pins `>=3.12,<3.13`)
- [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/adityasasidhar/doctopus.git
cd doctopus
uv sync --extra dev
uv run pytest
```

Optional extras declared in `pyproject.toml` — install only what your change touches:

```bash
uv sync --extra docling    # optional Docling backend (large; ~4 GB RAM for auto-selection)
uv sync --extra paddleocr  # optional CPU PaddleOCR PP-StructureV3 (explicit backend selection)
uv sync --extra ollama     # Ollama-backed extraction
uv sync --extra markitdown # MarkItDown-backed extraction
```

## Project layout

```text
src/doctopus/
  core/        # Document schema (models), gateway, chunking, errors
  routing/     # inspect_file and the routing decision (router)
  backends/    # Backend protocol, registry, and adapters (xberg, docling, ...)
  interfaces/  # CLI (typer), REST API (FastAPI), MCP server, demo UI
  bench/       # benchmark runner
tests/         # pytest suite, smoke scripts, fixture generator
fixtures/      # sample documents and ground truth
docs/          # documentation site (MkDocs); design specs and plans under docs/superpowers/
```

Design rules that keep the codebase coherent:

- **One output shape.** All backends return `RawResult` (`backends/base.py`); the gateway wraps it into the versioned `Document` (schema `1.0`). Do not add backend-specific fields to the public schema without a schema discussion first.
- **Never invent data.** Information an engine cannot provide stays `null`.
- **Keep Lite light.** Heavy optional imports stay lazy (see the `_docling()` factory in `backends/registry.py`) so `uv sync` without extras remains small.
- **Routing is inspect → route → extract**, with at most one alternative on failure or a suspicious result. Suspicion thresholds and fallback behavior live in `routing/router.py` and `core/gateway.py`; treat them as documented heuristics, and update the README table if you change them.

## Development workflow

1. Branch from `main` (`git checkout -b feat/your-change`).
2. Make your change, keeping commits small and focused.
3. Add or update tests for the behavior you changed.
4. Run the checks below.
5. Open a pull request describing the motivation, the approach, and how you tested it.

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/), e.g. `feat(backends): add markdown fallback backend` or `fix(gateway): keep original result when escalation yields less text`.

## Running tests

```bash
uv run pytest                      # full unit test suite
uv run python tests/mcp_smoke.py   # MCP server smoke test
```

The fast tests in `tests/test_core.py` use fake backends on purpose so routing, RAM gating, escalation, and safety logic can be tested without heavy imports. Follow that pattern when testing gateway or router behavior.

Quality and layout scripts (require fixtures):

```bash
uv run python tests/make_fixtures.py   # regenerate fixtures/ (needs the dev extra)
uv run python tests/ocr_quality.py     # OCR scoring against ground truth
uv run python tests/layout_quality.py  # reading-order / table scoring
```

Fixture PDFs under `fixtures/` are generated or curated inputs; ground truth lives in the adjacent `.truth.json` files. If you add a fixture, include its ground truth and note how it was produced.

## Benchmarks

If your change affects performance or extraction quality, reproduce the suite and record results:

```bash
uv sync --extra dev --extra docling
uv run python tests/make_fixtures.py
uv run python -m doctopus.bench.run
```

Paste the output into your PR (the reference table lives in `bench_results/results.md` and the README). Benchmarks run in fresh subprocesses; report the machine you ran them on, since numbers are hardware-dependent.

## Adding or changing a backend

1. Implement the `Backend` protocol from `backends/base.py`: `id`, `info()`, `supports(ext)`, and `async process(path, *, ocr=None) -> RawResult`.
2. Return honest values: set `quality` only if the engine reports it, leave the rest `None`.
3. Register it in `backends/registry.py` with a lazy factory if the import is heavy.
4. Make sure `uv run doctopus backends list` shows it and `uv run doctopus plan <file>` can select or escalate to it.
5. Add unit tests with a fake or minimal backend; add an end-to-end check only if the backend is installable in CI-sized environments.

The `paddleocr` adapter wraps PP-StructureV3 for PDFs and images. Keep pipeline initialization and prediction iteration in its locked worker thread; backend discovery must not import Paddle or load models. It is excluded from automatic selection and fallback until benchmarked. Canonical table blocks retain provenance, while the chunker emits their corresponding `Table` entries only once. Run `uv run pytest tests/test_paddleocr.py` for adapter and interface contract tests without model downloads.

## Documentation

- User-facing behavior changes (new flags, endpoints, routing rules, schema fields) must be reflected in `README.md` and the documentation site under `docs/`.
- Preview the site with `uv sync --group docs` then `uv run mkdocs serve`. CI builds it with `mkdocs build --strict`, so broken links fail the build.
- The Python API reference is generated from docstrings with mkdocstrings; keep public docstrings accurate.
- Design proposals and implementation plans go in `docs/superpowers/specs/` and `docs/superpowers/plans/`, dated `YYYY-MM-DD-<slug>.md`.
- Keep the routing diagram and selection table in the README accurate.

## Style

- Python 3.12 syntax; type annotations on public functions.
- Follow the surrounding style in each module (the codebase favors compact, direct code over deep class hierarchies).
- Prefer `pathlib.Path` over string paths.
- Errors surface through `doctopus.core.errors` (`DoctopusError` hierarchy); use them rather than bare `ValueError` for user-facing failures.

## Pull request checklist

- [ ] `uv run pytest` passes
- [ ] New behavior has tests; bug fixes have a regression test
- [ ] README / docs updated where user-visible
- [ ] Benchmarks re-run if performance or quality is affected
- [ ] Heavy imports stay lazy; Lite install stays light
- [ ] No invented data — unknowns remain `null`

## License

By contributing, you agree that your contributions are licensed under the Apache License 2.0, the same license as the project.
