# Quick start

This page assumes you have [installed](installation.md) `doctopus-ai`.

## Parse a document

```bash
doctopus parse path/to/document.pdf
```

Markdown goes to stdout and a short routing summary goes to stderr, so you can pipe the output:

```bash
doctopus parse paper.pdf > paper.md
doctopus parse paper.pdf --format json --output paper.json
```

## See why an engine was chosen

`plan` runs inspection and routing without extracting anything:

```bash
doctopus plan paper.pdf
doctopus plan paper.pdf --mode accurate
```

The three processing modes are `fast`, `balanced` (default) and `accurate`. See [Routing & fallback](concepts/routing.md).

## Pick an engine

```bash
doctopus backends list                       # what is installed and why others are not
doctopus parse report.docx --backend docling
```

## From Python

```python
import doctopus

doc = doctopus.parse("paper.pdf")

print(doc.markdown)
print(doc.tables)
print(doc.processing.backend)
print(doc.processing.decision.reasons)

chunks = doctopus.chunk("paper.pdf", max_chars=1500)
```

## Build a RAG corpus

```bash
doctopus chunk ./corpus --output corpus.jsonl
```

Each line is one chunk with its heading path, pages and source. See [Chunking](concepts/chunking.md).

## Serve it

```bash
doctopus serve --port 8000
```

Open [localhost:8000](http://localhost:8000) for the drag-and-drop demo, or `/docs` for the interactive API documentation. See [REST API & demo UI](usage/rest-api.md).

## Next steps

- [Engines](concepts/engines.md): what each backend is good at and what it costs.
- [MCP server](usage/mcp.md): give an agent safe access to a document folder.
- [Output schema](concepts/output.md): every field in the `Document`.
