"""Ollama VLM backend: one bad page never sinks the document; fences and empty answers are handled."""
import asyncio
import sys
from types import SimpleNamespace

import pytest

from doctopus.backends import ollama as ob
from doctopus.core.errors import ExtractionFailed


def install(monkeypatch, replies):
    """replies[i] is the page-i answer, or an Exception to raise for that page."""
    class Client:
        def __init__(self, host):
            pass

        async def chat(self, *, model, think, options, messages, keep_alive=None):
            r = replies.pop(0)
            if isinstance(r, Exception):
                raise r
            return SimpleNamespace(message=SimpleNamespace(content=r), done_reason="stop")

    monkeypatch.setitem(sys.modules, "ollama", SimpleNamespace(AsyncClient=Client))
    monkeypatch.setattr(ob.OllamaBackend, "_status", lambda self: (True, None))
    monkeypatch.setattr(ob, "_page_images", lambda path, n: ([(i + 1, b"png") for i in range(len(replies))], len(replies)))


def test_failed_page_is_skipped_with_warning(monkeypatch, tmp_path):
    install(monkeypatch, ["# One\n\nfirst page", RuntimeError("token repeat limit reached"), "```markdown\nthird\n```"])
    raw = asyncio.run(ob.OllamaBackend().process(tmp_path / "a.pdf"))
    assert [p.page for p in raw.pages] == [1, 3] and raw.page_count == 3
    assert raw.pages[1].text == "third" and "```" not in raw.markdown
    assert any(w.startswith("page 2:") and "repeat" in w for w in raw.warnings)


def test_empty_and_looping_pages_warn(monkeypatch, tmp_path):
    install(monkeypatch, ["", "row " * 400, "fine text"])
    raw = asyncio.run(ob.OllamaBackend().process(tmp_path / "a.pdf"))
    assert any("page 1:" in w and "no text" in w for w in raw.warnings)
    assert any("page 2:" in w and "repetitive" in w for w in raw.warnings)


def test_all_pages_failing_raises(monkeypatch, tmp_path):
    install(monkeypatch, [RuntimeError("boom"), ""])
    with pytest.raises(ExtractionFailed):
        asyncio.run(ob.OllamaBackend().process(tmp_path / "a.pdf"))
