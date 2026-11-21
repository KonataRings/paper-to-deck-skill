#!/usr/bin/env python3
"""Read a paper into a structure a slide plan can use.

    python read_paper.py --input paper.pdf --output structure.json

Extracts title, authors, abstract, section headings with their body text, figure
and table captions, and keeps the page number of every block so a slide can cite
where its claim comes from. Works on PDF, plain text and JATS/MathML XML.
"""
import argparse
import json
import os
import re
import sys

HEADING_HINTS = ("abstract", "introduction", "background", "related work", "methods",
                 "method", "materials and methods", "results", "discussion",
                 "conclusion", "conclusions", "limitations", "references",
                 "摘要", "引言", "背景", "方法", "结果", "讨论", "结论", "参考文献")
CAPTION = re.compile(r"^\s*(fig(?:ure)?\.?|table)\s*([0-9]+[a-z]?)\s*[.:|]", re.I)


def from_pdf(path):
    try:
        import pymupdf as fitz
    except Exception:
        import fitz
    doc = fitz.open(path)
    blocks = []
    for pno, page in enumerate(doc, start=1):
        d = page.get_text("dict")
        for b in d.get("blocks", []):
            if b.get("type") != 0:
                continue
            spans = [s for line in b.get("lines", []) for s in line.get("spans", [])]
            if not spans:
                continue
            text = " ".join(s.get("text", "").strip() for s in spans).strip()
            if not text:
                continue
            size = max(s.get("size", 0) for s in spans)
            bold = any("Bold" in (s.get("font") or "") for s in spans)
            blocks.append({"text": text, "page": pno, "size": round(size, 1), "bold": bold})
    n_pages = doc.page_count
    doc.close()
    return blocks, n_pages, os.path.basename(path)


def from_text(path):
    raw = open(path, encoding="utf-8-sig", errors="replace").read()
    blocks, page = [], 1
    for line in raw.splitlines():
        if not line.strip():
            page += 1
            continue
        blocks.append({"text": line.strip(), "page": page, "size": 11.0,
                       "bold": line.strip().isupper() or line.strip().endswith(":")})
    return blocks, max(page, 1), os.path.basename(path)


def from_xml(path):
    import xml.etree.ElementTree as ET
    root = ET.parse(path).getroot()
    blocks = []

    def walk(el, page=1):
        tag = el.tag.split("}")[-1] if isinstance(el.tag, str) else ""
        if tag in ("title", "p", "abstract", "label", "caption"):
            text = "".join(el.itertext()).strip()
            if text:
                blocks.append({"text": re.sub(r"\s+", " ", text), "page": page,
                               "size": 14.0 if tag == "title" else 10.5,
                               "bold": tag == "title"})
        for child in el:
            walk(child, page)

    walk(root)
    return blocks, 1, os.path.basename(path)


def is_heading(block, body_size):
    t = block["text"]
    if len(t) > 90 or len(t.split()) > 12:
        return False
    low = t.lower().strip(" .:0123456789")
    if any(low.startswith(h) for h in HEADING_HINTS):
        return True
    if re.match(r"^(\d+\.?)+\s+[A-Z\u4e00-\u9fff]", t):
        return True
    return block.get("bold") and block["size"] >= body_size and len(t.split()) <= 10


def structure(blocks, n_pages, source):
    sizes = [b["size"] for b in blocks if b["size"]]
    body_size = sorted(sizes)[len(sizes) // 2] if sizes else 10.5
    title = blocks[0]["text"] if blocks else ""
    # a title is the largest block on the first page
    first_page = [b for b in blocks[:12] if b["page"] == blocks[0]["page"]] if blocks else []
    if first_page:
        title = max(first_page, key=lambda b: b["size"])["text"]

    authors = ""
    for b in blocks[:8]:
        if b is not None and b["text"] != title and re.search(
                r"([A-Z][a-z]+ [A-Z][a-z]+)|(大学|学院|研究所|University|Institute)", b["text"]):
            authors = b["text"]
            break

    sections, figures, tables = [], [], []
    current = None
    for b in blocks:
        t = b["text"]
        m = CAPTION.match(t)
        if m:
            kind = "figure" if m.group(1).lower().startswith("fig") else "table"
            item = {"id": "%s%s" % (kind[0].upper(), m.group(2)), "caption": t,
                    "page": b["page"]}
            (figures if kind == "figure" else tables).append(item)
            continue
        if is_heading(b, body_size):
            current = {"heading": t.strip(), "page": b["page"], "body": []}
            sections.append(current)
            continue
        if current is None:
            current = {"heading": "Abstract" if "abstract" in t.lower() else "Opening",
                       "page": b["page"], "body": []}
            sections.append(current)
        current["body"].append(t)

    for s in sections:
        s["chars"] = sum(len(x) for x in s["body"])
        s["sentences"] = [x for para in s["body"] for x in re.split(r"(?<=[.!?。！？])\s+", para)
                          if len(x) > 20][:8]

    return {"source": source, "pages": n_pages, "title": title, "authors": authors,
            "body_size": body_size, "sections": sections,
            "figures": figures, "tables": tables, "blocks": len(blocks)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default="structure.json")
    a = ap.parse_args()

    ext = os.path.splitext(a.input)[1].lower()
    if ext == ".pdf":
        blocks, pages, name = from_pdf(a.input)
    elif ext in (".txt", ".md"):
        blocks, pages, name = from_text(a.input)
    elif ext in (".xml", ".nxml"):
        blocks, pages, name = from_xml(a.input)
    else:
        sys.exit("unsupported input type %s; pass PDF, TXT/MD or JATS XML" % ext)

    st = structure(blocks, pages, name)
    if not st["sections"]:
        sys.exit("no readable sections found in %s" % a.input)
    json.dump(st, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"title": st["title"][:80], "sections": len(st["sections"]),
                      "figures": len(st["figures"]), "tables": len(st["tables"]),
                      "pages": st["pages"], "output": a.output}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
