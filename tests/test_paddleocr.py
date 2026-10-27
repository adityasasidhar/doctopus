"""PP-StructureV3 contract tests; no Paddle runtime or model downloads required."""
import asyncio
import builtins
import json
import sys
import threading
import time
from types import SimpleNamespace
from pathlib import Path

import pytest

from doctopus.backends import registry
from doctopus.backends import paddleocr as adapter
from doctopus.backends.base import RawResult
from doctopus.core.chunk import chunk
from doctopus.core.errors import BackendUnavailable, ExtractionFailed, InputRejected, UnsupportedFormat
from doctopus.core.gateway import Gateway
from doctopus.core.models import DocMeta, Document, Processing


HTML_TABLE = '<table><tr><td colspan="2">Sales</td></tr><tr><td>A</td><td>12</td></tr></table>'


def block(label, content, index=0, bbox=None):
    return {"block_label": label, "block_content": content, "block_id": index,
            "block_bbox": bbox, "block_order": index}


def page(blocks, index=0, markdown="", **extra):
    return SimpleNamespace(json={"res": {"page_index": index, "parsing_res_list": blocks, **extra}},
                           markdown={"markdown_texts": markdown, "markdown_images": {}})


@pytest.fixture
def installed(monkeypatch):
    monkeypatch.setattr(adapter.util, "find_spec", lambda name: object())
    monkeypatch.setattr(adapter.metadata, "version", lambda name: "3.4.0")


@pytest.fixture
def engine(monkeypatch, installed):
    state = SimpleNamespace(results=[], loads=0, calls=0, threads=[], active=0, max_active=0, options=None)

    class Pipeline:
        def __init__(self, **kwargs):
            state.loads += 1
            state.options = kwargs
            state.threads.append(threading.get_ident())

        def predict(self, input):
            state.calls += 1
            state.threads.append(threading.get_ident())
            state.active += 1
            state.max_active = max(state.max_active, state.active)
            try:
                time.sleep(0.005)  # allow concurrent requests to contend for the pipeline
                yield from state.results
            finally:
                state.active -= 1

    monkeypatch.setitem(sys.modules, "paddleocr", SimpleNamespace(PPStructureV3=Pipeline))
    return state


def test_registry_discovers_paddleocr_without_heavy_imports(monkeypatch, installed):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {"paddleocr", "paddle", "paddlex"}:
            raise AssertionError(f"unexpected heavy import: {name}")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(registry, "_cache", {})
    info = registry.get("paddleocr").info()
    assert info.available and info.weight == "heavy"
    assert info.capabilities["ocr"] and info.capabilities["tables"] and info.capabilities["bbox"]
    assert not info.capabilities["office"]


@pytest.mark.parametrize("missing", ["paddleocr", "paddle", "paddlex"])
def test_incomplete_install_is_actionable_without_loading_models(monkeypatch, installed, missing):
    monkeypatch.setattr(adapter.util, "find_spec", lambda name: None if name == missing else object())
    backend = adapter.PaddleOCRBackend()
    info = backend.info()
    assert not info.available
    assert missing in info.reason_unavailable and "--extra paddleocr" in info.reason_unavailable
    with pytest.raises(BackendUnavailable, match="--extra paddleocr"):
        asyncio.run(backend.process(Path("a.pdf")))


def test_old_paddleocr_is_not_reported_ready(monkeypatch, installed):
    monkeypatch.setattr(adapter.metadata, "version", lambda name: "2.9.1")
    assert not adapter.PaddleOCRBackend().info().available


@pytest.mark.parametrize("ext", ["pdf", ".PDF", "png", ".JPG", "jpeg", "bmp", "tif", "tiff"])
def test_supported_inputs(ext):
    assert adapter.PaddleOCRBackend().supports(ext)


def test_rejects_office_and_disabled_ocr(engine, tmp_path):
    backend = adapter.PaddleOCRBackend()
    with pytest.raises(UnsupportedFormat):
        asyncio.run(backend.process(tmp_path / "a.docx"))
    with pytest.raises(InputRejected, match="OCR"):
        asyncio.run(backend.process(tmp_path / "a.pdf", ocr=False))
    assert engine.loads == 0


