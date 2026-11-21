#!/usr/bin/env python3
"""Render a real preview of the plan: PDF with one page per slide, plus PNGs.

    python preview.py --plan plan.json --output-dir out --png-slides 3

No PowerPoint or LibreOffice is required. The preview is drawn from the same plan
the pptx is built from, so slide order, titles, bullets and page references can be
inspected even where no renderer is installed. The audit records that the preview
comes from the plan, not from PowerPoint, so nobody mistakes it for a render of
the pptx file itself.
"""
import argparse
import json
import os

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas as rl_canvas

W, H = 960.0, 540.0
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

ACCENT = HexColor("#1f4e79")
MUTED = HexColor("#8a8a8a")
INK = HexColor("#1b1b1b")


def font_path():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def register_font():
    path = font_path()
    if not path:
        return "Helvetica"
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        pdfmetrics.registerFont(TTFont("DeckFont", path))
        return "DeckFont"
    except Exception:
        return "Helvetica"


def draw_slide(c, slide, font, total):
    c.setFillColor(HexColor("#ffffff"))
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(ACCENT)
    c.rect(0, H - 6, W, 6, stroke=0, fill=1)

    kind = slide.get("layout", "bullets")
    title = slide.get("title", "")
    c.setFillColor(INK)
    c.setFont(font, 30 if kind == "title" else 25)
    y = H - 70
    for line in simpleSplit(title, font, 24 if kind == "title" else 22, W - 120)[:2]:
        c.drawString(60, y, line)
        y -= 34

    if kind == "title":
        c.setFont(font, 16)
        c.setFillColor(MUTED)
        for line in simpleSplit(slide.get("subtitle", ""), font, 16, W - 120)[:2]:
            c.drawString(60, y - 10, line)
            y -= 22
        c.setFillColor(ACCENT)
        c.setFont(font, 14)
        claim = slide.get("claim", "")
        c.drawString(60, 90, simpleSplit(claim, font, 14, W - 120)[0] if claim else "")
    elif kind == "figure":
        c.setStrokeColor(MUTED)
        c.setDash(4, 4)
        c.setLineWidth(1)
        c.rect(60, 120, 520, 300, stroke=1, fill=0)
        c.setDash()
        c.setFillColor(MUTED)
        c.setFont(font, 13)
        c.drawString(72, 128, "figure %s (image placed in the pptx)" % (slide.get("figure") or "-"))
        c.setFillColor(INK)
        c.setFont(font, 15)
        ty = H - 150
        for line in simpleSplit(slide.get("claim", ""), font, 15, 300)[:10]:
            c.drawString(610, ty, line)
            ty -= 22
    else:
        c.setFont(font, 18)
        c.setFillColor(INK)
        by = H - 140
        for b in (slide.get("bullets") or [])[:5]:
            lines = simpleSplit("• " + b, font, 18, W - 150)[:3]
            for i, line in enumerate(lines):
                c.drawString(70 if i == 0 else 86, by, line)
                by -= 24
            by -= 10

    c.setFillColor(MUTED)
    c.setFont(font, 10)
    c.drawString(60, 28, slide.get("footer", ""))
    page = (slide.get("evidence") or {}).get("page")
    if page:
        c.drawString(W - 220, 28, "source: page %s" % page)


def make_pngs(plan, outdir, count):
    from PIL import Image, ImageDraw, ImageFont
    path = font_path()

    def F(size):
        return ImageFont.truetype(path, size) if path else ImageFont.load_default()

    made = []
    for i, slide in enumerate(plan["slides"][:count], start=1):
        img = Image.new("RGB", (1280, 720), "white")
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 1280, 8], fill="#1f4e79")
        d.text((80, 70), slide.get("title", "")[:60], font=F(40), fill="#1b1b1b")
        y = 170
        for b in (slide.get("bullets") or [])[:5]:
            d.text((96, y), "• " + b[:80], font=F(24), fill="#1b1b1b")
            y += 46
        if slide.get("layout") == "figure":
            d.rectangle([96, y, 700, y + 300], outline="#9aa", width=2)
        d.text((80, 670), "%s   source: page %s" % (
            slide.get("footer", ""), (slide.get("evidence") or {}).get("page", "-")),
            font=F(18), fill="#888")
        out = os.path.join(outdir, "preview_p%d.png" % i)
        img.save(out)
        made.append(out)
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--basename", default="deck_preview")
    ap.add_argument("--png-slides", type=int, default=3)
    a = ap.parse_args()

    plan = json.load(open(a.plan, encoding="utf-8-sig"))
    os.makedirs(a.output_dir, exist_ok=True)
    font = register_font()
    pdf_path = os.path.join(a.output_dir, a.basename + ".pdf")
    c = rl_canvas.Canvas(pdf_path, pagesize=(W, H))
    for slide in plan["slides"]:
        draw_slide(c, slide, font, len(plan["slides"]))
        c.showPage()
    c.save()

    pngs = make_pngs(plan, a.output_dir, a.png_slides)
    info = {"pdf": pdf_path, "pdf_bytes": os.path.getsize(pdf_path),
            "pages": len(plan["slides"]), "pngs": pngs, "font": font,
            "renderer": "reportlab from plan (not PowerPoint)"}
    json.dump(info, open(os.path.join(a.output_dir, "preview_info.json"), "w",
                         encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"pages": info["pages"], "pdf": pdf_path, "pngs": len(pngs),
                      "font": font}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
