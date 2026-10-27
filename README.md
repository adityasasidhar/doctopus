<div align="center">
  <img src="https://raw.githubusercontent.com/adityasasidhar/doctopus/main/assets/doctopus-logo.png" alt="Doctopus logo" width="340">

# Doctopus

**Many arms. One API.**

Turn documents into structured, LLM-ready data with a single self-hosted gateway.

[Documentation](https://adityasasidhar.github.io/doctopus/) · [Formats](#supported-formats) · [Quick start](#quick-start) · [Interfaces](#interfaces) · [Routing](#how-routing-works) · [Benchmarks](#benchmarks) · [Deploy](#deploy)

</div>

---

Doctopus parses PDFs, Office documents, and scans into Markdown, text, tables, and structured blocks. Use it from Python, the command line, a REST API, or an MCP client. Behind each interface is the same gateway: it selects an available processing engine, explains its decision, and can try an alternative when extraction fails or looks suspicious.

- **Start light.** Xberg is the default engine, with OCR, table extraction, and document structure.
- **Bring in Docling when you need it.** Install the optional backend for its richer layout taxonomy, select it explicitly, or let the gateway escalate when appropriate.
- **Add PaddleOCR for document images.** Install the optional CPU PP-StructureV3 backend for OCR, layout, and tables, then select it explicitly. Formula recognition is opt-in.
- **Keep one output shape.** A versioned document schema carries content, metadata, and processing details across backends.
- **Know what happened.** Routing reasons, warnings, timings, and fallback details travel with the result.
- **Run it yourself.** Use it locally or in Docker, without a per-page API service.

## Supported formats

### Input

| Category | Formats | Engines | Base install |
| --- | --- | --- | :---: |
| PDF | ![PDF][fmt-pdf] | All eight engines | ✅ |
| Word processing | ![DOCX][fmt-docx] ![RTF][fmt-rtf] | DOCX: `xberg`, `docling`, `mineru`, `markitdown` · RTF: `xberg` | ✅ |
| Presentations | ![PPTX][fmt-pptx] | `xberg`, `docling`, `mineru`, `markitdown` | ✅ |
| Spreadsheets | ![XLSX][fmt-xlsx] ![XLS][fmt-xls] ![CSV][fmt-csv] | XLSX, CSV: `xberg`, `docling`, `mineru`, `markitdown` · XLS: `markitdown` | XLSX, CSV |
| Web and text | ![HTML][fmt-html] ![Markdown][fmt-markdown] ![TXT][fmt-txt] ![JSON][fmt-json] ![XML][fmt-xml] | HTML: `xberg`, `docling`, `mineru`, `markitdown` · Markdown: `xberg`, `docling`, `markitdown` · TXT: `xberg`, `markitdown` · JSON, XML: `markitdown` | HTML, Markdown, TXT |
| Ebooks | ![EPUB][fmt-epub] ![MOBI][fmt-mobi] ![FB2][fmt-fb2] ![CBZ][fmt-cbz] | EPUB: `xberg`, `mineru`, `pymupdf4llm`, `markitdown` · MOBI, FB2, CBZ: `pymupdf4llm` | EPUB |
| Email | ![EML][fmt-eml] ![MSG][fmt-msg] | EML: `xberg` · MSG: `markitdown` | EML |
| Images and scans | ![PNG][fmt-png] ![JPEG][fmt-jpeg] ![TIFF][fmt-tiff] ![BMP][fmt-bmp] ![WebP][fmt-webp] | PNG, JPEG: `xberg`, `docling`, `paddleocr`, `marker`, `mineru`, `ollama` · TIFF: `xberg`, `docling`, `paddleocr`, `marker`, `ollama` · BMP: `paddleocr` · WebP: `marker`, `ollama` | PNG, JPEG, TIFF |
| Vector and fixed layout | ![XPS][fmt-xps] ![SVG][fmt-svg] | `pymupdf4llm` | — |

*Base install* means the `xberg` engine that ships with `pip install doctopus-ai`; the other engines are [optional](#engines). Both `.jpg` and `.jpeg` are accepted; `.htm` is accepted by Xberg and MarkItDown, and `.tif` by PaddleOCR. The router picks a compatible installed engine automatically, and `doctopus backends list --json` reports the exact extensions each installed engine accepts.

### Output

| Format | What you get | How to get it |
| --- | --- | --- |
| ![Markdown][fmt-markdown] | The whole document as Markdown, tables included | `doctopus parse` (default) · `doc.markdown` · `markdown` field in REST and MCP |
| ![Text][fmt-text] | The extracted text without Markdown syntax | `doctopus parse --format text` · `doc.text` |
| ![JSON][fmt-json] | The versioned `Document` (schema `1.0`): metadata, Markdown, text, blocks with bounding boxes, tables as Markdown and rows, pages, and processing details | `doctopus parse --format json` · `POST /v1/parse` · `doc.model_dump_json()` |
| ![JSONL][fmt-jsonl] | One layout-aware chunk per line, with heading path, pages, and source; tables are never split | `doctopus chunk` · `POST /v1/chunk` · MCP `chunk_document` |
| ![Pydantic][fmt-pydantic] | Typed `Document` and `Chunk` objects | `doctopus.parse()` · `doctopus.chunk()` |

See [Output](#output) for every field.

[fmt-pdf]: https://img.shields.io/badge/PDF-EC1C24?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgdmlld0JveD0iMCAwIDI0IDI0IiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxwYXRoIGQ9Ik0yMy42MyAxNS4zYy0uNzEtLjc0NS0yLjE2Ni0xLjE3LTQuMjI0LTEuMTctMS4xIDAtMi4zNzcuMTA2LTMuNzYxLjM1NGExOS40NDMgMTkuNDQzIDAgMCAxLTIuMzA3LTIuNjYxYy0uNTMyLS43MS0uOTk0LTEuNDktMS40Mi0yLjIzNi44MTctMi40ODQgMS4yMDctNC41MDcgMS4yMDctNS45NjIgMC0xLjYzMi0uNjAzLTMuMzM2LTIuMzQyLTMuMzM2LS41MzIgMC0xLjA2NS4zMi0xLjM0OS43ODEtLjc4IDEuMzg0LS40MjUgNC40LjkyMyA3LjM4MWE2MC4yNzcgNjAuMjc3IDAgMCAxLTEuNzAzIDQuNTA3Yy0uNTY4IDEuMzQ5LTEuMjA3IDIuNzMzLTEuOTE3IDQuMDFDMi44MzQgMTguNTMuMzE0IDIwLjM0LjAzIDIxLjc1OGMtLjEwNi41MzMuMDcxIDEuMDMuNDYyIDEuNDIuMTQyLjEwNy42MzkuNTMzIDEuNDkuNTMzIDIuNTkgMCA1LjMyMy00LjE4OCA2LjcwNy02LjcwNyAxLjA2NS0uMzU1IDIuMTMtLjcxIDMuMTk0LS45OTRhMzQuOTYzIDM0Ljk2MyAwIDAgMSAzLjQwNy0uNzQ1YzIuNzMyIDIuNDQ4IDUuMTQ1IDIuODM5IDYuMzUyIDIuODM5IDEuNDkgMCAyLjAyMy0uNjA0IDIuMi0xLjEuMzItLjY0LjEwNi0xLjM0OS0uMjEzLTEuNzA0em0tMS40MiAxLjAzYy0uMTA3LjUzMi0uNjQuODg3LTEuMzg0Ljg4Ny0uMjEzIDAtLjM5LS4wMzYtLjYwNC0uMDcxLTEuMzQ4LS4zMi0yLjYyNi0uOTk0LTMuOTAzLTIuMDU5YTE3LjcxNyAxNy43MTcgMCAwIDEgMi45OC0uMjQ4Yy43NDYgMCAxLjM4NS4wMzUgMS44MS4xNDIuNDk3LjEwNiAxLjI3OC40MjYgMS4xIDEuMzQ4em0tNy41MjQtMS42NjhhMzguMDEgMzguMDEgMCAwIDAtMi45NDUuNjc0IDM5LjY4IDM5LjY4IDAgMCAwLTIuNTIuNzQ1IDQwLjA1IDQwLjA1IDAgMCAwIDEuMjA3LTIuNTU1Yy40MjYtLjk5NC43OC0yLjAyMyAxLjEzNi0yLjk4MS4zNTQuNjAzLjc0NSAxLjIwNyAxLjEzNSAxLjczOWE1MC4xMjcgNTAuMTI3IDAgMCAwIDEuOTg3IDIuMzc4ek0xMC4wMzggMS40NmEuNzY4Ljc2OCAwIDAgMSAuNjc0LS40MjVjLjc0NSAwIC44ODcuODUxLjg4NyAxLjUyNiAwIDEuMTM1LS4zNTUgMi44NzQtLjk1OCA0Ljg2MS0xLjAzLTIuNzY4LTEuMS01LjA3NC0uNjAzLTUuOTYyek02LjEzNCAxNy45OTdjLTEuODEgMi45ODEtMy41NDkgNC44MjYtNC42MTMgNC44MjZhLjg3Mi44NzIgMCAwIDEtLjUzMi0uMTc3Yy0uMjEzLS4yMTMtLjMyLS40NjEtLjI0OS0uNzQ1LjIxMy0xLjA2NSAyLjI3MS0yLjU1NSA1LjM5NC0zLjkwNFoiLz48L3N2Zz4%3D&logoColor=white
[fmt-docx]: https://img.shields.io/badge/DOCX-2B579A?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgdmlld0JveD0iMCAwIDI0IDI0IiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxwYXRoIGQ9Ik0yMy4wMDQgMS41cS40MSAwIC43MDMuMjkzdC4yOTMuNzAzdjE5LjAwOHEwIC40MS0uMjkzLjcwM3QtLjcwMy4yOTNINi45OTZxLS40MSAwLS43MDMtLjI5M1Q2IDIxLjUwNFYxOEguOTk2cS0uNDEgMC0uNzAzLS4yOTNUMCAxNy4wMDRWNi45OTZxMC0uNDEuMjkzLS43MDNULjk5NiA2SDZWMi40OTZxMC0uNDEuMjkzLS43MDN0LjcwMy0uMjkzek02LjAzNSAxMS4yMDNsMS40NDIgNC43MzVoMS42NGwxLjU3LTcuODc2SDkuMDM2bC0uOTM3IDQuNjUzLTEuMzI1LTQuNUg1LjM4bC0xLjQwNiA0LjUyMy0uOTM4LTQuNjc1SDEuMzEybDEuNTcgNy44NzRoMS42NDF6TTIyLjUgMjF2LTNoLTE1djN6bTAtNC41di0zLjc1SDEydjMuNzV6bTAtNS4yNVY3LjVIMTJ2My43NXptMC01LjI1VjNoLTE1djNaIi8%2BPC9zdmc%2B&logoColor=white
[fmt-rtf]: https://img.shields.io/badge/RTF-5C6BC0?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGQ9Ik02LDJBMiwyIDAgMCwwIDQsNFYyMEEyLDIgMCAwLDAgNiwyMkgxOEEyLDIgMCAwLDAgMjAsMjBWOEwxNCwySDZNNiw0SDEzVjlIMThWMjBINlY0TTgsMTJWMTRIMTZWMTJIOE04LDE2VjE4SDEzVjE2SDhaIiAvPjwvc3ZnPg%3D%3D&logoColor=white
[fmt-pptx]: https://img.shields.io/badge/PPTX-B7472A?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgdmlld0JveD0iMCAwIDI0IDI0IiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxwYXRoIGQ9Ik0xMy41IDEuNXExLjQ1MyAwIDIuNzk1LjM3NSAxLjM0Mi4zNzUgMi41MDggMS4wNiAxLjE2Ni42ODYgMi4xMiAxLjY0MS45NTYuOTU1IDEuNjQxIDIuMTIxLjY4NiAxLjE2NiAxLjA2MSAyLjUwOFEyNCAxMC41NDcgMjQgMTJxMCAxLjQ1My0uMzc1IDIuNzk1LS4zNzUgMS4zNDItMS4wNiAyLjUwOC0uNjg2IDEuMTY2LTEuNjQxIDIuMTItLjk1NS45NTYtMi4xMjEgMS42NDEtMS4xNjYuNjg2LTIuNTA4IDEuMDYxLTEuMzQyLjM3NS0yLjc5NS4zNzUtMS4yOSAwLTIuNTItLjMwNS0xLjIzLS4zMDQtMi4zMzctLjg4NC0xLjEwOC0uNTgtMi4wNjMtMS40MTgtLjk1NS0uODM4LTEuNjkzLTEuODkzSC45OTdxLS40MTEgMC0uNzA0LS4yOTNUMCAxNy4wMDRWNi45OTZxMC0uNDEuMjkzLS43MDNULjk5NiA2aDMuODlxLjczOS0xLjA1NSAxLjY5NC0xLjg5My45NTUtLjgzNyAyLjA2My0xLjQxOCAxLjEwNy0uNTggMi4zMzctLjg4NFExMi4yMSAxLjUgMTMuNSAxLjV6bS43NSAxLjUzNXY4LjIxNWg4LjIxNXEtLjE0LTEuNjQtLjgyNi0zLjA3Ni0uNjg2LTEuNDM2LTEuNzgyLTIuNTMxLTEuMDk1LTEuMDk2LTIuNTM3LTEuNzgyLTEuNDQxLS42ODUtMy4wNy0uODI2em0tNS4yNjIgNy41N3EwLS42OC0uMjI4LTEuMTY2LS4yMjktLjQ4Ni0uNjI3LS43OS0uMzk5LS4zMDUtLjkzOC0uNDQ2LS41MzktLjE0LTEuMTcyLS4xNEgyLjg0OHY3Ljg2M2gxLjg0di0yLjc0Mkg1LjkzcS41NzQgMCAxLjExOS0uMTd0Ljk3OC0uNDkzcS40MzQtLjMyMi42OTgtLjgwMi4yNjMtLjQ4LjI2My0xLjExNHpNMTMuNSAyMXExLjE3MiAwIDIuMjYyLS4yODd0Mi4wNTYtLjgycS45NjctLjUzNCAxLjc3Ni0xLjI3OC44MDgtLjc0NCAxLjQxOC0xLjY2NC42MS0uOTIuOTg0LTEuOTg2LjM3NS0xLjA2Ny40NjktMi4yMjdoLTkuNzAzVjMuMDM1cS0xLjczNS4xNC0zLjI3LjkwOFQ2Ljc5NyA2aDQuMjA3cS40MSAwIC43MDMuMjkzdC4yOTMuNzAzdjEwLjAwOHEwIC40MS0uMjkzLjcwM3QtLjcwMy4yOTNINi43OTdxLjY0NC43MTUgMS40MTIgMS4yNzEuNzY4LjU1NyAxLjYyMy45NDQuODU1LjM4NyAxLjc4MS41ODZRMTIuNTQgMjEgMTMuNSAyMXpNNS44MTIgOS41OThxLjU3NSAwIC45MTUuMjI4LjM0LjIyOS4zNC44MzggMCAuMjctLjEyNC40NC0uMTIzLjE3LS4zMS4yNzUtLjE4OC4xMDUtLjQyMi4xNDYtLjIzNC4wNDEtLjQ0NS4wNDFINC42ODdWOS41OThaIi8%2BPC9zdmc%2B&logoColor=white
[fmt-xlsx]: https://img.shields.io/badge/XLSX-217346?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgdmlld0JveD0iMCAwIDI0IDI0IiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxwYXRoIGQ9Ik0yMyAxLjVxLjQxIDAgLjcuMy4zLjI5LjMuN3YxOXEwIC40MS0uMy43LS4yOS4zLS43LjNIN3EtLjQxIDAtLjctLjMtLjMtLjI5LS4zLS43VjE4SDFxLS40MSAwLS43LS4zLS4zLS4yOS0uMy0uN1Y3cTAtLjQxLjMtLjdRLjU4IDYgMSA2aDVWMi41cTAtLjQxLjMtLjcuMjktLjMuNy0uM3pNNiAxMy4yOGwxLjQyIDIuNjZoMi4xNGwtMi4zOC0zLjg3IDIuMzQtMy44SDcuNDZsLTEuMyAyLjQtLjA1LjA4LS4wNC4wOS0uNjQtMS4yOC0uNjYtMS4yOUgyLjU5bDIuMjcgMy44Mi0yLjQ4IDMuODVoMi4xNnpNMTQuMjUgMjF2LTNINy41djN6bTAtNC41di0zLjc1SDEydjMuNzV6bTAtNS4yNVY3LjVIMTJ2My43NXptMC01LjI1VjNINy41djN6bTguMjUgMTV2LTNoLTYuNzV2M3ptMC00LjV2LTMuNzVoLTYuNzV2My43NXptMC01LjI1VjcuNWgtNi43NXYzLjc1em0wLTUuMjVWM2gtNi43NXYzWiIvPjwvc3ZnPg%3D%3D&logoColor=white
[fmt-xls]: https://img.shields.io/badge/XLS-217346?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgdmlld0JveD0iMCAwIDI0IDI0IiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxwYXRoIGQ9Ik0yMyAxLjVxLjQxIDAgLjcuMy4zLjI5LjMuN3YxOXEwIC40MS0uMy43LS4yOS4zLS43LjNIN3EtLjQxIDAtLjctLjMtLjMtLjI5LS4zLS43VjE4SDFxLS40MSAwLS43LS4zLS4zLS4yOS0uMy0uN1Y3cTAtLjQxLjMtLjdRLjU4IDYgMSA2aDVWMi41cTAtLjQxLjMtLjcuMjktLjMuNy0uM3pNNiAxMy4yOGwxLjQyIDIuNjZoMi4xNGwtMi4zOC0zLjg3IDIuMzQtMy44SDcuNDZsLTEuMyAyLjQtLjA1LjA4LS4wNC4wOS0uNjQtMS4yOC0uNjYtMS4yOUgyLjU5bDIuMjcgMy44Mi0yLjQ4IDMuODVoMi4xNnpNMTQuMjUgMjF2LTNINy41djN6bTAtNC41di0zLjc1SDEydjMuNzV6bTAtNS4yNVY3LjVIMTJ2My43NXptMC01LjI1VjNINy41djN6bTguMjUgMTV2LTNoLTYuNzV2M3ptMC00LjV2LTMuNzVoLTYuNzV2My43NXptMC01LjI1VjcuNWgtNi43NXYzLjc1em0wLTUuMjVWM2gtNi43NXYzWiIvPjwvc3ZnPg%3D%3D&logoColor=white
[fmt-csv]: https://img.shields.io/badge/CSV-2E7D32?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGQ9Ik0xNCAySDZDNC45IDIgNCAyLjkgNCA0VjIwQzQgMjEuMSA0LjkgMjIgNiAyMkgxOEMxOS4xIDIyIDIwIDIxLjEgMjAgMjBWOEwxNCAyTTE4IDIwSDZWNEgxM1Y5SDE4VjIwTTEwIDE5TDEyIDE1SDlWMTBIMTVWMTVMMTMgMTlIMTAiIC8%2BPC9zdmc%2B&logoColor=white
[fmt-html]: https://img.shields.io/badge/HTML-E34F26?style=flat-square&logo=html5&logoColor=white
[fmt-markdown]: https://img.shields.io/badge/Markdown-000000?style=flat-square&logo=markdown&logoColor=white
[fmt-txt]: https://img.shields.io/badge/TXT-546E7A?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGQ9Ik01LDNDMy44OSwzIDMsMy44OSAzLDVWMTlDMywyMC4xMSAzLjg5LDIxIDUsMjFIMTlDMjAuMTEsMjEgMjEsMjAuMTEgMjEsMTlWNUMyMSwzLjg5IDIwLjExLDMgMTksM0g1TTUsNUgxOVYxOUg1VjVNNyw3VjlIMTdWN0g3TTcsMTFWMTNIMTdWMTFIN003LDE1VjE3SDE0VjE1SDdaIiAvPjwvc3ZnPg%3D%3D&logoColor=white
[fmt-json]: https://img.shields.io/badge/JSON-000000?style=flat-square&logo=json&logoColor=white
[fmt-xml]: https://img.shields.io/badge/XML-005FAD?style=flat-square&logo=xml&logoColor=white
[fmt-epub]: https://img.shields.io/badge/EPUB-6D4C41?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGQ9Ik0xMiAyMS41QzEwLjY1IDIwLjY1IDguMiAyMCA2LjUgMjBDNC44NSAyMCAzLjE1IDIwLjMgMS43NSAyMS4wNUMxLjY1IDIxLjEgMS42IDIxLjEgMS41IDIxLjFDMS4yNSAyMS4xIDEgMjAuODUgMSAyMC42VjZDMS42IDUuNTUgMi4yNSA1LjI1IDMgNUM0LjExIDQuNjUgNS4zMyA0LjUgNi41IDQuNUM4LjQ1IDQuNSAxMC41NSA0LjkgMTIgNkMxMy40NSA0LjkgMTUuNTUgNC41IDE3LjUgNC41QzE4LjY3IDQuNSAxOS44OSA0LjY1IDIxIDVDMjEuNzUgNS4yNSAyMi40IDUuNTUgMjMgNlYyMC42QzIzIDIwLjg1IDIyLjc1IDIxLjEgMjIuNSAyMS4xQzIyLjQgMjEuMSAyMi4zNSAyMS4xIDIyLjI1IDIxLjA1QzIwLjg1IDIwLjMgMTkuMTUgMjAgMTcuNSAyMEMxNS44IDIwIDEzLjM1IDIwLjY1IDEyIDIxLjVNMTIgOFYxOS41QzEzLjM1IDE4LjY1IDE1LjggMTggMTcuNSAxOEMxOC43IDE4IDE5LjkgMTguMTUgMjEgMTguNVY3QzE5LjkgNi42NSAxOC43IDYuNSAxNy41IDYuNUMxNS44IDYuNSAxMy4zNSA3LjE1IDEyIDhNMTMgMTEuNUMxNC4xMSAxMC44MiAxNS42IDEwLjUgMTcuNSAxMC41QzE4LjQxIDEwLjUgMTkuMjYgMTAuNTkgMjAgMTAuNzhWOS4yM0MxOS4xMyA5LjA4IDE4LjI5IDkgMTcuNSA5QzE1LjczIDkgMTQuMjMgOS4yOCAxMyA5Ljg0VjExLjVNMTcuNSAxMS42N0MxNS43OSAxMS42NyAxNC4yOSAxMS45MyAxMyAxMi40NlYxNC4xNUMxNC4xMSAxMy41IDE1LjYgMTMuMTYgMTcuNSAxMy4xNkMxOC41NCAxMy4xNiAxOS4zOCAxMy4yNCAyMCAxMy40VjExLjlDMTkuMTMgMTEuNzQgMTguMjkgMTEuNjcgMTcuNSAxMS42N00yMCAxNC41N0MxOS4xMyAxNC40MSAxOC4yOSAxNC4zMyAxNy41IDE0LjMzQzE1LjY3IDE0LjMzIDE0LjE3IDE0LjYgMTMgMTUuMTNWMTYuODJDMTQuMTEgMTYuMTYgMTUuNiAxNS44MyAxNy41IDE1LjgzQzE4LjU0IDE1LjgzIDE5LjM4IDE1LjkxIDIwIDE2LjA3VjE0LjU3WiIgLz48L3N2Zz4%3D&logoColor=white
[fmt-mobi]: https://img.shields.io/badge/MOBI-6D4C41?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGQ9Ik0xMiAyMS41QzEwLjY1IDIwLjY1IDguMiAyMCA2LjUgMjBDNC44NSAyMCAzLjE1IDIwLjMgMS43NSAyMS4wNUMxLjY1IDIxLjEgMS42IDIxLjEgMS41IDIxLjFDMS4yNSAyMS4xIDEgMjAuODUgMSAyMC42VjZDMS42IDUuNTUgMi4yNSA1LjI1IDMgNUM0LjExIDQuNjUgNS4zMyA0LjUgNi41IDQuNUM4LjQ1IDQuNSAxMC41NSA0LjkgMTIgNkMxMy40NSA0LjkgMTUuNTUgNC41IDE3LjUgNC41QzE4LjY3IDQuNSAxOS44OSA0LjY1IDIxIDVDMjEuNzUgNS4yNSAyMi40IDUuNTUgMjMgNlYyMC42QzIzIDIwLjg1IDIyLjc1IDIxLjEgMjIuNSAyMS4xQzIyLjQgMjEuMSAyMi4zNSAyMS4xIDIyLjI1IDIxLjA1QzIwLjg1IDIwLjMgMTkuMTUgMjAgMTcuNSAyMEMxNS44IDIwIDEzLjM1IDIwLjY1IDEyIDIxLjVNMTIgOFYxOS41QzEzLjM1IDE4LjY1IDE1LjggMTggMTcuNSAxOEMxOC43IDE4IDE5LjkgMTguMTUgMjEgMTguNVY3QzE5LjkgNi42NSAxOC43IDYuNSAxNy41IDYuNUMxNS44IDYuNSAxMy4zNSA3LjE1IDEyIDhNMTMgMTEuNUMxNC4xMSAxMC44MiAxNS42IDEwLjUgMTcuNSAxMC41QzE4LjQxIDEwLjUgMTkuMjYgMTAuNTkgMjAgMTAuNzhWOS4yM0MxOS4xMyA5LjA4IDE4LjI5IDkgMTcuNSA5QzE1LjczIDkgMTQuMjMgOS4yOCAxMyA5Ljg0VjExLjVNMTcuNSAxMS42N0MxNS43OSAxMS42NyAxNC4yOSAxMS45MyAxMyAxMi40NlYxNC4xNUMxNC4xMSAxMy41IDE1LjYgMTMuMTYgMTcuNSAxMy4xNkMxOC41NCAxMy4xNiAxOS4zOCAxMy4yNCAyMCAxMy40VjExLjlDMTkuMTMgMTEuNzQgMTguMjkgMTEuNjcgMTcuNSAxMS42N00yMCAxNC41N0MxOS4xMyAxNC40MSAxOC4yOSAxNC4zMyAxNy41IDE0LjMzQzE1LjY3IDE0LjMzIDE0LjE3IDE0LjYgMTMgMTUuMTNWMTYuODJDMTQuMTEgMTYuMTYgMTUuNiAxNS44MyAxNy41IDE1LjgzQzE4LjU0IDE1LjgzIDE5LjM4IDE1LjkxIDIwIDE2LjA3VjE0LjU3WiIgLz48L3N2Zz4%3D&logoColor=white
[fmt-fb2]: https://img.shields.io/badge/FB2-6D4C41?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGQ9Ik0xMiAyMS41QzEwLjY1IDIwLjY1IDguMiAyMCA2LjUgMjBDNC44NSAyMCAzLjE1IDIwLjMgMS43NSAyMS4wNUMxLjY1IDIxLjEgMS42IDIxLjEgMS41IDIxLjFDMS4yNSAyMS4xIDEgMjAuODUgMSAyMC42VjZDMS42IDUuNTUgMi4yNSA1LjI1IDMgNUM0LjExIDQuNjUgNS4zMyA0LjUgNi41IDQuNUM4LjQ1IDQuNSAxMC41NSA0LjkgMTIgNkMxMy40NSA0LjkgMTUuNTUgNC41IDE3LjUgNC41QzE4LjY3IDQuNSAxOS44OSA0LjY1IDIxIDVDMjEuNzUgNS4yNSAyMi40IDUuNTUgMjMgNlYyMC42QzIzIDIwLjg1IDIyLjc1IDIxLjEgMjIuNSAyMS4xQzIyLjQgMjEuMSAyMi4zNSAyMS4xIDIyLjI1IDIxLjA1QzIwLjg1IDIwLjMgMTkuMTUgMjAgMTcuNSAyMEMxNS44IDIwIDEzLjM1IDIwLjY1IDEyIDIxLjVNMTIgOFYxOS41QzEzLjM1IDE4LjY1IDE1LjggMTggMTcuNSAxOEMxOC43IDE4IDE5LjkgMTguMTUgMjEgMTguNVY3QzE5LjkgNi42NSAxOC43IDYuNSAxNy41IDYuNUMxNS44IDYuNSAxMy4zNSA3LjE1IDEyIDhNMTMgMTEuNUMxNC4xMSAxMC44MiAxNS42IDEwLjUgMTcuNSAxMC41QzE4LjQxIDEwLjUgMTkuMjYgMTAuNTkgMjAgMTAuNzhWOS4yM0MxOS4xMyA5LjA4IDE4LjI5IDkgMTcuNSA5QzE1LjczIDkgMTQuMjMgOS4yOCAxMyA5Ljg0VjExLjVNMTcuNSAxMS42N0MxNS43OSAxMS42NyAxNC4yOSAxMS45MyAxMyAxMi40NlYxNC4xNUMxNC4xMSAxMy41IDE1LjYgMTMuMTYgMTcuNSAxMy4xNkMxOC41NCAxMy4xNiAxOS4zOCAxMy4yNCAyMCAxMy40VjExLjlDMTkuMTMgMTEuNzQgMTguMjkgMTEuNjcgMTcuNSAxMS42N00yMCAxNC41N0MxOS4xMyAxNC40MSAxOC4yOSAxNC4zMyAxNy41IDE0LjMzQzE1LjY3IDE0LjMzIDE0LjE3IDE0LjYgMTMgMTUuMTNWMTYuODJDMTQuMTEgMTYuMTYgMTUuNiAxNS44MyAxNy41IDE1LjgzQzE4LjU0IDE1LjgzIDE5LjM4IDE1LjkxIDIwIDE2LjA3VjE0LjU3WiIgLz48L3N2Zz4%3D&logoColor=white
[fmt-cbz]: https://img.shields.io/badge/CBZ-6D4C41?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGQ9Ik0xMiAyMS41QzEwLjY1IDIwLjY1IDguMiAyMCA2LjUgMjBDNC44NSAyMCAzLjE1IDIwLjMgMS43NSAyMS4wNUMxLjY1IDIxLjEgMS42IDIxLjEgMS41IDIxLjFDMS4yNSAyMS4xIDEgMjAuODUgMSAyMC42VjZDMS42IDUuNTUgMi4yNSA1LjI1IDMgNUM0LjExIDQuNjUgNS4zMyA0LjUgNi41IDQuNUM4LjQ1IDQuNSAxMC41NSA0LjkgMTIgNkMxMy40NSA0LjkgMTUuNTUgNC41IDE3LjUgNC41QzE4LjY3IDQuNSAxOS44OSA0LjY1IDIxIDVDMjEuNzUgNS4yNSAyMi40IDUuNTUgMjMgNlYyMC42QzIzIDIwLjg1IDIyLjc1IDIxLjEgMjIuNSAyMS4xQzIyLjQgMjEuMSAyMi4zNSAyMS4xIDIyLjI1IDIxLjA1QzIwLjg1IDIwLjMgMTkuMTUgMjAgMTcuNSAyMEMxNS44IDIwIDEzLjM1IDIwLjY1IDEyIDIxLjVNMTIgOFYxOS41QzEzLjM1IDE4LjY1IDE1LjggMTggMTcuNSAxOEMxOC43IDE4IDE5LjkgMTguMTUgMjEgMTguNVY3QzE5LjkgNi42NSAxOC43IDYuNSAxNy41IDYuNUMxNS44IDYuNSAxMy4zNSA3LjE1IDEyIDhNMTMgMTEuNUMxNC4xMSAxMC44MiAxNS42IDEwLjUgMTcuNSAxMC41QzE4LjQxIDEwLjUgMTkuMjYgMTAuNTkgMjAgMTAuNzhWOS4yM0MxOS4xMyA5LjA4IDE4LjI5IDkgMTcuNSA5QzE1LjczIDkgMTQuMjMgOS4yOCAxMyA5Ljg0VjExLjVNMTcuNSAxMS42N0MxNS43OSAxMS42NyAxNC4yOSAxMS45MyAxMyAxMi40NlYxNC4xNUMxNC4xMSAxMy41IDE1LjYgMTMuMTYgMTcuNSAxMy4xNkMxOC41NCAxMy4xNiAxOS4zOCAxMy4yNCAyMCAxMy40VjExLjlDMTkuMTMgMTEuNzQgMTguMjkgMTEuNjcgMTcuNSAxMS42N00yMCAxNC41N0MxOS4xMyAxNC40MSAxOC4yOSAxNC4zMyAxNy41IDE0LjMzQzE1LjY3IDE0LjMzIDE0LjE3IDE0LjYgMTMgMTUuMTNWMTYuODJDMTQuMTEgMTYuMTYgMTUuNiAxNS44MyAxNy41IDE1LjgzQzE4LjU0IDE1LjgzIDE5LjM4IDE1LjkxIDIwIDE2LjA3VjE0LjU3WiIgLz48L3N2Zz4%3D&logoColor=white
[fmt-eml]: https://img.shields.io/badge/EML-455A64?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGQ9Ik0yMiA2QzIyIDQuOSAyMS4xIDQgMjAgNEg0QzIuOSA0IDIgNC45IDIgNlYxOEMyIDE5LjEgMi45IDIwIDQgMjBIMjBDMjEuMSAyMCAyMiAxOS4xIDIyIDE4VjZNMjAgNkwxMiAxMUw0IDZIMjBNMjAgMThINFY4TDEyIDEzTDIwIDhWMThaIiAvPjwvc3ZnPg%3D%3D&logoColor=white
[fmt-msg]: https://img.shields.io/badge/MSG-0078D4?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgdmlld0JveD0iMCAwIDI0IDI0IiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxwYXRoIGQ9Ik03Ljg4IDEyLjA0cTAgLjQ1LS4xMS44Ny0uMS40MS0uMzMuNzQtLjIyLjMzLS41OC41Mi0uMzcuMi0uODcuMnQtLjg1LS4ycS0uMzUtLjIxLS41Ny0uNTUtLjIyLS4zMy0uMzMtLjc1LS4xLS40Mi0uMS0uODZ0LjEtLjg3cS4xLS40My4zNC0uNzYuMjItLjM0LjU5LS41NC4zNi0uMi44Ny0uMnQuODYuMnEuMzUuMjEuNTcuNTUuMjIuMzQuMzEuNzcuMS40My4xLjg4ek0yNCAxMnY5LjM4cTAgLjQ2LS4zMy44LS4zMy4zMi0uOC4zMkg3LjEzcS0uNDYgMC0uOC0uMzMtLjMyLS4zMy0uMzItLjhWMThIMXEtLjQxIDAtLjctLjMtLjMtLjI5LS4zLS43VjdxMC0uNDEuMy0uN1EuNTggNiAxIDZoNi41VjIuNTVxMC0uNDQuMy0uNzUuMy0uMy43NS0uM2gxMi45cS40NCAwIC43NS4zLjMuMy4zLjc1VjEwLjg1bDEuMjQuNzJoLjAxcS4xLjA3LjE4LjE4LjA3LjEyLjA3LjI1em0tNi04LjI1djNoM3YtM3ptMCA0LjV2M2gzdi0zem0wIDQuNXYxLjgzbDMuMDUtMS44M3ptLTUuMjUtOXYzaDMuNzV2LTN6bTAgNC41djNoMy43NXYtM3ptMCA0LjV2Mi4wM2wyLjQxIDEuNSAxLjM0LS44di0yLjczek05IDMuNzVWNmgybC4xMy4wMS4xMi4wNHYtMi4zek01Ljk4IDE1Ljk4cS45IDAgMS42LS4zLjctLjMyIDEuMTktLjg2LjQ4LS41NS43My0xLjI4LjI1LS43NC4yNS0xLjYxIDAtLjgzLS4yNS0xLjU1LS4yNC0uNzEtLjcxLTEuMjR0LTEuMTUtLjgzcS0uNjgtLjMtMS41NS0uMy0uOTIgMC0xLjY0LjMtLjcxLjMtMS4yLjg1LS41LjU0LS43NSAxLjMtLjI1Ljc0LS4yNSAxLjYzIDAgLjg1LjI2IDEuNTYuMjYuNzIuNzQgMS4yMy40OC41MiAxLjE3LjgxLjY5LjMgMS41Ni4zek03LjUgMjFoMTIuMzlMMTIgMTYuMDhWMTdxMCAuNDEtLjMuNy0uMjkuMy0uNy4zSDcuNXptMTUtLjEzdi03LjI0bC01LjkgMy41NFoiLz48L3N2Zz4%3D&logoColor=white
[fmt-png]: https://img.shields.io/badge/PNG-7E57C2?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGQ9Ik0xOSwxOUg1VjVIMTlNMTksM0g1QTIsMiAwIDAsMCAzLDVWMTlBMiwyIDAgMCwwIDUsMjFIMTlBMiwyIDAgMCwwIDIxLDE5VjVBMiwyIDAgMCwwIDE5LDNNMTMuOTYsMTIuMjlMMTEuMjEsMTUuODNMOS4yNSwxMy40N0w2LjUsMTdIMTcuNUwxMy45NiwxMi4yOVoiIC8%2BPC9zdmc%2B&logoColor=white
[fmt-jpeg]: https://img.shields.io/badge/JPEG-7E57C2?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGQ9Ik0xOSwxOUg1VjVIMTlNMTksM0g1QTIsMiAwIDAsMCAzLDVWMTlBMiwyIDAgMCwwIDUsMjFIMTlBMiwyIDAgMCwwIDIxLDE5VjVBMiwyIDAgMCwwIDE5LDNNMTMuOTYsMTIuMjlMMTEuMjEsMTUuODNMOS4yNSwxMy40N0w2LjUsMTdIMTcuNUwxMy45NiwxMi4yOVoiIC8%2BPC9zdmc%2B&logoColor=white
[fmt-tiff]: https://img.shields.io/badge/TIFF-7E57C2?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGQ9Ik0xOSwxOUg1VjVIMTlNMTksM0g1QTIsMiAwIDAsMCAzLDVWMTlBMiwyIDAgMCwwIDUsMjFIMTlBMiwyIDAgMCwwIDIxLDE5VjVBMiwyIDAgMCwwIDE5LDNNMTMuOTYsMTIuMjlMMTEuMjEsMTUuODNMOS4yNSwxMy40N0w2LjUsMTdIMTcuNUwxMy45NiwxMi4yOVoiIC8%2BPC9zdmc%2B&logoColor=white
[fmt-bmp]: https://img.shields.io/badge/BMP-7E57C2?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGQ9Ik0xOSwxOUg1VjVIMTlNMTksM0g1QTIsMiAwIDAsMCAzLDVWMTlBMiwyIDAgMCwwIDUsMjFIMTlBMiwyIDAgMCwwIDIxLDE5VjVBMiwyIDAgMCwwIDE5LDNNMTMuOTYsMTIuMjlMMTEuMjEsMTUuODNMOS4yNSwxMy40N0w2LjUsMTdIMTcuNUwxMy45NiwxMi4yOVoiIC8%2BPC9zdmc%2B&logoColor=white
[fmt-webp]: https://img.shields.io/badge/WebP-7E57C2?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGQ9Ik0xOSwxOUg1VjVIMTlNMTksM0g1QTIsMiAwIDAsMCAzLDVWMTlBMiwyIDAgMCwwIDUsMjFIMTlBMiwyIDAgMCwwIDIxLDE5VjVBMiwyIDAgMCwwIDE5LDNNMTMuOTYsMTIuMjlMMTEuMjEsMTUuODNMOS4yNSwxMy40N0w2LjUsMTdIMTcuNUwxMy45NiwxMi4yOVoiIC8%2BPC9zdmc%2B&logoColor=white
[fmt-xps]: https://img.shields.io/badge/XPS-0078D4?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgdmlld0JveD0iMCAwIDI0IDI0IiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxwYXRoIGQ9Ik0wIDB2MTEuNDA4aDExLjQwOFYwem0xMi41OTQgMHYxMS40MDhIMjRWMHpNMCAxMi41OTRWMjRoMTEuNDA4VjEyLjU5NHptMTIuNTk0IDBWMjRIMjRWMTIuNTk0eiIvPjwvc3ZnPg%3D%3D&logoColor=white
[fmt-svg]: https://img.shields.io/badge/SVG-FFB13B?style=flat-square&logo=svg&logoColor=white
[fmt-text]: https://img.shields.io/badge/Text-546E7A?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBmaWxsPSJ3aGl0ZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxwYXRoIGQ9Ik01LDNDMy44OSwzIDMsMy44OSAzLDVWMTlDMywyMC4xMSAzLjg5LDIxIDUsMjFIMTlDMjAuMTEsMjEgMjEsMjAuMTEgMjEsMTlWNUMyMSwzLjg5IDIwLjExLDMgMTksM0g1TTUsNUgxOVYxOUg1VjVNNyw3VjlIMTdWN0g3TTcsMTFWMTNIMTdWMTFIN003LDE1VjE3SDE0VjE1SDdaIiAvPjwvc3ZnPg%3D%3D&logoColor=white
[fmt-jsonl]: https://img.shields.io/badge/JSONL-000000?style=flat-square&logo=json&logoColor=white
[fmt-pydantic]: https://img.shields.io/badge/Pydantic-E92063?style=flat-square&logo=pydantic&logoColor=white

## Quick start

Doctopus requires **Python 3.12**. Install it from PyPI as `doctopus-ai`; the import name and command are `doctopus`:

```bash
pip install doctopus-ai                # base install with the Xberg engine
pip install "doctopus-ai[docling]"     # add optional engines as extras
doctopus parse path/to/document.pdf
```

To work from a checkout of this repository instead, use [uv](https://docs.astral.sh/uv/):

```bash
# Install the lightweight Xberg backend
uv sync

# Parse a document to Markdown
uv run doctopus parse path/to/document.pdf

# See which engine would be selected, without extracting
uv run doctopus plan path/to/document.pdf
```

OCR and layout engines may download model weights on first use. To add the optional Docling backend:

```bash
uv sync --extra docling
uv run doctopus parse path/to/document.pdf --mode accurate
```

The Docling extra adds substantial dependencies. Automatic routing requires at least 4,000 MB of reported available RAM before choosing Docling; explicit selection bypasses this check. Check engine availability with `uv run doctopus backends list --json`, which also reports supported extensions, capabilities, and reasons an engine is unavailable.

`uv sync` selects the extras for that environment: include all the extras you want to retain in the same command, for example `uv sync --extra dev --extra docling --extra paddleocr`.

## Engines

Every adapter returns the same `Document` schema, but field coverage varies. Some engines supply native layout blocks and bounding boxes; others supply Markdown from which Doctopus derives headings, paragraphs, lists, code, and tables. Install only the engines you need.

| Engine | Adapter capabilities | Runs | Measured peak RAM | Router threshold | Install |
| --- | --- | --- | --- | --- | --- |
| `xberg` | Light: text layer, OCR, tables, structure; PDF, Office, images, and text formats | In-process | 100–200 MB | — | Included |
| `markitdown` | Light: Office, HTML, spreadsheets, and text-layer PDFs; no OCR | In-process | ~200 MB | — | `uv sync --extra markitdown` |
| `pymupdf4llm` | Light: MuPDF text layer, layout, tables, OCR; PDF and supported ebook/vector formats | In-process | 0.4–0.8 GB | — | `uv sync --extra pymupdf4llm` (installs `pymupdf>=2.0`) |
| `docling` | Heavy: layout, tables, OCR; PDF, Office, and images | In-process | 2.2–3.2 GB | 4,000 MB | `uv sync --extra docling` |
| `paddleocr` | Heavy: PP-StructureV3 OCR, layout, tables; optional formulas | In-process, CPU; explicit selection | 2.7–2.8 GB | 3,500 MB | `uv sync --extra paddleocr` |
| `marker` | Heavy: layout, tables, equations; PDF and images | Sidecar CLI | ~0.9 GB, plus GPU memory | 1,500 MB | See setup below |
| `mineru` | Heavy: layout, tables, formulas; PDF, images, and Office | Sidecar CLI | 0.7–1.6 GB | 2,000 MB | See setup below |
| `ollama` | Heavy: vision-language transcription; PDF and images | Ollama service | ~0.1 GB in Doctopus; model held by the Ollama server | — | See setup below |

The extension lists in `doctopus backends list --json` describe what each adapter accepts. Availability checks do not run an extraction; some engines still need first-run model downloads or additional runtime resources.

Peak RAM is the high-water resident set size (RSS) for Doctopus and its child processes on the bundled fixtures (1–15 pages). It was measured on one Linux laptop with 14 GB of RAM and a 4 GB RTX 3050 GPU, with model weights already downloaded. Treat these figures as a guide, not a guarantee: they grow with page count and page size. Marker ran its layout model on the GPU, and that memory is not included. Ollama runs the model in its own server process, outside Doctopus's measurement. With `qwen3-vl:2b-instruct`, the server used about 3 GB of GPU memory. The router threshold is the free memory the router requires before it chooses that engine automatically. See [How routing works](#how-routing-works).

### Sidecar engines and Ollama

Marker and MinerU run as separate command-line tools in their own `uv tool` environments. Install their tools and download the models checked by Doctopus:

```bash
uv tool install --python 3.12 marker-pdf
uvx --from huggingface-hub hf download datalab-to/surya_layout2

uv tool install --python 3.12 mineru
mineru-kit models download --tier basic --small-backend onnx
```

Ensure `marker_single` and `mineru-kit` are on the server process's `PATH`. Marker checks for its cached layout checkpoint; additional checkpoints may download on its first extraction. It defaults to CPU `fast` mode. `DOCTOPUS_MARKER_MODE` is passed to Marker's `--mode`; `balanced` requires its GPU/VLM setup. MinerU defaults to the `basic` tier and Doctopus never passes its `--remote` flag. Sidecars have a 900-second timeout, configurable with `DOCTOPUS_SIDECAR_TIMEOUT`.

For Ollama, install the client extra, start an Ollama server, and pull the exact default model:

```bash
uv sync --extra ollama
ollama pull qwen3-vl:2b-instruct
uv run doctopus parse scan.pdf --backend ollama
```

The adapter connects to `OLLAMA_HOST` (default `http://127.0.0.1:11434`) and uses `DOCTOPUS_OLLAMA_MODEL` (default `qwen3-vl:2b-instruct`). PDF transcription is limited to the first 30 pages by default; change `DOCTOPUS_OLLAMA_MAX_PAGES` to adjust it. The result warns when pages were omitted. `DOCTOPUS_OLLAMA_MAX_TOKENS` sets the per-page generation budget (default 3000), and `DOCTOPUS_OLLAMA_KEEP_ALIVE` controls how long Ollama retains the model. Images are sent to the configured Ollama host, which may be on another machine.

### Choosing an engine

- **Per request:** `--backend` / `-b` on the CLI, the `backend` form field in REST, the `backend` argument on MCP tools, or the engine selector in the demo UI.
- **Per deployment:** `DOCTOPUS_BACKEND=marker`, or `doctopus serve --backend marker` / `doctopus mcp --backend marker`. This applies to requests that do not name an engine.
- **Router:** `auto`, the default, lets the router choose. A request that names an engine, or `auto`, always overrides the deployment default. The routing reasons say which source the choice came from.
- **Accurate mode:** `--mode accurate` prefers an available heavy engine that supports the format and passes the router's memory check. The default preference order is `docling,marker,mineru,ollama`; change it with `DOCTOPUS_HEAVY_ORDER`. This sets priority, not an allowlist. PaddleOCR remains excluded.

### PaddleOCR PP-StructureV3

Install the optional CPU backend and select it by name:

```bash
uv sync --extra paddleocr
uv run doctopus parse scan.pdf --backend paddleocr
uv run doctopus chunk ./scans --backend paddleocr --output scans.jsonl
```

PP-StructureV3 accepts PDFs and PNG, JPG/JPEG, BMP, and TIF/TIFF images. It runs locally on the CPU, downloads model weights on its first extraction, and reuses the loaded pipeline for subsequent requests in the same process. It uses OCR for every input; the Python option `ocr=False` is rejected. Optional dependencies and model weights are substantial, so allow additional disk space beyond the base installation. With the default settings below, it peaked at 2.7–2.8 GB of RAM on the fixtures. PaddleOCR's own default model set, with formula, seal and chart recognition enabled, used more than 10 GB on a one-page PDF and was stopped by the Linux out-of-memory (OOM) killer on a 14 GB machine.

The adapter defaults to `PP-OCRv5_mobile_det` and `PP-OCRv5_mobile_rec`. Formula, seal, and chart recognition, document orientation, unwarping, text-line orientation, and MKL-DNN are disabled by default. Set `DOCTOPUS_PADDLE_FORMULAS=1` to enable formula recognition, `DOCTOPUS_PADDLE_MKLDNN=1` to opt into MKL-DNN, or `DOCTOPUS_PADDLE_DET` / `DOCTOPUS_PADDLE_REC` to change the OCR models. These settings are read when the pipeline is first initialized.

Select `paddleocr` through Python (`doctopus.parse("scan.pdf", backend="paddleocr")`), the REST `backend` form field, MCP's `backend` argument, or the demo's engine selector. It returns blocks in engine-provided order, pages, bounding boxes, and tables, plus formula blocks when formula recognition is enabled. Tables may contain HTML within Markdown to retain merged cells; structured table `rows` remain `null`. The adapter does not report a quality score to the fallback heuristic. Extracted image assets are not exported, and a warning identifies potentially unresolved Markdown image links.

PaddleOCR is **explicit selection only** in the routing policy and is never an automatic fallback target. The extra installs CPU PaddlePaddle, and the adapter hard-codes `device="cpu"`; installing a GPU runtime alone does not enable GPU extraction.

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

Use `--help` on any command to see its options. The `parse` command supports `md`, `text`, and `json`; `chunk` emits JSONL.

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

The top-level `parse` and `chunk` helpers are synchronous and use `asyncio.run`. For async applications, use the gateway directly:

```python
from doctopus.core.gateway import Gateway

async def extract(path):
    return await Gateway().parse(path, backend="auto", mode="balanced")
```

`doctopus.parse` and `Gateway.parse` also accept `fallback` and `ocr`. `fallback=False` disables retries; `fallback=True` allows one alternative even for an explicit engine, except in `fast` mode. OCR controls are backend-specific: `--ocr` requests forced OCR where supported, while Docling and PyMuPDF4LLM currently use their engine defaults. The default file-size limit for Python, CLI, and MCP is 200 MiB.

### REST API and demo UI

```bash
uv run doctopus serve --port 8000
```

Open [localhost:8000](http://localhost:8000) for the drag-and-drop demo, or send a document to the API:

```bash
curl -F file=@paper.pdf -F mode=balanced http://localhost:8000/v1/parse
```

| Endpoint | Request / response |
| --- | --- |
| `POST /v1/parse` | Multipart `file`, optional `backend`, `mode`, `fallback`; returns a `Document` as JSON |
| `POST /v1/chunk` | Multipart `file`, optional `backend`, `mode`, `max_chars` (100–20,000; default 1500); returns a JSON array of chunks |
| `POST /v1/plan` | Multipart `file`, optional `backend`, `mode`; returns a routing decision without extraction |
| `GET /v1/backends` | Engine availability, formats, capabilities, and metadata |
| `GET /v1/health` | Status, version, deployment default, and ready engine IDs; no extraction check |

The three processing modes are `fast`, `balanced` (default), and `accurate`. Interactive API documentation is available at `/docs`. REST does not currently expose an `ocr` form field. Uploads default to 50 MiB, controlled by `DOCTOPUS_MAX_UPLOAD_MB`.

When `DOCTOPUS_API_TOKEN` is set, the parse, chunk, plan, and backends endpoints require `Authorization: Bearer <token>`:

```bash
curl -H "Authorization: Bearer $DOCTOPUS_API_TOKEN" \
  -F file=@paper.pdf -F backend=xberg http://localhost:8000/v1/parse
```

The health endpoint, demo page, and API documentation remain public. The bundled demo does not send authorization headers, so it cannot process files against a token-protected API without an authentication-aware proxy or UI changes.

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

The server exposes `parse_document`, `chunk_document`, `explain_routing`, `list_processing_backends`, and `compare_processors`.

- `parse_document` returns Markdown, metadata, tables, and processing details. Markdown is capped at 60,000 characters by default (`max_chars`); `truncated` and `total_chars` describe the full length. Blocks are included only with `include_blocks=True`. This tool returns a subset of the canonical document, rather than its full JSON schema.
- `chunk_document` returns paged chunks with `offset` and `limit` (default 50), plus `total`. Each call parses the file again.
- `compare_processors` tries every available engine with fallback disabled, reporting per-engine results or failures.

Paths may be relative to `--root` or absolute within it; paths and symlinks resolving outside the root are rejected.

## How routing works

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

PaddleOCR PP-StructureV3 is also available via explicit `--backend paddleocr` selection; it is excluded from automatic routing and escalation.

| Selection | Initial engine | Fallback |
| --- | --- | --- |
| `fast` | Xberg if available and it supports the extension; otherwise another compatible light engine | None |
| `balanced` (default) | Same light-engine preference as `fast` | Light → first compatible heavy engine passing the memory check; heavy → compatible light engine |
| `accurate` | First compatible, available heavy engine in priority order passing the memory check; otherwise the light-engine preference | Same bounded alternative policy as `balanced` |
| Explicit backend | The requested engine | None by default |

Inspection records the extension, size, PDF page count when available, and reported free RAM. Initial routing uses the extension, backend availability, requested mode, and memory thresholds; it does not classify layout complexity before extraction. If no compatible light engine is found, the current implementation selects the first available non-Paddle engine. `fast` disables retries but can still select a heavy engine in that case. Extraction still rejects an unsupported format.

Memory checks use each backend's declared `ram_mb` threshold, reported by `doctopus backends list --json`: Docling 4,000 MB, PaddleOCR 3,500 MB, MinerU 2,000 MB and Marker 1,500 MB. Each threshold is the measured peak plus headroom. Ollama has no declared threshold. Memory availability comes from Linux `/proc/meminfo`; unknown memory does not block automatic selection. This check does not enforce container memory limits. Explicit selection bypasses memory checks and automatic format selection.

An alternative is tried after extraction fails or output triggers a suspicion check. For inputs classified as PDF/image by the inspector (`pdf`, `png`, `jpg`, `jpeg`, `tiff`, `bmp`), stripped text below 20 characters per inspected page is suspicious; the page count defaults to one when unknown. Engine-reported quality below 0.5 is suspicious for any format. If the alternative fails, or also looks suspicious and yields no more text, the gateway keeps the original result and adds a warning. These are heuristics, not guarantees of extraction quality. Inspect the returned warnings and validate output for your documents.

## Output

Python parsing, CLI JSON output, and REST `/v1/parse` return a versioned `Document` containing:

| Field | Contents |
| --- | --- |
| `meta` | Filename, format, page count when known, size, content hash, and other metadata |
| `markdown`, `text` | Extracted document content |
| `blocks`, `tables`, `pages` | Structured content, including page and bounding-box information when available |
| `processing` | Backend, elapsed time, routing decision, fallback information, and warnings |

Unavailable optional scalar values remain `null`; collections such as `blocks`, `tables`, and `pages` may be empty. Some adapters derive structure from Markdown rather than native layout. The JSON output uses schema version `1.0`.

`processing.decision` records the initial selection; `processing.backend` identifies the engine that produced the returned result. `elapsed_ms` measures the returned engine's extraction attempt, excluding inspection, previous failed attempts, and response serialization. `peak_rss_mb` is a process/child high-water mark, not memory allocated by a single request.

### Chunks

`doctopus chunk` writes one chunk per line, ready for embedding, retrieval, or dataset building:

```json
{"id":"bdfaa68d8984-0000","kind":"text","text":"Example paragraph.","n_chars":18,"heading_path":["Introduction"],"pages":[1],"block_ids":["b0"],"table_id":null,"source":{"filename":"paper.pdf","document_id":"doc_example","content_hash":"bdfaa68d8984…","backend":"xberg","schema_version":"1.0"}}
```

- Headings close the current chunk and are recorded in `heading_path` for the chunks that follow.
- Text is packed up to `--max-chars` (default 1500). An over-long paragraph is split at sentence boundaries, then at spaces.
- Each table becomes one `table` chunk and is never split, so it may exceed `max_chars`. Tables with known pages are interleaved at page boundaries; tables with unknown pages go last. PaddleOCR table content can contain HTML. When there are no text-bearing blocks, chunks use page text or document text, skipping paragraphs found within a table's Markdown.
- Blocks labeled `page_header` and `page_footer` are dropped; engines without those labels cannot provide that filtering.
- Chunk IDs combine the content hash and ordinal position. They are repeatable for the same extraction and chunk settings; changing the backend or chunk size can change what a given ID contains. `source.document_id` is generated per parse.
- The CLI searches directories recursively for extensions supported by available engines. Byte-identical files are parsed before duplicate chunks are skipped. A file that fails is reported and the run continues; the exit code is 2 if any file failed.

## Benchmarks

These historical measurements cover Xberg, Docling, and automatic routing on the repository fixtures. The runner uses a fresh subprocess per file/engine pair; the saved results do not record hardware or dependency versions. Treat the figures as a snapshot, not a current performance guarantee or a comparison of all eight engines. Quality is scored only for fixtures with a reference.

| Document | Engine | Wall time | Peak RSS | Quality |
| --- | --- | ---: | ---: | --- |
| 15-page, two-column paper | Xberg | 0.37 s | 158 MB | — |
| | Docling | 18.12 s | 2,997 MB | — |
| 9-page paper | Xberg | 0.36 s | 170 MB | — |
| | Docling | 22.84 s | 3,221 MB | — |
| 3-page scan | Xberg | 0.24 s | 198 MB | OCR F1 0.967 |
| | Docling | 40.67 s | 3,152 MB | OCR F1 0.921 |
| Merged-header table | Xberg | 0.13 s | 99 MB | Cell-token coverage 1.000 |
| | Docling | 8.10 s | 2,581 MB | Cell-token coverage 1.000 |
| Two-column reading order | Xberg | 0.10 s | 98 MB | Order 1.000 |
| | Docling | 6.97 s | 2,183 MB | Order 1.000 |

On the three scored fixtures, Xberg matched or exceeded Docling's scores while using less time and memory. Table detection counts differed on the two papers, but there is no table ground truth for those papers. OCR F1 compares token counts against Xberg's extraction of the original digital pages; cell-token coverage checks whether expected cell tokens occur anywhere in the Markdown, not whether table structure or merged cells are correct. The order score compares the expected `P01`–`P24` marker sequence. The degraded scan has no recorded quality score.

To reproduce the benchmark suite:

```bash
uv sync --extra dev --extra docling
uv run python tests/make_fixtures.py
uv run python -m doctopus.bench.run --backends xberg,docling,auto
```

The generator uses the checked-in `fixtures/attention_2col.pdf`. Results are written to `bench_results/results.md` (git-ignored). Omit `--backends` to benchmark every currently available engine plus `auto`; model downloads and warm caches can affect timings even though each measurement uses a new process.

## Deploy

Build and start the default Xberg image with Docker Compose:

```bash
docker compose -f deploy/docker-compose.yml up --build
```

Build an image with the optional Docling backend:

```bash
docker build -f deploy/Dockerfile --build-arg EXTRA=docling -t doctopus:standard .
```

Compose defines one service. To use Docling through Compose, set `build.args.EXTRA: docling` and raise `mem_limit` in `deploy/docker-compose.yml`; building the separate `doctopus:standard` tag alone does not change the Compose service. The Docker build argument installs one optional extra; sidecar tools and an Ollama server are not included.

The Compose service sets a 512 MiB memory limit and publishes port 8000. This is the bundled base configuration, not a guarantee that every workload fits. Heavy engines need additional memory. Its volume preserves `/data`, with `XBERG_CACHE_DIR=/data/xberg`; other engines' model caches are not persisted by that volume unless configured there.

The local `serve` command binds to `127.0.0.1` by default; the container serves on `0.0.0.0`. Compose forwards `DOCTOPUS_API_TOKEN` from the host and sets `DOCTOPUS_MAX_UPLOAD_MB` to 50. Add `DOCTOPUS_BACKEND`, `DOCTOPUS_HEAVY_ORDER`, or other settings to the Compose environment explicitly if needed. API settings are read when the server starts. Uploaded documents are streamed to temporary files and removed after processing.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run python tests/mcp_smoke.py
```

Install `--extra docling` as well when developing or testing the optional backend.
Use `--extra paddleocr` for real PP-StructureV3 extraction. PaddleOCR adapter tests use representative engine results so the normal unit suite requires no Paddle models.

See [CONTRIBUTING.md](https://github.com/adityasasidhar/doctopus/blob/main/CONTRIBUTING.md) for the project layout and contribution workflow.

## License

Doctopus is [MIT licensed](https://github.com/adityasasidhar/doctopus/blob/main/LICENSE), as declared in `pyproject.toml`. Backend packages and model weights have their own licenses; the backend listing reports available license metadata, which may be incomplete and does not cover every dependency or model.
