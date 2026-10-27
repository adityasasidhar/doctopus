# Benchmarks

These historical measurements cover Xberg, Docling, and automatic routing on the repository fixtures. The runner uses a fresh subprocess per file/engine pair; the saved results do not record hardware or dependency versions. Treat the figures as a snapshot, not a current performance guarantee or a comparison of all eight engines. Quality is scored only for fixtures with a reference.

| Document | Engine | Wall time | Peak RSS | Quality |
| --- | --- | ---: | ---: | --- |
| 15-page, two-column paper | Xberg | 0.37 s | 158 MB | — |
| | Docling | 18.12 s | 2,997 MB | — |
| 9-page paper | Xberg | 0.36 s | 170 MB | — |
| | Docling | 22.84 s | 3,221 MB | — |
| 3-page scan | Xberg | 0.24 s | 198 MB | OCR F1 0.967 |
| | Docling | 40.67 s | 3,152 MB | OCR F1 0.921 |
| Merged-header table | Xberg | 0.13 s | 99 MB | Cell-token coverage 1.000 |
| | Docling | 8.10 s | 2,581 MB | Cell-token coverage 1.000 |
| Two-column reading order | Xberg | 0.10 s | 98 MB | Order 1.000 |
| | Docling | 6.97 s | 2,183 MB | Order 1.000 |

On the three scored fixtures, Xberg matched or exceeded Docling's scores while using less time and memory. Table detection counts differed on the two papers, but there is no table ground truth for those papers.

## What the scores mean

- **OCR F1** compares token counts against Xberg's extraction of the original digital pages.
- **Cell-token coverage** checks whether expected cell tokens occur anywhere in the Markdown, not whether table structure or merged cells are correct.
- **Order** compares the expected `P01`–`P24` marker sequence.

The degraded scan has no recorded quality score.

## Reproduce

From a checkout of the repository:

```bash
uv sync --extra dev --extra docling
uv run python tests/make_fixtures.py
uv run python -m doctopus.bench.run --backends xberg,docling,auto
```

The generator uses the checked-in `fixtures/attention_2col.pdf`. Results are written to `bench_results/results.md` (git-ignored). Omit `--backends` to benchmark every currently available engine plus `auto`; model downloads and warm caches can affect timings even though each measurement uses a new process.
