# PaddleOCR PP-StructureV3 backend

## Intent and scope

Add the requested PP-StructureV3 engine to Doctopus through its existing
`Backend` protocol. The public backend ID is `paddleocr`. Support local PDF,
PNG, JPG/JPEG, BMP, and TIF/TIFF inputs and return the existing schema version
`1.0`. This change is limited to PaddleOCR integration.

## Approach

Use a lazy, in-process Python adapter around `paddleocr.PPStructureV3`, matching
the existing Docling adapter. A separate HTTP service would introduce endpoint
configuration and a deployment dependency that this request does not need.
Making PaddleOCR mandatory would defeat the lightweight default installation.
The selected engine is PP-StructureV3, as requested by the user; these integration
details are proposed implementation choices.

## Behavior

- Add the optional `paddleocr` extra, including the PaddleOCR document-parsing
  dependencies and CPU PaddlePaddle runtime. Keep imports and model loading lazy.
- Expose `paddleocr` in backend discovery, the CLI help, MCP backend arguments,
  and the demo engine selector. Python and REST already accept backend strings.
- Initialize the pipeline on first extraction and reuse it. Run initialization,
  prediction iteration, and normalization outside the async event loop;
  serialize access to the shared pipeline.
- Map per-page prediction results into `RawResult`: engine Markdown, plain text,
  pages, typed blocks, tables, and bounding boxes. Convert PDF page indices to
  Doctopus's one-based page numbers and use page 1 for image inputs.
- Preserve engine reading order. Recognize heading, paragraph, caption, formula,
  header, and footer labels; link table blocks to canonical tables using matching
  IDs so chunking emits each table once. Engine HTML tables may remain embedded in Markdown. Leave cell
  grids and confidence unknown unless the engine supplies compatible values.
- PP-StructureV3 inherently uses OCR. Reject `ocr=False` with an actionable input
  error rather than pretending OCR was disabled.
- Report missing optional dependencies and processing failures using Doctopus
  errors. Listing engines must not import Paddle or download models.
- Initially require explicit selection. Exclude this unbenchmarked heavy engine
  from automatic initial selection and fallback, while preserving the existing
  routing policy and one-retry limit. Automatic use can follow measured results.

## Verification and limits

Use representative fake Paddle results to test normalization, missing packages,
lazy execution, concurrency, and errors without downloading models. Exercise
selection through the gateway, REST, CLI, and MCP and run the existing suite.
Resolve the optional dependency lock and document install/usage commands.
A real inference smoke test is conditional on runtime/model availability;
report clearly if only adapter and interface tests were possible.

Reference: [official PP-StructureV3 Python API](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PP-StructureV3.html).
