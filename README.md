<div align="center">
  <img src="assets/doctopus-logo.png" alt="Doctopus, a cute purple octopus holding the logos of its supported document-processing backends" width="340">

# Doctopus

**Many arms. One API.**

Turn documents into structured, LLM-ready data with a single self-hosted gateway.

[Quick start](#quick-start) · [Interfaces](#interfaces) · [Routing](#how-routing-works) · [Benchmarks](#benchmarks) · [Deploy](#deploy)

</div>

---

Doctopus parses PDFs, Office documents, and scans into Markdown, text, tables, and structured blocks. Use it from Python, the command line, a REST API, or an MCP client. Behind each interface is the same gateway: it selects an available processing engine, explains its decision, and can try an alternative when extraction fails or looks suspicious.

- **Start light.** Xberg is the default engine, with OCR, table extraction, and document structure.
- **Bring in Docling when you need it.** Install the optional backend for its richer layout taxonomy, select it explicitly, or let the gateway escalate when appropriate.
- **Add PaddleOCR for document images.** Install the optional PP-StructureV3 backend for OCR, layout, tables, and formulas, then select it explicitly.
- **Keep one output shape.** A versioned document schema carries content, metadata, and processing details across backends.
- **Know what happened.** Routing reasons, warnings, timings, and fallback details travel with the result.
- **Run it yourself.** Use it locally or in Docker, without a per-page API service.

## Quick start

Doctopus requires **Python 3.12** and [uv](https://docs.astral.sh/uv/). From a checkout of this repository:

```bash
# Install the lightweight Xberg backend
uv sync

# Parse a document to Markdown
uv run doctopus parse path/to/document.pdf

# See which engine would be selected, without extracting
uv run doctopus plan path/to/document.pdf
```

On the first OCR run, Xberg downloads its OCR model and caches it locally. To add the optional Docling backend:

```bash
uv sync --extra docling
uv run doctopus parse path/to/document.pdf --mode accurate
```

The standard installation is substantially larger and Docling needs around 4 GB of available RAM for automatic selection. Check installed engines with `uv run doctopus backends list`.

## Engines

Every engine returns the same `Document` schema, so you can swap one for another without changing the code that consumes the output. Install only the engines you need.

| Engine | Kind | Runs | Install | Licence |
| --- | --- | --- | --- | --- |
| `xberg` | Light: text layer, OCR, tables | In-process | Included | MIT |
| `markitdown` | Light: Office, HTML and spreadsheets; no OCR | In-process | `uv sync --extra markitdown` | MIT |
| `pymupdf4llm` | Light: MuPDF text layer, small layout model, OCR | In-process | `uv sync --extra pymupdf4llm` | AGPL-3.0 |
| `docling` | Heavy: layout and table models | In-process | `uv sync --extra docling` | MIT |
| `paddleocr` | Heavy: PP-StructureV3 OCR, layout, tables, formulas | In-process (CPU; explicit selection) | `uv sync --extra paddleocr` | Apache-2.0 package |
| `marker` | Heavy: layout models, equations | Sidecar | `uv tool install --python 3.12 marker-pdf` | Apache-2.0 code; model weights under modified OpenRAIL-M |
| `mineru` | Heavy: layout models, formulas, Office | Sidecar | `uv tool install --python 3.12 mineru` | MinerU Open Source License |
| `ollama` | Heavy: local vision-language model | Ollama service | `uv sync --extra ollama` and `ollama pull qwen3-vl:2b` | MIT client; model licence varies |

Sidecar engines run as separate command-line tools in their own `uv tool` environments. Marker and MinerU have conflicting dependency pins, so they cannot share one environment, and a separate process returns its memory when each job finishes. Doctopus never passes MinerU's `--remote` flag, so documents stay on the machine. Marker defaults to its CPU `fast` mode; set `DOCTOPUS_MARKER_MODE=balanced` if you run its GPU vision-model container.

Check each licence against your use before deploying, particularly AGPL-3.0 and the Marker model weights.

### Choosing an engine

- **Per request:** `--backend` / `-b` on the CLI, the `backend` form field in REST, the `backend` argument on MCP tools, or the engine selector in the demo UI.
- **Per deployment:** `DOCTOPUS_BACKEND=marker`, or `doctopus serve --backend marker` / `doctopus mcp --backend marker`. This applies to requests that do not name an engine.
- **Router:** `auto`, the default, lets the router choose. A request that names an engine, or `auto`, always overrides the deployment default. The routing reasons say which source the choice came from.
- **Accurate mode:** `--mode accurate` uses the first heavy engine that supports the format and fits in free memory. The order is `docling,marker,mineru,ollama`; change it with `DOCTOPUS_HEAVY_ORDER`.

### PaddleOCR PP-StructureV3

Install the optional CPU backend and select it by name:

```bash
uv sync --extra paddleocr
uv run doctopus parse scan.pdf --backend paddleocr
uv run doctopus chunk ./scans --backend paddleocr --output scans.jsonl
```

PP-StructureV3 accepts PDFs and PNG, JPG/JPEG, BMP, and TIF/TIFF images. It runs locally on the CPU, downloads model weights on its first extraction, and reuses the loaded pipeline for subsequent requests in the same process. It uses OCR for every input; the Python option `ocr=False` is rejected. Optional dependencies and model weights are substantial, so allow additional disk space and memory beyond the lightweight profile.

Select `paddleocr` through Python (`doctopus.parse("scan.pdf", backend="paddleocr")`), the REST `backend` form field, MCP's `backend` argument, or the demo's engine selector. It returns the same document schema, including reading-order blocks, pages, bounding boxes, tables, and recognized formulas. Tables may contain HTML within Markdown to retain merged cells; `rows` and document quality remain unknown. Extracted image assets are not exported, and a warning identifies potentially unresolved Markdown image links.

PaddleOCR is **explicit selection only** until it has been benchmarked here; automatic modes and fallback continue to use the existing engine policy. This extra installs CPU PaddlePaddle. For GPU use, follow the [official PaddlePaddle installation instructions](https://www.paddleocr.ai/latest/en/version3.x/installation.html) in an environment with the appropriate GPU runtime; the bundled adapter currently selects the CPU device.

## Interfaces

### Command line

```bash
# Markdown goes to stdout; the routing summary goes to stderr
uv run doctopus parse paper.pdf

# Save the canonical JSON result
uv run doctopus parse paper.pdf --format json --output result.json

# Choose an engine explicitly
uv run doctopus parse report.docx --backend docling
uv run doctopus parse scan.pdf --backend paddleocr

# Inspect routing or available engines
uv run doctopus plan paper.pdf --mode accurate
uv run doctopus backends list

# Export layout-aware chunks from files or folders as JSONL
uv run doctopus chunk ./corpus --output corpus.jsonl
```

Use `--help` on any command to see its options. Supported output formats are `md`, `text`, and `json`.

### Python

```python
import doctopus

doc = doctopus.parse("paper.pdf")

print(doc.markdown)
print(doc.tables)
print(doc.processing.backend)
print(doc.processing.decision.reasons)

chunks = doctopus.chunk("paper.pdf", max_chars=1500)
```

For async applications, use `await Gateway().parse(...)` from `doctopus.core.gateway`.

### REST API and demo UI

```bash
uv run doctopus serve --port 8000
```

Open [localhost:8000](http://localhost:8000) for the drag-and-drop demo, or send a document to the API:

```bash
curl -F file=@paper.pdf -F mode=balanced http://localhost:8000/v1/parse
```

Other endpoints include `POST /v1/chunk`, `POST /v1/plan`, `GET /v1/backends`, and `GET /v1/health`. Interactive API documentation is available at `/docs`.

### MCP

Run the server over stdio with access restricted to a document directory:

```bash
uv run doctopus mcp --root ./docs
```

For an MCP client, adjust these absolute paths to your checkout and documents directory:

```json
{
  "mcpServers": {
    "doctopus": {
      "command": "uv",
      "args": ["--directory", "/path/to/doctopus", "run", "doctopus", "mcp", "--root", "/path/to/docs"]
    }
  }
}
```

The server exposes `parse_document`, `chunk_document` (paged with `offset` and `limit`), `explain_routing`, `list_processing_backends`, and `compare_processors`.

## How routing works

```text
CLI · REST · MCP · Python
          │
          ▼
   Inspect → Route → Extract → Document
               │        │
               │        └─ At most one alternative on failure or a suspicious result
               ├─ Xberg: light, default
               └─ Docling: optional, layout-aware
```

PaddleOCR PP-StructureV3 is also available via explicit `--backend paddleocr` selection; it is excluded from automatic routing and escalation.

| Selection | Initial engine | Fallback |
| --- | --- | --- |
| `fast` | Xberg when available | None |
| `balanced` (default) | Xberg when available | At most one alternative, if available and suitable |
| `accurate` | The first heavy engine in `DOCTOPUS_HEAVY_ORDER` that supports the format and fits in free memory; otherwise Xberg | At most one alternative, if available and suitable |
| Explicit backend | The requested engine | None by default |

A PDF or image result is considered suspicious when it has fewer than 20 characters per page, or when the engine reports quality below 0.5. If an escalation fails or also looks suspicious and yields no more text, the gateway keeps the original result and adds a warning. These are heuristics, not guarantees of extraction quality. Inspect the returned warnings and validate output for your documents.

## Output

Each parse returns a versioned `Document` containing:

| Field | Contents |
| --- | --- |
| `meta` | Filename, format, page count when known, size, content hash, and other metadata |
| `markdown`, `text` | Extracted document content |
| `blocks`, `tables`, `pages` | Structured content, including page and bounding-box information when available |
| `processing` | Backend, elapsed time, routing decision, fallback information, and warnings |

Information an engine cannot provide remains `null`; it is not invented. The JSON output uses schema version `1.0`.

### Chunks

`doctopus chunk` writes one chunk per line, ready for embedding, retrieval, or dataset building:

```json
{"id": "bdfaa68d8984-0004", "kind": "text", "text": "Recurrent neural networks, long short-term memory ...",
 "n_chars": 1173, "heading_path": ["Attention Is All You Need", "1 Introduction"], "pages": [2],
 "block_ids": ["node-d42c39aa99f836ef", "…"], "table_id": null,
 "source": {"filename": "attention_2col.pdf", "document_id": "…", "content_hash": "bdfaa68d…",
            "backend": "xberg", "schema_version": "1.0"}}
```

- Headings close the current chunk and are recorded in `heading_path` for the chunks that follow.
- Text is packed up to `--max-chars` (default 1500). An over-long paragraph is split at sentence boundaries, then at spaces.
- Each table becomes one `table` chunk in Markdown, in page order, and is never split. When an engine returns no layout blocks, chunks come from page text instead, and text that repeats a table is skipped.
- Page headers and footers are dropped.
- Chunk ids combine the content hash and position, so the same file always yields the same ids.
- Within a batch, byte-identical files are skipped. A file that fails is reported and the run continues; the exit code is 2 if any file failed.

## Benchmarks

The following measurements were taken in fresh subprocesses on one laptop. They describe these fixtures and hardware, not a universal comparison. Quality is scored only where ground truth exists.

| Document | Engine | Wall time | Peak RSS | Quality |
| --- | --- | ---: | ---: | --- |
| 15-page, two-column paper | Xberg | 0.37 s | 158 MB | — |
| | Docling | 18.12 s | 2,997 MB | — |
| 9-page paper | Xberg | 0.36 s | 170 MB | — |
| | Docling | 22.84 s | 3,221 MB | — |
| 3-page scan | Xberg | 0.24 s | 198 MB | OCR F1 0.967 |
| | Docling | 40.67 s | 3,152 MB | OCR F1 0.921 |
| Merged-header table | Xberg | 0.13 s | 99 MB | Cell recall 1.000 |
| | Docling | 8.10 s | 2,581 MB | Cell recall 1.000 |
| Two-column reading order | Xberg | 0.10 s | 98 MB | Order 1.000 |
| | Docling | 6.97 s | 2,183 MB | Order 1.000 |

On these scored fixtures, Xberg matched or exceeded Docling's scores while using less time and memory. Docling produced a richer block taxonomy, and table detection varied between the two papers. Both engines performed poorly on a deliberately degraded scan. Results depend on document characteristics; counterexamples and reproducible benchmarks are welcome.

To reproduce the benchmark suite:

```bash
uv sync --extra dev --extra docling
uv run python tests/make_fixtures.py
uv run python -m doctopus.bench.run
```

## Deploy

Start the lightweight Docker Compose profile:

```bash
docker compose -f deploy/docker-compose.yml up
```

Build an image with the optional Docling backend:

```bash
docker build -f deploy/Dockerfile --build-arg EXTRA=docling -t doctopus:standard .
```

The included Compose configuration uses a 512 MB memory limit for the lightweight profile. A deployment using Docling needs more memory; adjust the configuration accordingly. The included volume preserves the OCR model cache across restarts.

Set `DOCTOPUS_API_TOKEN` to require a bearer token on the protected API endpoints, and `DOCTOPUS_MAX_UPLOAD_MB` to change the upload limit (default: 50 MB). The health endpoint is unauthenticated. MCP file access is confined to its configured `--root`; uploaded files are streamed to temporary storage and removed after processing.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run python tests/mcp_smoke.py
```

Install `--extra docling` as well when developing or testing the optional backend.
Use `--extra paddleocr` for real PP-StructureV3 extraction. PaddleOCR adapter tests use representative engine results so the normal unit suite requires no Paddle models.

## License

Apache-2.0.