def test_pdf_normalization_preserves_content_order_and_provenance(engine, tmp_path):
    engine.results = [
        page([block("doc_title", "Report", bbox=[1, 2, 90, 20]),
              block("paragraph_title", "Results", 1), block("text", "Revenue increased.", 2),
              block("table", HTML_TABLE, 3, [10, 30, 100, 80]),
              block("formula", "E=mc^2", 4), block("header", "Private", 5),
              block("footer", "1", 6), block("figure_title", "Figure 1", 7)],
             markdown="# Report\n\n## Results\n\nRevenue increased.\n\n" + HTML_TABLE, page_count=2),
        page([block("text", "Next page.")], index=1, markdown="Next page.", page_count=2),
    ]
    raw = asyncio.run(adapter.PaddleOCRBackend().process(tmp_path / "a.pdf"))
    assert raw.page_count == 2 and raw.ocr_used is True and raw.mime_type == "application/pdf"
    assert raw.quality is None
    assert raw.markdown.startswith("# Report") and raw.markdown.endswith("Next page.")
    assert "Sales" in raw.text and "<td" not in raw.text and "E=mc^2" in raw.text
    assert [p.page for p in raw.pages] == [1, 2]
    assert raw.pages[1].text == "Next page."
    assert [b.type for b in raw.blocks] == ["heading", "heading", "paragraph", "table", "formula",
                                         "page_header", "page_footer", "caption", "paragraph"]
    assert raw.blocks[0].bbox.x0 == 1 and raw.blocks[0].page == 1
    assert raw.blocks[0].level == 1 and raw.blocks[1].level == 2
    assert len({b.id for b in raw.blocks}) == len(raw.blocks)
    assert all(b.source == "paddleocr" for b in raw.blocks)
    assert raw.tables[0].markdown == HTML_TABLE and raw.tables[0].rows is None
    assert raw.tables[0].page == 1 and raw.tables[0].bbox.y0 == 30
    assert engine.options["device"] == "cpu"
    assert engine.options["use_doc_unwarping"] is False
    assert engine.options["use_doc_orientation_classify"] is False


def wrap(raw):
    return Document(meta=DocMeta(document_id="test", filename="a.pdf", format="pdf", size_bytes=1,
                                content_hash="ab" * 32),
                    processing=Processing(backend="paddleocr", mode="manual", elapsed_ms=1),
                    **{k: getattr(raw, k) for k in ("text", "markdown", "blocks", "tables", "pages")})


@pytest.mark.parametrize("with_text", [False, True])
def test_table_chunks_are_emitted_once(engine, tmp_path, with_text):
    blocks = [block("table", HTML_TABLE)]
    if with_text:
        blocks.insert(0, block("text", "Intro", 1))
    engine.results = [page(blocks, markdown=HTML_TABLE), page([block("table", HTML_TABLE)], index=1)]
    raw = asyncio.run(adapter.PaddleOCRBackend().process(tmp_path / "a.pdf"))
    chunks = chunk(wrap(raw))
    assert len(raw.tables) == len({t.id for t in raw.tables}) == 2
    assert len([c for c in chunks if c.kind == "table"]) == 2
    assert [c.text for c in chunks if c.kind == "text"] == (["Intro"] if with_text else [])
    assert "Sales" in raw.text and "Sales" in raw.pages[0].text


def test_image_and_empty_pages(engine, tmp_path):
    engine.results = [page([block("text", "Image text", bbox=[1, 2])], index=None, markdown="Image text")]
    backend = adapter.PaddleOCRBackend()
    raw = asyncio.run(backend.process(tmp_path / "a.PNG"))
    assert raw.page_count == 1 and raw.pages[0].page == 1 and raw.mime_type == "image/png"
    assert raw.blocks[0].bbox is None
    engine.results = [page([], index=0), page([], index=1)]
    raw = asyncio.run(backend.process(tmp_path / "a.pdf"))
    assert raw.page_count == 2 and raw.text == "" and len(raw.pages) == 2


def test_no_prediction_pages_is_an_error(engine, tmp_path):
    with pytest.raises(ExtractionFailed, match="no pages"):
        asyncio.run(adapter.PaddleOCRBackend().process(tmp_path / "a.pdf"))


def test_pipeline_reused_and_serialized_off_event_loop(engine, tmp_path):
    backend = adapter.PaddleOCRBackend()
    engine.results = [page([block("text", "Hello")], markdown="Hello")]
    main_thread = threading.get_ident()

    async def run():
        return await asyncio.gather(*(backend.process(tmp_path / "a.pdf") for _ in range(4)))

    assert len(asyncio.run(run())) == 4
    asyncio.run(backend.process(tmp_path / "a.pdf"))  # reuse across event loops, as in the CLI
    assert engine.loads == 1 and engine.calls == 5 and engine.max_active == 1
    assert all(t != main_thread for t in engine.threads)


def test_mid_prediction_failure_is_not_partial_success(engine, tmp_path):
    def broken():
        yield page([block("text", "partial")])
        raise RuntimeError("prediction failed")

    engine.results = broken()
    with pytest.raises(ExtractionFailed, match="prediction failed"):
        asyncio.run(adapter.PaddleOCRBackend().process(tmp_path / "a.pdf"))


def test_missing_doc_parser_dependencies_are_actionable(monkeypatch, installed, tmp_path):
    def broken(**kwargs):
        raise ImportError("Please install the doc-parser extra")

    monkeypatch.setitem(sys.modules, "paddleocr", SimpleNamespace(PPStructureV3=broken))
    with pytest.raises(BackendUnavailable, match="--extra paddleocr"):
        asyncio.run(adapter.PaddleOCRBackend().process(tmp_path / "a.pdf"))


@pytest.fixture
def paddle_gateway(monkeypatch, engine, tmp_path):
    engine.results = [page([block("text", "Extracted document content.")], markdown="Extracted document content.")]
    backend = adapter.PaddleOCRBackend()
    monkeypatch.setattr(registry, "_cache", {"paddleocr": backend})
    monkeypatch.setattr(registry, "_FACTORIES", {"paddleocr": lambda: backend})
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF-1.4 fake")
    return path


