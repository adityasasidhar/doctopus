# Engines

Every adapter returns the same [`Document`](output.md) schema, but field coverage varies. Some engines supply native layout blocks and bounding boxes; others supply Markdown from which Doctopus derives headings, paragraphs, lists, code, and tables. Install only the engines you need.

| Engine | Adapter capabilities | Runs | Measured peak RAM | Router threshold | Install |
| --- | --- | --- | --- | --- | --- |
| `xberg` | Light: text layer, OCR, tables, structure; PDF, Office, images, and text formats | In-process | 100–200 MB | — | Included |
| `markitdown` | Light: Office, HTML, spreadsheets, and text-layer PDFs; no OCR | In-process | ~200 MB | — | `doctopus-ai[markitdown]` |
| `pymupdf4llm` | Light: MuPDF text layer, layout, tables, OCR; PDF and supported ebook/vector formats | In-process | 0.4–0.8 GB | — | `doctopus-ai[pymupdf4llm]` (AGPL-3.0) |
| `docling` | Heavy: layout, tables, OCR; PDF, Office, and images | In-process | 2.2–3.2 GB | 4,000 MB | `doctopus-ai[docling]` |
| `paddleocr` | Heavy: PP-StructureV3 OCR, layout, tables; optional formulas | In-process, CPU; explicit selection | 2.7–2.8 GB | 3,500 MB | `doctopus-ai[paddleocr]` |
| `marker` | Heavy: layout, tables, equations; PDF and images | Sidecar CLI | ~0.9 GB, plus GPU memory | 1,500 MB | [Sidecar setup](#sidecar-engines-and-ollama) |
| `mineru` | Heavy: layout, tables, formulas; PDF, images, and Office | Sidecar CLI | 0.7–1.6 GB | 2,000 MB | [Sidecar setup](#sidecar-engines-and-ollama) |
| `ollama` | Heavy: vision-language transcription; PDF and images | Ollama service | ~0.1 GB in Doctopus; model held by the Ollama server | — | `doctopus-ai[ollama]` + [setup](#ollama) |

`doctopus backends list --json` reports the extensions each adapter accepts, its capabilities, license metadata, and why an engine is unavailable. Availability checks do not run an extraction; some engines still need first-run model downloads or additional runtime resources.

!!! info "About the memory figures"
    Peak RAM is the high-water resident set size (RSS) for Doctopus and its child processes on the bundled fixtures (1–15 pages), measured on one Linux laptop with 14 GB of RAM and a 4 GB RTX 3050 GPU, with model weights already downloaded. Treat them as a guide, not a guarantee: they grow with page count and page size. Marker ran its layout model on the GPU, and that memory is not included. Ollama runs the model in its own server process, outside Doctopus's measurement. The router threshold is the free memory the router requires before it chooses that engine automatically.

## Choosing an engine

- **Per request:** `--backend` / `-b` on the CLI, the `backend` form field in REST, the `backend` argument on MCP tools, `backend=` in Python, or the engine selector in the demo UI.
- **Per deployment:** `DOCTOPUS_BACKEND=marker`, or `doctopus serve --backend marker` / `doctopus mcp --backend marker`. This applies to requests that do not name an engine.
- **Router:** `auto`, the default, lets the router choose. A request that names an engine, or `auto`, always overrides the deployment default. The routing reasons say which source the choice came from.
- **Accurate mode:** `--mode accurate` prefers an available heavy engine that supports the format and passes the router's memory check. The default preference order is `docling,marker,mineru,ollama`; change it with `DOCTOPUS_HEAVY_ORDER`. This sets priority, not an allowlist. PaddleOCR remains excluded.

## Sidecar engines and Ollama

### Marker and MinerU

Marker and MinerU run as separate command-line tools in their own `uv tool` environments, because their dependency pins conflict. Install their tools and download the models checked by Doctopus:

```bash
uv tool install --python 3.12 marker-pdf
uvx --from huggingface-hub hf download datalab-to/surya_layout2

uv tool install --python 3.12 mineru
mineru-kit models download --tier basic --small-backend onnx
```

Ensure `marker_single` and `mineru-kit` are on the server process's `PATH`.

- Marker checks for its cached layout checkpoint; additional checkpoints may download on its first extraction. It defaults to CPU `fast` mode. `DOCTOPUS_MARKER_MODE` is passed to Marker's `--mode`; `balanced` requires its GPU/VLM setup.
- MinerU defaults to the `basic` tier, and Doctopus never passes its `--remote` flag.
- Sidecars have a 900-second timeout, configurable with `DOCTOPUS_SIDECAR_TIMEOUT`.

### Ollama

Install the client extra, start an Ollama server, and pull the default model:

```bash
pip install "doctopus-ai[ollama]"
ollama pull qwen3-vl:2b-instruct
doctopus parse scan.pdf --backend ollama
```

The adapter connects to `OLLAMA_HOST` (default `http://127.0.0.1:11434`) and uses `DOCTOPUS_OLLAMA_MODEL` (default `qwen3-vl:2b-instruct`). With that model the server used about 3 GB of GPU memory.

- PDF transcription is limited to the first 30 pages by default (`DOCTOPUS_OLLAMA_MAX_PAGES`). The result warns when pages were omitted.
- `DOCTOPUS_OLLAMA_MAX_TOKENS` sets the per-page generation budget (default 3000).
- `DOCTOPUS_OLLAMA_KEEP_ALIVE` controls how long Ollama retains the model.

!!! warning
    Page images are sent to the configured Ollama host, which may be on another machine.

## PaddleOCR PP-StructureV3

Install the optional CPU backend and select it by name:

```bash
pip install "doctopus-ai[paddleocr]"
doctopus parse scan.pdf --backend paddleocr
doctopus chunk ./scans --backend paddleocr --output scans.jsonl
```

PP-StructureV3 accepts PDFs and PNG, JPG/JPEG, BMP, and TIF/TIFF images. It runs locally on the CPU, downloads model weights on its first extraction, and reuses the loaded pipeline for later requests in the same process. It uses OCR for every input; the Python option `ocr=False` is rejected.

With the defaults below it peaked at 2.7–2.8 GB of RAM on the fixtures. PaddleOCR's own default model set, with formula, seal and chart recognition enabled, used more than 10 GB on a one-page PDF and was stopped by the Linux OOM killer on a 14 GB machine.

The adapter defaults to `PP-OCRv5_mobile_det` and `PP-OCRv5_mobile_rec`. Formula, seal, and chart recognition, document orientation, unwarping, text-line orientation, and MKL-DNN are disabled by default.

| Variable | Effect |
| --- | --- |
| `DOCTOPUS_PADDLE_FORMULAS=1` | Enable formula recognition |
| `DOCTOPUS_PADDLE_MKLDNN=1` | Opt into MKL-DNN |
| `DOCTOPUS_PADDLE_DET`, `DOCTOPUS_PADDLE_REC` | Change the OCR detection and recognition models |

These settings are read when the pipeline is first initialized.

It returns blocks in engine-provided order, pages, bounding boxes, and tables, plus formula blocks when formula recognition is enabled. Tables may contain HTML within Markdown to retain merged cells; structured table `rows` remain `null`. The adapter does not report a quality score to the fallback heuristic. Extracted image assets are not exported, and a warning identifies potentially unresolved Markdown image links.

PaddleOCR is **explicit selection only** and is never an automatic fallback target. The extra installs CPU PaddlePaddle and the adapter hard-codes `device="cpu"`; installing a GPU runtime alone does not enable GPU extraction.
