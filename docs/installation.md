# Installation

Doctopus is published on PyPI as [`doctopus-ai`](https://pypi.org/project/doctopus-ai/). The import name and the command are both `doctopus`.

!!! note "Python 3.12"
    Doctopus currently requires **Python 3.12** (`>=3.12,<3.13`), because several engine packages do not yet support newer interpreters.

## Base install

The base install includes the lightweight [Xberg](concepts/engines.md) engine, the CLI, the REST API and the MCP server.

=== "pip"

    ```bash
    pip install doctopus-ai
    ```

=== "uv (project)"

    ```bash
    uv add doctopus-ai
    ```

=== "uv (CLI tool)"

    ```bash
    uv tool install --python 3.12 doctopus-ai
    ```

Check that it works and see which engines are available:

```bash
doctopus --help
doctopus backends list
```

OCR and layout engines may download model weights on first use.

## Optional engines

Install only the engines you need. Each one is an optional extra:

| Extra | Engine | Notes |
| --- | --- | --- |
| `docling` | [Docling](https://github.com/docling-project/docling) | Rich layout, tables and OCR. Substantial dependencies; needs ~4 GB free RAM for automatic selection. |
| `paddleocr` | PaddleOCR PP-StructureV3 | CPU OCR, layout and tables for scans. Explicit selection only. |
| `markitdown` | [MarkItDown](https://github.com/microsoft/markitdown) | Office, HTML, spreadsheets and text-layer PDFs; no OCR. |
| `pymupdf4llm` | PyMuPDF | **AGPL-3.0.** MuPDF text layer, layout and tables. |
| `ollama` | Ollama vision models | Needs a running Ollama server. |

```bash
pip install "doctopus-ai[docling]"
pip install "doctopus-ai[docling,markitdown]"   # several at once
```

[Marker](https://github.com/datalab-to/marker) and [MinerU](https://github.com/opendatalab/MinerU) run as sidecar command-line tools in their own environments, because their dependency pins conflict. See [Sidecar engines](concepts/engines.md#sidecar-engines-and-ollama).

## From source

```bash
git clone https://github.com/adityasasidhar/doctopus.git
cd doctopus
uv sync                         # base install
uv sync --extra docling         # add an engine
uv run doctopus parse path/to/document.pdf
```

`uv sync` selects the extras for that environment: include every extra you want to keep in the same command, for example `uv sync --extra dev --extra docling --extra paddleocr`.

## Docker

```bash
docker compose -f deploy/docker-compose.yml up --build
```

See [Deployment](deployment.md) for images with optional engines.
