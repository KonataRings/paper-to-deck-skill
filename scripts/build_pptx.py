#!/usr/bin/env python3
"""Build the deck from the plan, honouring a template when one is supplied.

    python build_pptx.py --plan plan.json --output deck.pptx [--template t.pptx] \
        [--artifacts /input/artifacts]

With a template, the deck inherits the template's theme, masters and layouts, so
fonts and bullet styles follow the organiser's file. Without one, a clean 16:9
deck is built. Speaker notes carry the claim, the page it came from and what to
say, which is what makes the deck reviewable rather than decorative.
"""
import argparse
import glob
import json
import os
import sys

from pptx import Presentation
from pptx.util import Emu, Inches, Pt
from pptx.dml.color import RGBColor

TEXT_W = 11.5
BODY_TOP = 1.9
BODY_H = 4.6


def find_layout(prs, kind):
    """Pick a template layout by name, then by placeholder shape."""
    names = {"title": ("title slide", "title", "封面", "标题幻灯片"),
             "section": ("section header", "section", "分节"),
             "content": ("title and content", "content", "标题和内容", "正文")}
    for layout in prs.slide_layouts:
        low = (layout.name or "").lower()
        if any(k in low for k in names.get(kind, ())):
            return layout
    for layout in prs.slide_layouts:
        ph = [p.placeholder_format.type for p in layout.placeholders]
        if kind == "title" and len(ph) >= 2:
            return layout
        if kind == "content" and ph:
            return layout
    return prs.slide_layouts[min(1, len(prs.slide_layouts) - 1)]


def drop_existing_slides(prs):
    xml_slides = prs.slides._sldIdLst
    for slide in list(xml_slides):
        rid = slide.rId
        prs.part.drop_rel(rid)
        xml_slides.remove(slide)


def set_text_frame(tf, lines, size=20, color=(0x22, 0x22, 0x22), bullet=True):
    tf.clear()
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line if not bullet else "• " + line
        for run in p.runs:
            run.font.size = Pt(size)
            run.font.color.rgb = RGBColor(*color)
        p.space_after = Pt(8)


def add_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def find_image(artifacts, fig_id):
    if not artifacts or not fig_id:
        return None
    num = "".join(ch for ch in str(fig_id) if ch.isdigit())
    patterns = ["*%s*.png" % num, "*%s*.jpg" % num, "*%s*.jpeg" % num, "*%s*.pdf" % num,
                "*.png", "*.jpg"]
    for pat in patterns:
        hits = sorted(glob.glob(os.path.join(artifacts, "**", pat), recursive=True))
        hits = [h for h in hits if os.path.getsize(h) > 4000]
        if hits:
            return hits[0]
    return None


def add_footer(slide, text, prs):
    box = slide.shapes.add_textbox(Inches(TEXT_W - 1.2), Inches(6.95), Inches(1.0), Inches(0.3))
    tf = box.text_frame
    tf.text = text
    for p in tf.paragraphs:
        for r in p.runs:
            r.font.size = Pt(10)
            r.font.color.rgb = RGBColor(0x88, 0x88, 0x88)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--template")
    ap.add_argument("--artifacts")
    ap.add_argument("--keep-template-slides", action="store_true")
    a = ap.parse_args()

    plan = json.load(open(a.plan, encoding="utf-8-sig"))
    template = a.template or (plan.get("deck") or {}).get("template")

    if template and os.path.exists(template):
        prs = Presentation(template)
        used_template = True
        if not a.keep_template_slides:
            drop_existing_slides(prs)
    else:
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        used_template = False
        if template:
            print("warning: template %s not found, using the built-in layout" % template,
                  file=sys.stderr)

    built, notes_missing = 0, []
    for s in plan["slides"]:
        kind = s.get("layout", "bullets")
        layout = find_layout(prs, "title" if kind == "title" else "content")
        slide = prs.slides.add_slide(layout)

        title_ph = slide.shapes.title
        if title_ph is None:
            tb = slide.shapes.add_textbox(Inches(0.6), Inches(0.5), Inches(11.5), Inches(1.1))
            title_ph = tb
            tf = tb.text_frame
            tf.text = s.get("title", "")
            for r in tf.paragraphs[0].runs:
                r.font.size = Pt(30)
        else:
            title_ph.text = s.get("title", "")
            for p in title_ph.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(30 if kind == "title" else 26)

        body = None
        for ph in slide.placeholders:
            if ph.placeholder_format.idx != 0:
                body = ph
                break

        if kind == "title":
            if body is not None and s.get("subtitle"):
                body.text_frame.text = s["subtitle"]
                for p in body.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(18)
                        r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
        elif kind == "figure":
            img = find_image(a.artifacts, s.get("figure"))
            pic_top = Inches(BODY_TOP)
            if img and os.path.exists(img):
                try:
                    slide.shapes.add_picture(img, Inches(0.9), pic_top, width=Inches(6.4))
                except Exception as exc:
                    print("warning: could not place %s (%s)" % (img, exc), file=sys.stderr)
            cap = slide.shapes.add_textbox(Inches(7.6), pic_top, Inches(4.8), Inches(4.4))
            set_text_frame(cap.text_frame, [s.get("claim", "")], size=16, bullet=False)
        else:
            lines = s.get("bullets") or [s.get("claim", "")]
            if body is not None:
                set_text_frame(body.text_frame, lines[:5], size=20)
            else:
                tb = slide.shapes.add_textbox(Inches(0.8), Inches(BODY_TOP),
                                              Inches(TEXT_W), Inches(BODY_H))
                set_text_frame(tb.text_frame, lines[:5], size=20)

        add_footer(slide, "%s · p.%s" % (s.get("footer", ""),
                                         (s.get("evidence") or {}).get("page", "-")), prs)
        if s.get("notes"):
            add_notes(slide, s["notes"])
        else:
            notes_missing.append(s.get("index"))
        built += 1

    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    prs.save(a.output)
    print(json.dumps({"slides": built, "bytes": os.path.getsize(a.output),
                      "template": template if used_template else None,
                      "notes_missing": notes_missing, "output": a.output},
                     ensure_ascii=False))
    return 0 if built else 1


if __name__ == "__main__":
    sys.exit(main())
