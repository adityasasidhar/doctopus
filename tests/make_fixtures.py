"""Generate the fixtures that can't be downloaded: plain text PDF, scanned (image-only) PDF, DOCX with a table."""
from pathlib import Path

import pypdfium2 as pdfium
from docx import Document
from fpdf import FPDF

F = Path(__file__).resolve().parent.parent / "fixtures"

# 1. simple, single-column digital PDF (the "easy" case the light engine should own)
pdf = FPDF()
pdf.set_auto_page_break(True, 15)
for i in range(6):
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Section {i + 1}: Quarterly Operations Notes", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    for _ in range(6):
        pdf.multi_cell(0, 6, "The platform processed a steady volume of documents this quarter. Most files were short "
                       "text reports and memos that needed no special handling, and turnaround stayed well within target. "
                       "Operators asked for clearer logs and faster startup on small servers.")
        pdf.ln(2)
pdf.output(F / "simple_text.pdf")

# 2. scanned PDF: rasterise 3 pages of the attention paper into an image-only PDF (no text layer)
src = pdfium.PdfDocument(F / "attention_2col.pdf")
imgs = [src[i].render(scale=2.0).to_pil().convert("RGB") for i in (0, 4, 8)]
imgs[0].save(F / "scanned_3p.pdf", save_all=True, append_images=imgs[1:], resolution=150)

# 3. DOCX with a table
d = Document()
d.add_heading("Vendor Cost Comparison", 1)
d.add_paragraph("Per-page pricing for document processing across three vendors.")
t = d.add_table(rows=1, cols=4)
t.style = "Table Grid"
for c, h in zip(t.rows[0].cells, ("Vendor", "Pages/mo", "Price/page", "Monthly")):
    c.text = h
for row in (("Vendor A", "100000", "0.015", "1500"), ("Vendor B", "100000", "0.010", "1000"), ("Doctopus", "100000", "0.000", "3")):
    cells = t.add_row().cells
    for c, v in zip(cells, row):
        c.text = v
d.add_paragraph("Doctopus runs on a small VPS, so cost is hosting only.")
d.save(F / "report_table.docx")
print("fixtures:", sorted(p.name for p in F.iterdir()))

# 4. two-column PDF with numbered paragraphs: ground truth reading order is P01..P24 (left column first)
pdf = FPDF()
pdf.add_page()
pdf.set_font("Helvetica", "B", 16)
pdf.cell(0, 10, "Two Column Reading Order Test", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", size=10)
with pdf.text_columns(ncols=2, gutter=8) as cols:
    for i in range(1, 25):
        cols.write(text=f"P{i:02d} The quick brown fox jumps over the lazy dog while the committee reviews item {i} of the agenda in detail. ")
        cols.ln()
pdf.output(F / "twocol_order.pdf")

# 5. table with merged header cells; ground-truth cells recorded in twocol/table_truth.json
import json
pdf = FPDF()
pdf.add_page()
pdf.set_font("Helvetica", size=10)
rows = [("Region", "2024", "2025", "2026"), ("North", "120.5", "134.2", "150.9"), ("South", "98.1", "101.7", "110.3"),
        ("East", "75.0", "82.4", "90.6"), ("West", "143.2", "150.0", "162.8"), ("Total", "436.8", "468.3", "514.6")]
with pdf.table(col_widths=(30, 30, 30, 30), text_align="CENTER") as t:
    r = t.row()
    r.cell("Revenue by region (USD millions)", colspan=4)
    for data in rows:
        r = t.row()
        for c in data:
            r.cell(c)
pdf.output(F / "table_merged.pdf")
json.dump({"cells": [c for r in rows for c in r], "title": "Revenue by region (USD millions)"}, open(F / "table_merged.truth.json", "w"))
print("added:", "twocol_order.pdf", "table_merged.pdf")

# 6. degraded scan: low-res, skewed, blurred, JPEG-compressed -- the case where a light OCR might struggle
import io
from PIL import Image, ImageFilter
bad = []
for im in imgs:
    im = im.resize((im.width // 2, im.height // 2)).rotate(2.5, expand=True, fillcolor="white").filter(ImageFilter.GaussianBlur(1.2))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=22); bad.append(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"))
bad[0].save(F / "scanned_degraded.pdf", save_all=True, append_images=bad[1:], resolution=72)
print("added: scanned_degraded.pdf")
