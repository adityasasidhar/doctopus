# Configuration

Doctopus is configured with environment variables. Command-line flags, request fields and function arguments take precedence where they exist.

## Routing and engines

| Variable | Default | Effect |
| --- | --- | --- |
| `DOCTOPUS_BACKEND` | `auto` | Default engine for requests that do not name one. Same as `serve --backend` / `mcp --backend`. |
| `DOCTOPUS_HEAVY_ORDER` | `docling,marker,mineru,ollama` | Priority of heavy engines in `accurate` mode and for escalation. Sets priority, not an allowlist. |

## REST API

| Variable | Default | Effect |
| --- | --- | --- |
| `DOCTOPUS_API_TOKEN` | unset | When set, `/v1/parse`, `/v1/chunk`, `/v1/plan` and `/v1/backends` require `Authorization: Bearer <token>`. |
| `DOCTOPUS_MAX_UPLOAD_MB` | `50` | Upload size limit in MiB. |

API settings are read when the server starts.

## Sidecars (Marker, MinerU)

| Variable | Default | Effect |
| --- | --- | --- |
| `DOCTOPUS_SIDECAR_TIMEOUT` | `900` | Seconds before a sidecar extraction is stopped. |
| `DOCTOPUS_MARKER_MODE` | `fast` | Passed to Marker's `--mode`. `balanced` needs Marker's GPU/VLM setup. |
| `DOCTOPUS_MINERU_TIER` | `basic` | MinerU model tier. `standard` and `advanced` need a local VLM runtime. |
| `DOCTOPUS_MINERU_MODELS` | `~/.mineru/models` | Where Doctopus looks for downloaded MinerU models. |

## Ollama

| Variable | Default | Effect |
| --- | --- | --- |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama server. Page images are sent here. |
| `DOCTOPUS_OLLAMA_MODEL` | `qwen3-vl:2b-instruct` | Vision-language model used for transcription. |
| `DOCTOPUS_OLLAMA_MAX_PAGES` | `30` | Maximum PDF pages transcribed. The result warns when pages were omitted. |
| `DOCTOPUS_OLLAMA_MAX_TOKENS` | `3000` | Per-page generation budget. |
| `DOCTOPUS_OLLAMA_KEEP_ALIVE` | Ollama's default | How long Ollama keeps the model loaded. |

## PaddleOCR

Read when the pipeline is first initialized.

| Variable | Default | Effect |
| --- | --- | --- |
| `DOCTOPUS_PADDLE_FORMULAS` | off | Set to `1` to enable formula recognition. |
| `DOCTOPUS_PADDLE_MKLDNN` | off | Set to `1` to opt into MKL-DNN. |
| `DOCTOPUS_PADDLE_DET` | `PP-OCRv5_mobile_det` | OCR detection model. |
| `DOCTOPUS_PADDLE_REC` | `PP-OCRv5_mobile_rec` | OCR recognition model. |

## Limits

| Interface | File-size limit |
| --- | --- |
| Python, CLI, MCP | 200 MiB |
| REST | 50 MiB (`DOCTOPUS_MAX_UPLOAD_MB`) |
