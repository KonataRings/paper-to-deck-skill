#!/usr/bin/env python3
"""Export the deck to PDF: prefer a real PowerPoint-compatible renderer.

    python export_pdf.py --pptx deck.pptx --plan plan.json --output-dir out

Order of attempts:
  1. LibreOffice (`soffice --headless --convert-to pdf`), which renders the actual
     pptx — fonts, bullets and shapes as the file defines them;
  2. the plan-drawn preview from `preview.py`, which is not a render of the pptx
     and is labelled as such in the report.

The chosen renderer is written into the JSON so a reviewer knows which file they
are looking at. Silently passing a plan drawing off as a deck render would be
exactly the kind of unverifiable claim this skill is meant to avoid.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

WINDOWS_PATHS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
]


def find_soffice():
    for name in ("soffice", "libreoffice", "soffice.bin"):
        hit = shutil.which(name)
        if hit:
            return hit
    for path in WINDOWS_PATHS:
        if os.path.exists(path):
            return path
    return None


def convert_with_soffice(soffice, pptx, outdir, timeout=240):
    before = set(glob.glob(os.path.join(outdir, "*.pdf")))
    cmd = [soffice, "--headless", "--norestore", "--convert-to", "pdf",
           "--outdir", outdir, pptx]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "LibreOffice timed out after %ds" % timeout
    after = set(glob.glob(os.path.join(outdir, "*.pdf")))
    new = sorted(after - before)
    if new:
        return new[0], None
    produced = os.path.join(outdir, os.path.splitext(os.path.basename(pptx))[0] + ".pdf")
    if os.path.exists(produced):
        return produced, None
    return None, (p.stderr or p.stdout or "no PDF produced").strip()[:300]


def page_count(path):
    try:
        import pymupdf as fitz
    except Exception:
        try:
            import fitz
        except Exception:
            return None
    doc = fitz.open(path)
    n = doc.page_count
    doc.close()
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pptx", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--no-soffice", action="store_true")
    a = ap.parse_args()

    os.makedirs(a.output_dir, exist_ok=True)
    target = os.path.join(a.output_dir, "deck_export.pdf")
    info = {"pptx": a.pptx, "renderer": None, "pdf": None, "notes": []}

    soffice = None if a.no_soffice else find_soffice()
    if soffice:
        produced, err = convert_with_soffice(soffice, os.path.abspath(a.pptx), a.output_dir)
        if produced:
            if os.path.abspath(produced) != os.path.abspath(target):
                shutil.move(produced, target)
            info.update(renderer="libreoffice", pdf=target, soffice=soffice,
                        pages=page_count(target))
        else:
            info["notes"].append("LibreOffice present but conversion failed: %s" % err)
    else:
        info["notes"].append("LibreOffice not available; no true pptx render on this machine")

    if not info["pdf"]:
        p = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                         "preview.py"),
                            "--plan", a.plan, "--output-dir", a.output_dir,
                            "--basename", "deck_export", "--png-slides", "0"],
                           capture_output=True, text=True)
        if p.returncode != 0:
            sys.stderr.write(p.stdout + p.stderr)
            sys.exit("preview fallback failed")
        info.update(renderer="plan", pdf=target,
                    pages=page_count(target),
                    caveat="PDF drawn from the slide plan, not a render of the pptx")

    json.dump(info, open(os.path.join(a.output_dir, "export_info.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"renderer": info["renderer"], "pdf": info["pdf"],
                      "pages": info.get("pages"), "notes": info["notes"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
