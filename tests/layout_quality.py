"""Where does the heavy engine earn its cost? Reading order (2-col) and merged-header table cell recall."""
import asyncio, difflib, json, re
from doctopus.core.gateway import Gateway

async def main():
    gw = Gateway(); truth = json.load(open("fixtures/table_merged.truth.json"))
    print(f"{'engine':8s} {'time':>7s} | {'reading-order':>13s} {'markers':>8s} | {'table-cell recall':>17s} {'tables':>6s}")
    for be in ("xberg", "docling"):
        d = await gw.parse("fixtures/twocol_order.pdf", backend=be, fallback=False)
        seq = re.findall(r"P(\d{2})\b", d.markdown)
        want = [f"{i:02d}" for i in range(1, 25)]
        order = difflib.SequenceMatcher(None, want, seq, autojunk=False).ratio()
        t = await gw.parse("fixtures/table_merged.pdf", backend=be, fallback=False)
        tbl_text = " ".join(x.markdown for x in t.tables) or ""
        toks = set(re.findall(r"[\w.]+", tbl_text))
        cells = truth["cells"]
        recall = sum(1 for c in cells if c in toks) / len(cells)
        print(f"{be:8s} {d.processing.elapsed_ms/1000:6.1f}s | {order:13.3f} {len(seq):>5d}/24 | {recall:17.3f} {len(t.tables):>6d}")
asyncio.run(main())
