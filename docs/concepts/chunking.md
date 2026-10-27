# Chunking

`doctopus chunk`, `doctopus.chunk()`, `POST /v1/chunk` and the `chunk_document` MCP tool split a parsed document into layout-aware chunks, ready for embedding, retrieval, or dataset building.

```bash
doctopus chunk ./corpus --output corpus.jsonl --max-chars 1500
```

Each JSONL line is one chunk:

```json
{"id":"bdfaa68d8984-0000","kind":"text","text":"Provided proper attribution is provided, Google hereby grants permission …","n_chars":173,"heading_path":[],"pages":[1],"block_ids":["node-1ef092e0f747cf1d"],"table_id":null,"source":{"filename":"attention_2col.pdf","document_id":"doc_bdfaa68d8984_a4b0bb","content_hash":"bdfaa68d8984f0dc…","backend":"xberg","schema_version":"1.0"}}
```

## Rules

- Headings close the current chunk and are recorded in `heading_path` for the chunks that follow.
- Text is packed up to `max_chars` (default 1500). An over-long paragraph is split at sentence boundaries, then at spaces.
- Each table becomes one `table` chunk and is never split, so it may exceed `max_chars`. Tables with known pages are interleaved at page boundaries; tables with unknown pages go last. PaddleOCR table content can contain HTML.
- When there are no text-bearing blocks, chunks use page text or document text, skipping paragraphs found within a table's Markdown.
- Blocks labeled `page_header` and `page_footer` are dropped; engines without those labels cannot provide that filtering.

## IDs and deduplication

Chunk IDs combine the content hash and ordinal position. They are repeatable for the same extraction and chunk settings; changing the backend or chunk size can change what a given ID contains. `source.document_id` is generated per parse.

The CLI searches directories recursively for extensions supported by available engines. Byte-identical files are parsed before duplicate chunks are skipped. A file that fails is reported and the run continues; the exit code is `2` if any file failed.

## Python

```python
import doctopus

for c in doctopus.chunk("paper.pdf", max_chars=1000):
    print(c.kind, c.heading_path, c.pages, c.text[:80])
```

To chunk a `Document` you already have, use `doctopus.core.chunk.chunk(doc, max_chars=...)`.
