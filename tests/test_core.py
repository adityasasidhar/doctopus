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
    def __init__(self, id, text="x " * 500, quality=1.0, fail=False, weight="light"):
        self.id, self.text, self.quality, self.fail, self.weight, self.calls = id, text, quality, fail, weight, 0

    def info(self):
        return BackendInfo(id=self.id, version="0", available=True, formats=["pdf"], capabilities={}, weight=self.weight)

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


def test_router_reasons_always_end_with_choice():
    d = router.decide({"ext": "pdf", "size_kb": 1}, mode="balanced", available=["xberg"])
    assert d.reasons[-1] == "→ xberg"
