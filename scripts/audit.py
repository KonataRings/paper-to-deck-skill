#!/usr/bin/env python3
"""Audit the built deck: structure, notes, text fit, fonts, preview agreement.

    python audit.py --pptx deck.pptx --plan plan.json --preview out/deck_preview.pdf \
        --output out/deck_audit.json

The audit answers the questions a reviewer will ask: does it open, how many
slides, does each slide have speaker notes, is any text box overfull, which fonts
are referenced, and does the preview have one page per slide.
"""
import argparse
import json
import os
import sys

CHARS_PER_LINE = {18: 46, 20: 42, 24: 34, 30: 26}


def estimate_overflow(text, width_in, height_in, size_pt):
    """Rough capacity check: characters per line from the box width, lines from height."""
    cpl = max(10, int(width_in * 96 / (size_pt * 0.55)))
    lines = max(1, int(height_in * 96 / (size_pt * 1.45)))
    capacity = cpl * lines
    return len(text) - capacity


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pptx", required=True)
    ap.add_argument("--plan")
    ap.add_argument("--preview")
    ap.add_argument("--output", default="deck_audit.json")
    a = ap.parse_args()

    from pptx import Presentation
    from pptx.util import Emu

    report = {"pptx": a.pptx, "ok": True, "problems": [], "warnings": [], "slides": []}
    if not os.path.exists(a.pptx) or os.path.getsize(a.pptx) < 5000:
        report["ok"] = False
        report["problems"].append("deck file missing or implausibly small")
        json.dump(report, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps(report, ensure_ascii=False))
        return 1

    prs = Presentation(a.pptx)
    report["slide_size_in"] = [round(prs.slide_width / 914400, 2),
                               round(prs.slide_height / 914400, 2)]
    fonts, notes_missing, empties = set(), [], []
    for i, slide in enumerate(prs.slides, start=1):
        title = slide.shapes.title.text if slide.shapes.title is not None else ""
        if not title.strip():
            empties.append(i)
        texts, overflow = [], False
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            t = shape.text_frame.text
            if not t.strip():
                continue
            sizes = [r.font.size.pt for p in shape.text_frame.paragraphs for r in p.runs
                     if r.font.size is not None]
            size = sizes[0] if sizes else 18
            for p in shape.text_frame.paragraphs:
                for r in p.runs:
                    if r.font.name:
                        fonts.add(r.font.name)
            w = Emu(shape.width).inches if shape.width else 4
            h = Emu(shape.height).inches if shape.height else 2
            if estimate_overflow(t, w, h, size) > 0:
                overflow = True
            texts.append(t)
        has_notes = bool(slide.has_notes_slide and
                         slide.notes_slide.notes_text_frame.text.strip())
        if not has_notes:
            notes_missing.append(i)
        report["slides"].append({"index": i, "title": title[:80], "shapes": len(slide.shapes),
                                 "chars": sum(len(t) for t in texts), "notes": has_notes,
                                 "overflow_risk": overflow})

    report["slide_count"] = len(prs.slides)
    report["fonts"] = sorted(fonts)
    if empties:
        report["problems"].append("slides without a title: %s" % empties)
    if notes_missing:
        report["warning_notes_missing"] = notes_missing
        report["warnings"].append("slides without speaker notes: %s" % notes_missing)
    risky = [s["index"] for s in report["slides"] if s["overflow_risk"]]
    if risky:
        report["warnings"].append("text may overflow on slides %s" % risky)

    if a.plan and os.path.exists(a.plan):
        plan = json.load(open(a.plan, encoding="utf-8-sig"))
        if len(plan["slides"]) != report["slide_count"]:
            report["problems"].append("plan has %d slides but the deck has %d"
                                      % (len(plan["slides"]), report["slide_count"]))
        claims = [s for s in plan["slides"] if s.get("claim")]
        report["claims"] = len(claims)

    if a.preview and os.path.exists(a.preview):
        try:
            import pymupdf as fitz
        except Exception:
            import fitz
        doc = fitz.open(a.preview)
        report["preview_pages"] = doc.page_count
        if doc.page_count != report["slide_count"]:
            report["problems"].append("preview has %d pages for %d slides"
                                      % (doc.page_count, report["slide_count"]))
        doc.close()

    report["ok"] = not report["problems"]
    json.dump(report, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"ok": report["ok"], "slides": report["slide_count"],
                      "problems": report["problems"], "warnings": report["warnings"][:3],
                      "fonts": report["fonts"]}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
