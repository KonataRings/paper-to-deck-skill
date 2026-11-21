#!/usr/bin/env python3
"""Build the self-made benchmark cases for the deck skill.

    python build_cases.py --outdir cases

Six synthetic cases, each aimed at one behaviour the skill claims to support:
an English paper with figure captions, a Chinese manuscript, a template with a
non-default slide size, a hand-edited plan, a paper with no figures, and an empty
input that must be refused rather than filled in.
"""
import argparse
import json
import os

from pptx import Presentation
from pptx.util import Inches
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas

ENGLISH = [
    ("Abstract", "We measure how a relay stage adapts when stimuli repeat. "
                 "Responses decline monotonically and the decline survives a rest period."),
    ("1 Introduction", "Adaptation is common, but the stage where gain changes is unclear. "
                       "Our preparation lets us stimulate while recording the relay."),
    ("2 Methods", "Stimuli of 200 ms were delivered at 1 Hz. Signals were filtered at 300 Hz. "
                  "The control arm followed the same protocol without the relay."),
    ("3 Results", "The first trial gave the largest response, later trials declined. "
                  "Figure 1 shows a representative trace. "
                  "Figure 2 summarises ten trials. "
                  "The control arm stayed below 0.4 mV."),
    ("4 Conclusion", "The gain change sits at the relay, not at the recorder. "
                     "Interval dependence remains untested."),
]
CHINESE = [
    ("摘要", "本文研究重复刺激下中继环节的增益如何变化。重复施加短暂刺激后，记录到的响应单调下降。"),
    ("1 方法", "刺激时长 200 毫秒，重复频率 1 赫兹，信号滤波至 300 赫兹。对照组保持相同的实验流程。"),
    ("2 结果", "首个试次的响应最大，随后逐次下降。对照组的幅度始终低于 0.4 毫伏。"),
    ("3 结论", "增益变化发生在中继环节，而不是记录端。间隔依赖尚未检验。"),
]


def make_pdf(path, sections, title, authors, captions=()):
    c = rl_canvas.Canvas(path, pagesize=A4)
    W, H = A4
    from reportlab.lib.utils import simpleSplit
    y = H - 70
    c.setFont("Helvetica-Bold", 16)
    for line in simpleSplit(title, "Helvetica-Bold", 16, W - 120):
        c.drawString(60, y, line)
        y -= 22
    c.setFont("Helvetica", 10)
    c.drawString(60, y - 4, authors)
    y -= 36
    for head, body in sections:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(60, y, head)
        y -= 18
        c.setFont("Helvetica", 10.5)
        for line in simpleSplit(body, "Helvetica", 10.5, W - 120):
            c.drawString(60, y, line)
            y -= 14
        y -= 14
    y -= 6
    c.setFont("Helvetica-Oblique", 9)
    for cap in captions:
        for line in simpleSplit(cap, "Helvetica-Oblique", 9, W - 120):
            c.drawString(60, y, line)
            y -= 12
    c.showPage()
    c.save()


def make_template(path, width_in=13.333, height_in=7.5):
    prs = Presentation()
    prs.slide_width = Inches(width_in)
    prs.slide_height = Inches(height_in)
    prs.save(path)


def make_text(path, sections, title, authors):
    """Plain-text manuscript: no font is involved, so CJK survives any environment."""
    lines = [title, authors, ""]
    for head, body in sections:
        lines.append(head)
        lines.extend(body.split("。"))
        lines.append("")
    open(path, "w", encoding="utf-8").write("\n".join(lines))


CASES = [
    {"id": "english-paper", "expect": "success", "min_slides": 6,
     "paper": ("pdf", ENGLISH, "Relay gain adapts to repeated stimulation",
               "A. Example, B. Sample, Institute of Demonstrative Studies",
               ["Figure 1. Representative trace, amplitude in mV against time.",
                "Figure 2. Peak amplitude across ten trials."]),
     "expect_figure_slide": True},
    {"id": "chinese-manuscript", "expect": "success", "min_slides": 5,
     "paper": ("txt", CHINESE, "重复刺激下的中继增益变化", "示例作者，示例研究所", []),
     "expect_language": "zh"},
    {"id": "template-4x3", "expect": "success", "min_slides": 4,
     "paper": ("pdf", ENGLISH, "Relay gain adapts to repeated stimulation",
               "A. Example", []),
     "template": (10.0, 7.5), "expect_size": [10.0, 7.5]},
    {"id": "edited-plan", "expect": "plan", "plan_slides": 3,
     "paper": ("pdf", ENGLISH, "Relay gain adapts to repeated stimulation", "A. Example", [])},
    {"id": "no-figures", "expect": "success", "min_slides": 4,
     "paper": ("pdf", ENGLISH[:3], "Relay gain adapts to repeated stimulation", "A. Example", []),
     "expect_figure_slide": False},
    {"id": "empty-input", "expect": "insufficient_evidence"},
]


def build(outdir):
    made = []
    for case in CASES:
        cdir = os.path.join(outdir, case["id"])
        os.makedirs(os.path.join(cdir, "artifacts"), exist_ok=True)
        json.dump({"case_id": case["id"],
                   "output_contract": {"required": ["editable_deck", "preview", "outline"]}},
                  open(os.path.join(cdir, "case.json"), "w", encoding="utf-8"))
        if "paper" in case:
            kind, sections, title, authors, caps = case["paper"]
            if kind == "txt":
                make_text(os.path.join(cdir, "artifacts", "paper.txt"), sections, title, authors)
            else:
                make_pdf(os.path.join(cdir, "artifacts", "paper.pdf"), sections, title, authors, caps)
        if "template" in case:
            w, h = case["template"]
            make_template(os.path.join(cdir, "artifacts", "org_template.pptx"), w, h)
        made.append((case, cdir))
    return made


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="cases")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    for case, path in build(a.outdir):
        print("%-20s %s" % (case["id"], path))

