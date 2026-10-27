"""Chunker: pure function over the canonical Document, so tests build Documents by hand."""
from doctopus.core.chunk import chunk
from doctopus.core.models import Block, DocMeta, Document, Page, Processing, Table


def doc(blocks=(), tables=(), pages=(), text=""):
    return Document(
        meta=DocMeta(document_id="doc_x", filename="a.pdf", format="pdf", size_bytes=1, content_hash="ab" * 32),
        markdown=text, text=text, blocks=list(blocks), tables=list(tables), pages=list(pages),
        processing=Processing(backend="xberg", mode="balanced", elapsed_ms=1),
    )


def b(i, type, text, page=1, level=None):
    return Block(id=f"b{i}", type=type, text=text, page=page, level=level, source="xberg")


def test_headings_set_context_and_split_sections():
    d = doc([b(0, "heading", "Intro", level=1), b(1, "paragraph", "alpha"),
             b(2, "heading", "Method", level=1), b(3, "heading", "Data", level=2), b(4, "paragraph", "beta")])
    cs = chunk(d)
    assert [c.text for c in cs] == ["alpha", "beta"]
    assert cs[0].heading_path == ["Intro"] and cs[1].heading_path == ["Method", "Data"]


def test_size_budget_packs_and_splits_paragraphs():
    d = doc([b(i, "paragraph", "word " * 40) for i in range(5)])  # 200 chars each
    cs = chunk(d, max_chars=450)
    assert all(c.n_chars <= 450 for c in cs) and len(cs) == 3
    big = chunk(doc([b(0, "paragraph", "Sentence one is here. " * 100)]), max_chars=300)
    assert len(big) > 1 and all(c.n_chars <= 300 for c in big)


def test_tables_are_whole_chunks_in_page_order():
    d = doc([b(0, "paragraph", "p1", page=1), b(1, "paragraph", "p2", page=2)],
            tables=[Table(id="t0", page=1, markdown="| a | b |\n|---|---|\n| 1 | 2 |", source="xberg")])
    cs = chunk(d, max_chars=5)
    assert [c.kind for c in cs] == ["text", "table", "text"]
    assert cs[1].text.startswith("| a |") and cs[1].pages == [1] and cs[1].table_id == "t0"


def test_page_furniture_dropped_and_pages_tracked():
    d = doc([b(0, "page_header", "ACME CONFIDENTIAL"), b(1, "paragraph", "x", page=1),
             b(2, "paragraph", "y", page=2), b(3, "page_footer", "3", page=2)])
    (c,) = chunk(d)
    assert c.text == "x\n\ny" and c.pages == [1, 2] and c.block_ids == ["b1", "b2"]


def test_falls_back_to_pages_then_text_when_no_blocks():
    cs = chunk(doc(pages=[Page(page=1, text="one\n\ntwo"), Page(page=2, text="three")]))
    assert [c.pages for c in cs] == [[1, 2]] and "three" in cs[0].text
    assert chunk(doc(text="just text"))[0].pages == []


def test_page_fallback_does_not_duplicate_tables():
    md = "| a | b |\n| --- | --- |\n| 1 | 2 |"
    d = doc(pages=[Page(page=1, text=f"Intro line\n\n{md}")], tables=[Table(id="t0", page=1, markdown=md, source="xberg")])
    assert [(c.kind, c.text) for c in chunk(d)] == [("text", "Intro line"), ("table", md)]


def test_ids_are_deterministic_and_carry_provenance():
    d = doc([b(0, "paragraph", "alpha")])
    a, b_ = chunk(d)[0], chunk(d)[0]
    assert a.id == b_.id == "abababababab-0000"
    assert a.source.filename == "a.pdf" and a.source.backend == "xberg" and a.source.content_hash == "ab" * 32


def test_table_blocks_without_a_canonical_table_keep_their_text():
    d = doc([b(0, "table", "Orphan table text")])
    assert [c.text for c in chunk(d)] == ["Orphan table text"]


def test_empty_layout_blocks_still_fall_back_to_page_text():
    d = doc([b(0, "paragraph", "")], pages=[Page(page=1, text="Page content")])
    assert [c.text for c in chunk(d)] == ["Page content"]
