# Routing & fallback

Every request goes through the same pipeline, whichever interface it came from:

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

The decision and its reasons travel with the result in `processing.decision`, and `doctopus plan` shows them without extracting.

## Modes

| Selection | Initial engine | Fallback |
| --- | --- | --- |
| `fast` | Xberg if available and it supports the extension; otherwise another compatible light engine | None |
| `balanced` (default) | Same light-engine preference as `fast` | Light → first compatible heavy engine passing the memory check; heavy → compatible light engine |
| `accurate` | First compatible, available heavy engine in priority order passing the memory check; otherwise the light-engine preference | Same bounded alternative policy as `balanced` |
| Explicit backend | The requested engine | None by default |

## Inspection

Inspection records the extension, size, PDF page count when available, and reported free RAM. Initial routing uses the extension, backend availability, requested mode, and memory thresholds; it does not classify layout complexity before extraction.

If no compatible light engine is found, the router selects the first available non-Paddle engine. `fast` disables retries but can still select a heavy engine in that case. Extraction still rejects an unsupported format.

## Memory checks

Each backend declares a `ram_mb` threshold, reported by `doctopus backends list --json`:

| Engine | Threshold |
| --- | ---: |
| Docling | 4,000 MB |
| PaddleOCR | 3,500 MB |
| MinerU | 2,000 MB |
| Marker | 1,500 MB |

Each threshold is the measured peak plus headroom. Ollama has no declared threshold. Memory availability comes from Linux `/proc/meminfo`; unknown memory does not block automatic selection. This check does not enforce container memory limits. Explicit selection bypasses memory checks and automatic format selection.

## Fallback

An alternative is tried after extraction fails or the output triggers a suspicion check:

- For inputs classified as PDF or image (`pdf`, `png`, `jpg`, `jpeg`, `tiff`, `bmp`), stripped text below **20 characters per inspected page** is suspicious. The page count defaults to one when unknown.
- Engine-reported quality below **0.5** is suspicious for any format.

If the alternative fails, or also looks suspicious and yields no more text, the gateway keeps the original result and adds a warning. When an alternative is used, `processing.fallback_from` names the engine that was replaced.

Control this with `fallback`: `False` (or `--no-fallback`) disables retries; `True` allows one alternative even for an explicit engine, except in `fast` mode.

!!! note
    These are heuristics, not guarantees of extraction quality. Inspect the returned warnings and validate output for your documents.
