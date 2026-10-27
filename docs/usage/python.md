# Python

```python
import doctopus

doc = doctopus.parse("paper.pdf")

print(doc.markdown)
print(doc.tables)
print(doc.processing.backend)
print(doc.processing.decision.reasons)

chunks = doctopus.chunk("paper.pdf", max_chars=1500)
decision = doctopus.plan("paper.pdf", mode="accurate")
```

## Top-level helpers

| Function | Returns |
| --- | --- |
| `doctopus.parse(path, *, backend=None, mode="balanced", fallback=None, ocr=None)` | [`Document`](../concepts/output.md) |
| `doctopus.chunk(path, *, max_chars=1500, backend=None, mode="balanced")` | `list[Chunk]` |
| `doctopus.plan(path, *, backend=None, mode="balanced")` | `Decision`, without extracting |

- `backend` is `"auto"` (the router decides) or an engine id. `None` uses `$DOCTOPUS_BACKEND`, otherwise `"auto"`.
- `mode` is `"fast"`, `"balanced"` or `"accurate"`. See [Routing & fallback](../concepts/routing.md).
- `fallback=False` disables retries. `fallback=True` allows one alternative even for an explicitly chosen engine, except in `fast` mode.
- `ocr=True` requests forced OCR where the engine supports it. Docling and PyMuPDF4LLM currently use their engine defaults.

The default file-size limit is 200 MiB.

## Async applications

The top-level helpers are synchronous and use `asyncio.run`, so they cannot be called from a running event loop. Use the gateway directly instead:

```python
from doctopus.core.gateway import Gateway

gateway = Gateway()

async def extract(path):
    return await gateway.parse(path, backend="auto", mode="balanced")
```

`Gateway` also exposes `plan()` and `list_backends()`. See the [Python API reference](../reference/python-api.md).

## Working with the result

```python
doc = doctopus.parse("report.pdf")

for block in doc.blocks:
    if block.type == "heading":
        print("#" * (block.level or 1), block.text)

for table in doc.tables:
    print(table.page, table.markdown)

for warning in doc.processing.warnings:
    print("warning:", warning)

doc.model_dump_json(indent=2)   # it is a Pydantic model
```

Values an engine cannot provide stay `None`; Doctopus never fabricates them.
