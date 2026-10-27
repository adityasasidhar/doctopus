<div align="center">
  <img src="assets/doctopus-mascot-cute.png" alt="Doctopus, a friendly octopus holding symbols for Python, the CLI, REST, and MCP" width="340">

# Doctopus

**Many arms. One API.**

Turn documents into structured, LLM-ready data with a single self-hosted gateway.

[Quick start](#quick-start) · [Interfaces](#interfaces) · [Routing](#how-routing-works) · [Benchmarks](#benchmarks) · [Deploy](#deploy)

</div>

---

Doctopus parses PDFs, Office documents, and scans into Markdown, text, tables, and structured blocks. Use it from Python, the command line, a REST API, or an MCP client. Behind each interface is the same gateway: it selects an available processing engine, explains its decision, and can try an alternative when extraction fails or looks suspicious.

- **Start light.** Xberg is the default engine, with OCR, table extraction, and document structure.
- **Bring in Docling when you need it.** Install the optional backend for its richer layout taxonomy, select it explicitly, or let the gateway escalate when appropriate.
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

## Interfaces

### Command line

```bash
# Markdown goes to stdout; the routing summary goes to stderr
uv run doctopus parse paper.pdf

# Save the canonical JSON result
uv run doctopus parse paper.pdf --format json --output result.json

# Choose an engine explicitly
uv run doctopus parse report.docx --backend docling

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

| Selection | Initial engine | Fallback |
| --- | --- | --- |
| `fast` | Xberg when available | None |
| `balanced` (default) | Xberg when available | At most one alternative, if available and suitable |
| `accurate` | Docling when installed and sufficient memory is available; otherwise Xberg | At most one alternative, if available and suitable |
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

## License

Apache-2.0.
