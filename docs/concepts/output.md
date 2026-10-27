# Output schema

Python parsing, CLI JSON output, and REST `/v1/parse` return a versioned `Document`. The current schema version is `1.0`.

| Field | Contents |
| --- | --- |
| `schema_version` | `"1.0"` |
| `meta` | Filename, format, page count when known, size, content hash, and other metadata |
| `markdown`, `text` | Extracted document content |
| `blocks`, `tables`, `pages` | Structured content, including page and bounding-box information when available |
| `processing` | Backend, elapsed time, routing decision, fallback information, and warnings |

Unavailable optional scalar values remain `null`; collections such as `blocks`, `tables`, and `pages` may be empty. Some adapters derive structure from Markdown rather than native layout.

## Example

A trimmed result for a 15-page PDF routed automatically to Xberg (`doctopus parse attention_2col.pdf --format json`):

```json
{
  "schema_version": "1.0",
  "meta": {
    "document_id": "doc_bdfaa68d8984_5c2285",
    "filename": "attention_2col.pdf",
    "format": "pdf",
    "mime_type": "application/pdf",
    "page_count": 15,
    "size_bytes": 2215244,
    "content_hash": "bdfaa68d8984f0dc02beaca527b76f207d99b666d31d1da728ee0728182df697",
    "title": null,
    "processed_at": "2026-10-27T06:13:31.983468Z"
  },
  "markdown": "…",
  "text": "…",
  "blocks": [
    {
      "id": "node-cdec5f8baa3a76a9",
      "type": "heading",
      "text": "Attention Is All You Need",
      "page": 1,
      "bbox": {"x0": 211.49, "y0": 629.96, "x1": 399.89, "y1": 647.17},
      "level": 1,
      "source": "xberg"
    }
  ],
  "tables": [
    {
      "id": "table-1",
      "page": 6,
      "markdown": "| Layer Type | Complexity per Layer | …",
      "rows": [["Layer Type", "Complexity per Layer", "…"], ["Self-Attention", "O ( n2 · d )", "…"]],
      "bbox": {"x0": 125.0, "y0": 611.0, "x1": 487.0, "y1": 678.0},
      "source": "xberg"
    }
  ],
  "pages": [{"page": 1, "text": "…"}],
  "processing": {
    "backend": "xberg",
    "backend_version": "1.3.9",
    "mode": "balanced",
    "elapsed_ms": 287,
    "peak_rss_mb": 140.9,
    "ocr_used": false,
    "fallback_from": null,
    "warnings": [],
    "decision": {
      "backend": "xberg",
      "mode": "balanced",
      "reasons": [
        "paddleocr is opt-in: select it explicitly with backend='paddleocr'",
        "pdf · 15 pages · 2163.3 KB",
        "light engine first (built-in OCR, tables, bbox); escalates only if output looks wrong",
        "→ xberg"
      ],
      "inspection": {"ext": "pdf", "size_kb": 2163.3, "kind": "pdf", "pages": 15, "mem_available_mb": 3043}
    }
  }
}
```

## Processing details

- `processing.decision` records the initial selection; `processing.backend` identifies the engine that produced the returned result. They differ when a fallback was used, and `fallback_from` names the replaced engine.
- `mode` is `manual` when the request named an engine explicitly.
- `elapsed_ms` measures the returned engine's extraction attempt, excluding inspection, previous failed attempts, and response serialization.
- `peak_rss_mb` is a process/child high-water mark, not memory allocated by a single request.

## Models

| Model | Fields |
| --- | --- |
| `DocMeta` | `document_id`, `filename`, `format`, `mime_type`, `page_count`, `size_bytes`, `content_hash` (SHA-256 of the input), `title`, `processed_at` |
| `Block` | `id`, `type` (`heading`, `paragraph`, `list_item`, `code`, `caption`, …), `text`, `page`, `bbox`, `level`, `source` |
| `Table` | `id`, `page`, `markdown`, `rows`, `bbox`, `source` |
| `Page` | `page`, `text` |
| `Bbox` | `x0`, `y0`, `x1`, `y1` |
| `Processing` | `backend`, `backend_version`, `mode`, `elapsed_ms`, `peak_rss_mb`, `ocr_used`, `fallback_from`, `warnings`, `decision` |
| `Decision` | `backend`, `mode`, `reasons`, `inspection` |

All models are Pydantic v2 models in `doctopus.core.models`. See the [Python API reference](../reference/python-api.md).