def test_explicit_gateway_selection(paddle_gateway):
    doc = asyncio.run(Gateway().parse(paddle_gateway, backend="paddleocr"))
    assert doc.processing.backend == "paddleocr" and doc.processing.mode == "manual"
    assert doc.processing.ocr_used is True and doc.blocks[0].source == "paddleocr"
    assert chunk(doc)[0].source.backend == "paddleocr"


@pytest.mark.parametrize("mode", ["fast", "balanced", "accurate"])
def test_automatic_routing_rejects_paddle_only_install(paddle_gateway, mode):
    with pytest.raises(BackendUnavailable, match="explicit"):
        Gateway().plan(paddle_gateway, mode=mode)


def test_paddle_is_not_an_automatic_fallback(paddle_gateway, monkeypatch, engine):
    class Light:
        id = "xberg"

        def info(self):
            return registry.get("paddleocr").info().model_copy(update={"id": "xberg", "weight": "light"})

        def supports(self, ext):
            return True

        async def process(self, path, *, ocr=None):
            return RawResult(text="", markdown="", quality=0.1)

    monkeypatch.setitem(registry._FACTORIES, "xberg", Light)
    doc = asyncio.run(Gateway().parse(paddle_gateway))
    assert doc.processing.backend == "xberg" and engine.calls == 0


def test_missing_paddle_runtime_error_has_install_hint(monkeypatch, paddle_gateway):
    monkeypatch.setattr(adapter.util, "find_spec", lambda name: None if name == "paddle" else object())
    with pytest.raises(ExtractionFailed, match="--extra paddleocr"):
        asyncio.run(Gateway().parse(paddle_gateway, backend="paddleocr"))


def test_rest_parse_chunk_and_demo_support_paddle(paddle_gateway, monkeypatch):
    from fastapi.testclient import TestClient
    from doctopus.interfaces import api

    monkeypatch.setattr(api, "TOKEN", None)
    with TestClient(api.app) as client:
        files = {"file": ("scan.pdf", paddle_gateway.read_bytes(), "application/pdf")}
        parsed = client.post("/v1/parse", files=files, data={"backend": "paddleocr"})
        assert parsed.status_code == 200
        assert parsed.json()["processing"]["backend"] == "paddleocr"
        assert parsed.json()["meta"]["filename"] == "scan.pdf"
        chunks = client.post("/v1/chunk", files=files, data={"backend": "paddleocr"})
        assert chunks.status_code == 200 and chunks.json()[0]["source"]["backend"] == "paddleocr"
        backends = {b["id"]: b for b in client.get("/v1/backends").json()}
        assert backends["paddleocr"]["available"] is True
        assert "fetch('/v1/backends')" in client.get("/").text


def test_cli_parse_and_chunk_accept_paddle(paddle_gateway):
    from typer.testing import CliRunner
    from doctopus.interfaces.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["parse", str(paddle_gateway), "--backend", "paddleocr", "--format", "json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["processing"]["backend"] == "paddleocr"
    result = runner.invoke(app, ["chunk", str(paddle_gateway), "--backend", "paddleocr"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["source"]["backend"] == "paddleocr"
    listed = runner.invoke(app, ["backends", "list", "--json"])
    assert listed.exit_code == 0
    assert any(b["id"] == "paddleocr" for b in json.loads(listed.stdout))


def test_mcp_schema_and_calls_accept_paddle(paddle_gateway):
    from doctopus.interfaces.mcp_server import build_server

    async def run():
        server = build_server(paddle_gateway.parent)
        tools = {t.name: t for t in await server.list_tools()}
        for name in ("parse_document", "chunk_document"):
            schema = tools[name].input_schema["properties"]["backend"]
            choices = [value for option in schema["anyOf"] for value in option.get("enum", [])]
            assert "paddleocr" in choices
            response = await server.call_tool(name, {"path": paddle_gateway.name, "backend": "paddleocr"})
            content = response.content
            data = json.loads(content[0].text)
            if name == "parse_document":
                assert data["processing"]["backend"] == "paddleocr"
            else:
                assert data["chunks"][0]["source"]["backend"] == "paddleocr"

    asyncio.run(run())


def test_paddle_stays_opt_in_with_configured_heavy_order(paddle_gateway, monkeypatch):
    from doctopus.routing import router

    monkeypatch.setattr(router, "HEAVY_ORDER", ["paddleocr", "docling"])
    paddle = registry.get("paddleocr").info()
    docling = paddle.model_copy(update={"id": "docling", "ram_mb": 4000})
    info = {"ext": "pdf", "size_kb": 1, "mem_available_mb": 16000}
    backends = [paddle, docling]
    assert [b.id for b in router.heavy_candidates(backends, info)] == ["docling"]
    assert router.decide(info, mode="accurate", backends=backends).backend == "docling"
    assert router.escalation_target("xberg", [paddle], info) is None
