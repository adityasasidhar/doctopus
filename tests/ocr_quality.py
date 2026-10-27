"""OCR quality: score scanned_3p.pdf output against the digital text of the pages it was rendered from."""
import asyncio, re, difflib, sys, time
from collections import Counter
from doctopus.core.gateway import Gateway

norm = lambda s: re.findall(r"[a-z0-9]+", s.lower())

def f1(a, b):
    ca, cb = Counter(a), Counter(b)
    ov = sum((ca & cb).values())
    p, r = ov / max(len(b), 1), ov / max(len(a), 1)
    return 2 * p * r / (p + r) if p + r else 0.0

SCAN = __import__("sys").argv[1] if len(__import__("sys").argv) > 1 else "fixtures/scanned_3p.pdf"

async def main():
    gw = Gateway()
    digital = await gw.parse("fixtures/attention_2col.pdf", backend="xberg", fallback=False)
    truth = norm(" ".join(p.text for p in digital.pages if p.page in (1, 5, 9)))
    print(f"ground truth: {len(truth)} words from digital pages 1,5,9\n")
    for be in ("xberg", "docling"):
        d = await gw.parse(SCAN, backend=be, fallback=False)
        got = norm(d.text)
        sm = difflib.SequenceMatcher(None, truth, got, autojunk=False).ratio()
        print(f"{be:8s} {d.processing.elapsed_ms/1000:6.1f}s  words={len(got):5d}  bag-F1={f1(truth,got):.3f}  ordered-sim={sm:.3f}")

asyncio.run(main())
