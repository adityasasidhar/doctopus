"""Benchmark: every installed engine (+ auto), one fresh subprocess per cell (honest peak RSS + cold start).

Quality is reported only where ground truth exists; elsewhere '-' (we do not invent scores).
Usage: python -m doctopus.bench.run [--fixtures DIR] [--out MD] [--backends a,b,auto] [--files x.pdf,y.pdf]
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

WORKER = r"""
import asyncio, json, resource, sys, time
from doctopus.core.gateway import Gateway
async def main():
    t = time.perf_counter()
    d = await Gateway().parse(sys.argv[1], backend=sys.argv[2], fallback=(sys.argv[2] == "auto"))
    print("@@" + json.dumps({"wall_s": round(time.perf_counter() - t, 2),
        "rss_mb": round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                            resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024),  # sidecars
        "backend": d.processing.backend, "fallback_from": d.processing.fallback_from,
        "tables": len(d.tables), "blocks": len(d.blocks), "text": d.text, "md": d.markdown,
        "pages": [[p.page, p.text] for p in d.pages]}))
asyncio.run(main())
"""
norm = lambda s: re.findall(r"[a-z0-9]+", s.lower())


def _f1(a, b):
    ov = sum((Counter(a) & Counter(b)).values())
    p, r = ov / max(len(b), 1), ov / max(len(a), 1)
    return 2 * p * r / (p + r) if p + r else 0.0


def score(name: str, res: dict, fx: Path, ref_pages: list) -> str:
    if name == "scanned_3p.pdf":
        truth = norm(" ".join(t for p, t in ref_pages if p in (1, 5, 9)))
        return f"OCR F1 {_f1(truth, norm(res['text'])):.3f}"
    if name == "twocol_order.pdf":
        seq = re.findall(r"P(\d{2})\b", res["md"])
        return f"order {difflib.SequenceMatcher(None, [f'{i:02d}' for i in range(1, 25)], seq, autojunk=False).ratio():.3f}"
    if name == "table_merged.pdf":
        truth = json.load(open(fx / "table_merged.truth.json"))["cells"]
        toks = set(re.findall(r"[\w.]+", res["md"]))
        return f"cells {sum(c in toks for c in truth) / len(truth):.3f}"
    return "-"


def cell(path: Path, backend: str) -> dict:
    out = subprocess.run([sys.executable, "-c", WORKER, str(path), backend], capture_output=True, text=True)
    line = next((l for l in out.stdout.splitlines() if l.startswith("@@")), None)
    return json.loads(line[2:]) if line else {"error": (out.stderr.strip().splitlines() or ["?"])[-1][:80]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default="fixtures")
    ap.add_argument("--out", default="bench_results/results.md")
    ap.add_argument("--backends", help="comma list; default: every installed engine + auto")
    ap.add_argument("--files", help="comma list of fixture names; default: all")
    a = ap.parse_args()
    from doctopus.backends import registry

    fx, out_md = Path(a.fixtures), Path(a.out)
    infos = {i.id: i for i in registry.list_info()}
    backends = a.backends.split(",") if a.backends else [b for b, i in infos.items() if i.available] + ["auto"]
    files = sorted(p for p in fx.iterdir() if p.suffix in {".pdf", ".docx"})
    if a.files:
        files = [f for f in files if f.name in a.files.split(",")]
    ref = cell(fx / "attention_2col.pdf", "xberg")["pages"]  # digital text = OCR ground truth
    rows = ["| file | backend | wall s | peak RSS MB | tables | blocks | quality | routed to |",
            "|---|---|---:|---:|---:|---:|---|---|"]
    out_md.parent.mkdir(parents=True, exist_ok=True)
    for f in files:
        for be in backends:
            if be != "auto" and be in infos and f.suffix.lstrip(".") not in infos[be].formats:
                continue  # unsupported format: not a result, so not a row
            print(f"  {f.name} / {be} …", file=sys.stderr, flush=True)
            r = cell(f, be)
            if "error" in r:
                rows.append(f"| {f.name} | {be} | - | - | - | - | error: {r['error']} | - |")
            else:
                routed = (r["backend"] + (f" (escalated from {r['fallback_from']})" if r["fallback_from"] else "")
                          if be == "auto" else "")
                rows.append(f"| {f.name} | {be} | {r['wall_s']} | {r['rss_mb']} | {r['tables']} | {r['blocks']} | "
                            f"{score(f.name, r, fx, ref)} | {routed} |")
            out_md.write_text("\n".join(rows) + "\n")  # after every cell: a crash late in a long run keeps the rest
    print("\n".join(rows))


if __name__ == "__main__":
    main()
