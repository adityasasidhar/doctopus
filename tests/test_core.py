"""Fast unit tests: routing policy, RAM gate, bounded escalation, safety. Fake backends -> no heavy imports."""
import asyncio
from pathlib import Path

import pytest

from doctopus.backends import registry
from doctopus.backends.base import RawResult
from doctopus.core.errors import ExtractionFailed, InputRejected
from doctopus.core.gateway import Gateway
from doctopus.core.models import BackendInfo
from doctopus.routing import router


class Fake:
    def __init__(self, id, text="x " * 500, quality=1.0, fail=False, weight="light", formats=("pdf",)):
        self.id, self.text, self.quality, self.fail, self.weight, self.calls = id, text, quality, fail, weight, 0
        self.formats = list(formats)

    def info(self):
        return BackendInfo(id=self.id, version="0", available=True, formats=self.formats, capabilities={},
                           weight=self.weight, ram_mb=4000 if self.weight == "heavy" else None)

    def supports(self, ext):
        return True

    async def process(self, path, *, ocr=None):
        self.calls += 1
        if self.fail:
            raise RuntimeError("boom")
        return RawResult(markdown=self.text, text=self.text, page_count=1, quality=self.quality)


@pytest.fixture
def pdf(tmp_path):
    p = tmp_path / "a.pdf"
    p.write_bytes(b"%PDF-1.4 fake")
    return p


@pytest.fixture
def fakes(monkeypatch):
    f = {"xberg": Fake("xberg"), "docling": Fake("docling", weight="heavy")}
    monkeypatch.setattr(registry, "_cache", dict(f))
    monkeypatch.setattr(registry, "_FACTORIES", {k: (lambda k=k: f[k]) for k in f})
    monkeypatch.setattr("doctopus.routing.inspect.mem_available_mb", lambda: 16000)
    return f


def run(c):
    return asyncio.run(c)


def test_default_is_light_engine(fakes, pdf):
    d = run(Gateway().parse(pdf))
    assert d.processing.backend == "xberg" and d.processing.fallback_from is None
    assert d.processing.decision.reasons[-1] == "→ xberg"


def test_accurate_prefers_docling_when_ram_allows(fakes, pdf):
    assert run(Gateway().parse(pdf, mode="accurate")).processing.backend == "docling"


def test_accurate_degrades_when_ram_too_low(fakes, pdf, monkeypatch):
    monkeypatch.setattr("doctopus.routing.inspect.mem_available_mb", lambda: 1200)
    d = run(Gateway().parse(pdf, mode="accurate"))
    assert d.processing.backend == "xberg"
    assert any("only 1.2 GB" in r for r in d.processing.decision.reasons)


def test_escalates_once_on_bad_output(fakes, pdf):
    fakes["xberg"].text = ""
    d = run(Gateway().parse(pdf))
    assert d.processing.backend == "docling" and d.processing.fallback_from == "xberg"
    assert fakes["xberg"].calls == 1 and fakes["docling"].calls == 1


def test_escalation_never_returns_a_worse_answer(fakes, pdf):
    fakes["xberg"].text, fakes["xberg"].quality = "garbled " * 3, 0.2
    fakes["docling"].text = ""
    d = run(Gateway().parse(pdf))
    assert d.processing.backend == "xberg" and d.text.startswith("garbled")
    assert any("did no better" in w for w in d.processing.warnings)


def test_escalation_crash_keeps_light_result(fakes, pdf):
    fakes["xberg"].quality, fakes["docling"].fail = 0.2, True
    d = run(Gateway().parse(pdf))
    assert d.processing.backend == "xberg"
    assert any("escalation failed" in w for w in d.processing.warnings)


def test_no_escalation_when_ram_low(fakes, pdf, monkeypatch):
    monkeypatch.setattr("doctopus.routing.inspect.mem_available_mb", lambda: 1000)
    fakes["xberg"].quality = 0.1
    d = run(Gateway().parse(pdf))
    assert d.processing.backend == "xberg" and fakes["docling"].calls == 0


def test_fast_never_escalates(fakes, pdf):
    fakes["xberg"].text = ""
    run(Gateway().parse(pdf, mode="fast"))
    assert fakes["docling"].calls == 0


def test_manual_has_no_silent_substitution(fakes, pdf):
    fakes["docling"].fail = True
    with pytest.raises(ExtractionFailed):
        run(Gateway().parse(pdf, backend="docling"))
    assert fakes["xberg"].calls == 0


