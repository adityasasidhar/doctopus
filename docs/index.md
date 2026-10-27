---
hide:
  - navigation
  - toc
---

<div class="dx-hero" markdown>

![Doctopus logo](assets/logo.png)

# Doctopus

<p class="dx-tagline">Many arms. One API.</p>
<p class="dx-sub">Turn documents into structured, LLM-ready data with a single self-hosted gateway.</p>

[Get started](installation.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/adityasasidhar/doctopus){ .md-button }

</div>

Doctopus parses PDFs, Office documents, and scans into Markdown, text, tables, and structured blocks. Use it from Python, the command line, a REST API, or an MCP client. Behind each interface is the same gateway: it selects an available processing engine, explains its decision, and can try an alternative when extraction fails or looks suspicious.

```bash
pip install doctopus-ai
doctopus parse paper.pdf
```

## Features

<div class="grid cards" markdown>

-   :material-feather:{ .lg .middle } **Start light**

    ---

    Xberg is the default engine, with OCR, table extraction, and document structure, at 100–200 MB of RAM.

    [:octicons-arrow-right-24: Engines](concepts/engines.md)

-   :material-shape-outline:{ .lg .middle } **Eight engines, one schema**

    ---

    Docling, PaddleOCR, Marker, MinerU, MarkItDown, PyMuPDF4LLM and Ollama vision models all return the same versioned `Document`.

    [:octicons-arrow-right-24: Output schema](concepts/output.md)

-   :material-routes:{ .lg .middle } **Explainable routing**

    ---

    The router picks an engine by format, mode and free memory, records why, and tries at most one alternative on a failed or suspicious result.

    [:octicons-arrow-right-24: Routing](concepts/routing.md)

-   :material-puzzle:{ .lg .middle } **Every interface**

    ---

    Python, CLI, REST API with a drag-and-drop demo, and an MCP server for agents, all backed by the same gateway.

    [:octicons-arrow-right-24: Usage](usage/cli.md)

-   :material-scissors-cutting:{ .lg .middle } **RAG-ready chunks**

    ---

    Layout-aware chunks that respect headings and never split tables, exported as JSONL.

    [:octicons-arrow-right-24: Chunking](concepts/chunking.md)

-   :material-server:{ .lg .middle } **Run it yourself**

    ---

    Use it locally or in Docker, without a per-page API service.

    [:octicons-arrow-right-24: Deployment](deployment.md)

</div>

## At a glance

=== "Python"

    ```python
    import doctopus

    doc = doctopus.parse("paper.pdf")
    print(doc.markdown)
    print(doc.processing.backend, doc.processing.decision.reasons)

    chunks = doctopus.chunk("paper.pdf", max_chars=1500)
    ```

=== "CLI"

    ```bash
    doctopus parse paper.pdf                        # Markdown to stdout
    doctopus parse scan.pdf --backend docling       # pick an engine
    doctopus plan paper.pdf --mode accurate         # explain routing only
    doctopus chunk ./corpus --output corpus.jsonl   # chunks for RAG
    ```

=== "REST"

    ```bash
    doctopus serve --port 8000
    curl -F file=@paper.pdf http://localhost:8000/v1/parse
    ```

=== "MCP"

    ```json
    {
      "mcpServers": {
        "doctopus": {
          "command": "doctopus",
          "args": ["mcp", "--root", "/path/to/docs"]
        }
      }
    }
    ```

## How it works

```text
CLI · REST · MCP · Python
          │
          ▼
   Inspect → Route → Extract → Document
               │        │
               │        └─ At most one alternative on failure or a suspicious result
               ├─ Light: xberg (preferred), pymupdf4llm, markitdown
               ├─ Heavy: docling, marker, mineru, ollama
               └─ Explicit only: paddleocr
```

Doctopus is [MIT licensed](https://github.com/adityasasidhar/doctopus/blob/main/LICENSE). Backend packages and model weights have their own licenses.
