# Doctopus — design (hackathon prototype)

*Many arms. One API.* Open-source document-processing gateway: one canonical output,
swappable engines (Xberg fast/light, Docling layout-aware/heavy), a deterministic,
explainable router, exposed as Python SDK, CLI, REST and MCP over one shared core.

## Scope (P0)
- Core `Gateway.parse()` + canonical `Document` schema v1 (markdown, text, blocks w/ page+bbox, tables, processing metadata; unknowns are `null`, never fabricated).
- Backends: `xberg` (renamed from Kreuzberg; async API), `docling` (optional extra).
- Router: near-free `inspect()` (ext, size, pages, free RAM) -> rules -> `Decision` with human-readable reasons; modes fast/balanced/accurate/manual; bounded single fallback.
  - **Revised after benchmarks:** the content-heuristic router ("scanned/tables/columns → Docling") was dropped. Xberg matched or beat Docling on every ground-truth test, and the pypdf probe cost as much as a full Xberg parse. The policy is now light-first: Docling only for `accurate`/manual, or as the one escalation when output looks wrong (<20 chars/page or quality <0.5), and only with ≥4 GB free RAM. An escalation that does no better keeps the original result.
- Interfaces: Typer CLI, FastAPI (+ static demo page), MCP stdio server (mcp>=2) with allowlisted root.
- `bench`: xberg-only vs docling-only vs auto on fixtures (time, peak RSS, quality).
- `chunk`: layout-aware chunks (heading path, pages, whole tables, deterministic ids) as JSONL via CLI/SDK/REST/MCP.
## Out (stretch/P1/P2): caching, async jobs, remote MCP, Qdrant, auth beyond static token.
## Constraints
Python 3.12 pinned; Docling only via `--extra docling`; stdout machine-readable, logs on stderr; Lite install = no torch.
## Verified facts (2026-10-27)
xberg 1.3.9 (`xberg.extract` is async; `output_format="markdown"`, `include_document_structure=True`, `PageConfig(extract_pages=True)`); docling 2.143.0; mcp 2.3.0 (`mcp.server.MCPServer`).