def test_fallback_is_bounded_to_one_retry(fakes, pdf):
    fakes["xberg"].fail = fakes["docling"].fail = True
    with pytest.raises(ExtractionFailed):
        run(Gateway().parse(pdf))
    assert fakes["xberg"].calls == 1 and fakes["docling"].calls == 1


def test_rejects_oversize_and_missing(fakes, pdf, tmp_path):
    with pytest.raises(InputRejected):
        run(Gateway(max_bytes=3).parse(pdf))
    with pytest.raises(InputRejected):
        run(Gateway().parse(tmp_path / "nope.pdf"))


def test_api_manual_backend_never_substitutes(fakes, pdf):
    from fastapi.testclient import TestClient

    from doctopus.interfaces.api import app

    fakes["docling"].fail = True
    with pdf.open("rb") as fh:
        r = TestClient(app).post("/v1/parse", files={"file": ("a.pdf", fh)}, data={"backend": "docling"})
    assert r.status_code == 422 and fakes["xberg"].calls == 0


def test_api_chunk_returns_chunks(fakes, pdf):
    from fastapi.testclient import TestClient

    from doctopus.interfaces.api import app

    with pdf.open("rb") as fh:
        r = TestClient(app).post("/v1/chunk", files={"file": ("a.pdf", fh)}, data={"max_chars": "300"})
    cs = r.json()
    assert r.status_code == 200 and len(cs) > 1 and all(c["n_chars"] <= 300 for c in cs)
    assert cs[0]["source"]["filename"] == "a.pdf" and cs[0]["source"]["backend"] == "xberg"


def info(id, weight="light", formats=("pdf",), ram_mb=None, available=True):
    return BackendInfo(id=id, available=available, formats=list(formats), capabilities={}, weight=weight, ram_mb=ram_mb)


def test_router_reasons_always_end_with_choice():
    d = router.decide({"ext": "pdf", "size_kb": 1}, mode="balanced", backends=[info("xberg")])
    assert d.reasons[-1] == "→ xberg"


def test_accurate_walks_heavy_order_skipping_what_does_not_fit(monkeypatch):
    monkeypatch.setattr(router, "HEAVY_ORDER", ["docling", "marker", "ollama"])
    bs = [info("xberg"), info("docling", "heavy", ram_mb=4000), info("marker", "heavy", ram_mb=3000),
          info("ollama", "heavy", formats=("png",))]
    d = router.decide({"ext": "pdf", "size_kb": 1, "mem_available_mb": 3500}, mode="accurate", backends=bs)
    assert d.backend == "marker" and "docling needs ~4 GB" in d.reasons[1]
    d = router.decide({"ext": "png", "size_kb": 1, "mem_available_mb": 3500}, mode="accurate", backends=bs)
    assert d.backend == "ollama"  # only heavy engine that reads png


def test_escalation_target_is_heavy_for_light_and_light_for_heavy():
    bs = [info("markitdown"), info("xberg"), info("docling", "heavy", ram_mb=4000)]
    assert router.escalation_target("xberg", bs, {"ext": "pdf", "mem_available_mb": 9000}) == "docling"
    assert router.escalation_target("xberg", bs, {"ext": "pdf", "mem_available_mb": 1000}) is None
    assert router.escalation_target("docling", bs, {"ext": "pdf"}) == "xberg"


def test_light_default_respects_format():
    bs = [info("xberg", formats=("pdf",)), info("markitdown", formats=("pdf", "xls"))]
    assert router.decide({"ext": "xls", "size_kb": 1}, mode="balanced", backends=bs).backend == "markitdown"


def test_mcp_engine_choices_match_registry():
    import typing

    from doctopus.interfaces.mcp_server import Engine

    assert set(typing.get_args(Engine)) - {"auto"} == set(registry._FACTORIES)


def test_default_backend_applies_only_when_request_names_none(fakes, pdf, monkeypatch):
    monkeypatch.setenv("DOCTOPUS_BACKEND", "docling")
    assert run(Gateway().parse(pdf)).processing.backend == "docling"  # env default
    assert run(Gateway().parse(pdf, backend="auto")).processing.backend == "xberg"  # explicit auto wins
    assert run(Gateway(default_backend="xberg").parse(pdf)).processing.backend == "xberg"  # ctor beats env


def test_unknown_default_backend_fails_fast(fakes, monkeypatch):
    from doctopus.core.errors import BackendUnavailable

    with pytest.raises(BackendUnavailable):
        Gateway(default_backend="nope")
