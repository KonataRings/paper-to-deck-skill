#!/usr/bin/env python3
"""Turn a paper structure into a slide plan with claims and evidence.

    python plan.py --structure structure.json --output plan.json \
        --max-slides 14 --minutes 12 --template template.pptx

Every slide carries: a title, bullets or a figure, one claim in a sentence, the
page the claim comes from, and speaker notes. The plan is plain JSON, so a human
or an agent can edit the story before any pptx is built.
"""
import argparse
import json
import re

STOP = re.compile(r"^(we |in this|here|this paper|the aim|figure|table|however, |thus, )", re.I)


def trim(text, limit=140):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in (". ", "; ", ", "):
        i = cut.rfind(sep)
        if i > limit * 0.5:
            return cut[:i].strip(" ,;") + ("." if sep == ". " else "")
    return cut.rstrip() + "…"


def bullets(section, max_bullets=4):
    out = []
    for s in section.get("sentences") or []:
        if len(out) >= max_bullets:
            break
        if len(s) < 25:
            continue
        out.append(trim(s, 120))
    if not out:
        for para in (section.get("body") or [])[:max_bullets]:
            out.append(trim(para, 120))
    return out


def build(structure, max_slides=14, minutes=12, template=None, language="auto"):
    zh = language == "zh" or (language == "auto" and
                              bool(re.search(r"[\u4e00-\u9fff]", structure.get("title", ""))))
    L = (lambda zh_s, en_s: zh_s if zh else en_s)
    sections = [s for s in structure.get("sections") or [] if s.get("chars", 0) > 120]
    if not sections:
        sections = (structure.get("sections") or [])[:4]

    slides = []
    slides.append({"layout": "title", "title": structure.get("title") or L("未命名报告", "Untitled"),
                   "subtitle": structure.get("authors") or "",
                   "bullets": [], "claim": L("本次汇报的主线", "The through-line of this talk"),
                   "evidence": {"page": 1, "figure": None},
                   "notes": L("开场用一句话说明这项工作报告什么问题、给出什么结论。",
                              "Open with one sentence on the question and the answer.")})

    if len(sections) >= 3:
        slides.append({"layout": "outline", "title": L("汇报结构", "Outline"),
                       "bullets": [s["heading"] for s in sections[:6]],
                       "claim": L("先给结构，让听众知道落点", "Give the structure up front"),
                       "evidence": {"page": sections[0].get("page", 1), "figure": None},
                       "notes": L("列出各节，不要念标题。", "List the sections; do not read them out.")})

    budget = max(3, min(max_slides, int(minutes * 1.4) + 2)) - len(slides)
    picked = sections[:budget]
    for s in picked:
        claim = (s.get("sentences") or [s.get("body", [""])[0] if s.get("body") else s["heading"]])[0]
        slides.append({"layout": "bullets", "title": s["heading"],
                       "bullets": bullets(s),
                       "claim": trim(claim, 180),
                       "evidence": {"page": s.get("page", 1), "figure": None},
                       "notes": L("这一页的主张是：%s。先讲主张，再用要点支撑。",
                                  "Claim: %s. State it, then support it with the bullets.")
                       % trim(claim, 90)})

    figs = structure.get("figures") or []
    for f in figs[:2]:
        slides.append({"layout": "figure", "title": trim(f["caption"], 70),
                       "bullets": [], "figure": f.get("id"),
                       "claim": trim(f["caption"], 180),
                       "evidence": {"page": f.get("page", 1), "figure": f.get("id")},
                       "notes": L("对照图 %s 讲一句结论，说明它支持哪条主张。",
                                  "Use figure %s for one conclusion; say which claim it supports.")
                       % f.get("id")})

    tail = None
    for s in sections[::-1]:
        if re.search(r"(conclusion|discussion|summary|结论|讨论|小结)", s["heading"], re.I):
            tail = s
            break
    if tail is None and sections:
        tail = sections[-1]
    if tail:
        slides.append({"layout": "conclusion", "title": L("结论与下一步", "Conclusions and next steps"),
                       "bullets": bullets(tail, 3),
                       "claim": trim((tail.get("sentences") or [tail["heading"]])[0], 180),
                       "evidence": {"page": tail.get("page", 1), "figure": None},
                       "notes": L("只留三条，分别对应主张、证据与限制。",
                                  "Keep three: claim, evidence, limitation.")})

    for i, s in enumerate(slides, start=1):
        s["index"] = i
        s["footer"] = "%d / %d" % (i, len(slides))

    return {"deck": {"title": slides[0]["title"], "template": template,
                     "aspect": "16:9", "language": "zh" if zh else "en",
                     "minutes": minutes},
            "source": {"paper": structure.get("source"), "pages": structure.get("pages")},
            "slides": slides,
            "coverage": {"sections_used": len(picked), "sections_total": len(sections),
                         "figures_used": min(2, len(figs)), "figures_total": len(figs)}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--structure", required=True)
    ap.add_argument("--output", default="plan.json")
    ap.add_argument("--max-slides", type=int, default=14)
    ap.add_argument("--minutes", type=int, default=12)
    ap.add_argument("--template", default=None)
    ap.add_argument("--language", default="auto", choices=["auto", "zh", "en"])
    a = ap.parse_args()

    st = json.load(open(a.structure, encoding="utf-8-sig"))
    plan = build(st, a.max_slides, a.minutes, a.template, a.language)
    json.dump(plan, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"slides": len(plan["slides"]), "coverage": plan["coverage"],
                      "output": a.output}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    main()
