"""Markdown -> canonical blocks/tables, shared by every Markdown-only backend."""
from doctopus.backends.markdown import from_markdown

MD = """# Title

Intro paragraph
continues here.

## Results

- first item
- second item

| Region | 2025 |
| --- | --- |
| North | 1.5 |

```python
x = 1
```

![figure](img.png)
"""


def test_blocks_and_tables_from_markdown():
    r = from_markdown([(1, MD)], source="t")
    assert [(b.type, b.level) for b in r.blocks] == [
        ("heading", 1), ("paragraph", None), ("heading", 2), ("list_item", None), ("list_item", None), ("code", None)]
    assert r.blocks[1].text == "Intro paragraph\ncontinues here."
    assert r.blocks[3].text == "first item"
    (t,) = r.tables
    assert t.rows == [["Region", "2025"], ["North", "1.5"]] and t.page == 1 and t.markdown.startswith("| Region")
    assert all(b.page == 1 and b.source == "t" for b in r.blocks)


def test_pages_numbered_and_text_without_markup():
    r = from_markdown([(1, "# A\n\nalpha"), (2, "beta")], source="t")
    assert [p.page for p in r.pages] == [1, 2] and r.page_count == 2
    assert r.blocks[-1].page == 2 and "#" not in r.text and "alpha" in r.text
    assert r.markdown == "# A\n\nalpha\n\nbeta"


def test_unknown_pages_stay_none():
    r = from_markdown([(None, "just text")], source="t")
    assert r.blocks[0].page is None and r.pages == [] and r.page_count is None


def test_html_tables_become_pipe_tables():
    html = ('<table><tr><td colspan="3">Revenue | USD</td></tr>'
            '<tr><th>Region</th><th>2025</th><th>2026</th></tr><tr><td>North</td><td>1</td><td>2</td></tr></table>')
    r = from_markdown([(1, "Intro.\n" + html + "\nAfter.")], source="mineru")
    assert len(r.tables) == 1 and r.tables[0].page == 1
    assert r.tables[0].rows == [["Revenue | USD", "", ""], ["Region", "2025", "2026"], ["North", "1", "2"]]
    assert "<table" not in r.markdown and "<td" not in r.text
    assert [b.text for b in r.blocks] == ["Intro.", "After."]
