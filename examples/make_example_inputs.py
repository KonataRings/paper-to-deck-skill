#!/usr/bin/env python3
"""Generate the synthetic paper and template used by the example case.

    python make_example_inputs.py --outdir case/artifacts

The paper is fabricated for demonstration: it has a title, authors, an abstract,
four sections and two figure captions, which is enough to exercise reading,
planning and citing page numbers. It is not a real publication.
"""
import argparse
import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas

TITLE = "Relay gain adapts to stimulus history in a synthetic preparation"
AUTHORS = "A. Example, B. Sample, Institute of Demonstrative Studies"

SECTIONS = [
    ("Abstract",
     "We study how a relay stage adjusts its gain when the same stimulus is repeated. "
     "Repeated brief stimuli produced a monotonic decline in the recorded response. "
     "The decline persisted after a rest period and was absent in the control arm."),
    ("1 Introduction",
     "Adaptation is widely observed, yet the stage at which gain changes remains unclear. "
     "Here we ask whether the change occurs before or within the relay. "
     "Our preparation allows the stimulus to be applied while the relay is recorded."),
    ("2 Methods",
     "Stimuli of 200 ms were delivered at 1 Hz for ten trials. "
     "Recordings were filtered between 1 and 300 Hz and sampled at 20 kHz. "
     "The control arm received the same protocol without the relay in the path. "
     "All amplitudes are reported in millivolts, peak to baseline."),
    ("3 Results",
     "The first trial produced the largest response and later trials declined. "
     "Figure 1 shows a representative trace with a peak near 13 mV. "
     "Figure 2 summarises the decline across preparations. "
     "The control arm stayed below 0.4 mV throughout, so the decline is not an artefact of the recorder."),
    ("4 Discussion",
     "The gain change is already visible at the relay, which places the adaptation before the recorder. "
     "A limitation is that only one inter-stimulus interval was tested. "
     "Next we will vary the interval and test whether recovery follows a single time constant."),
    ("5 Conclusion",
     "Relay gain declines with repeated stimulation and the decline is intrinsic to the relay. "
     "The control arm rules out a purely recording-side explanation. "
     "Interval dependence remains untested."),
]

CAPTIONS = [
    "Figure 1. Representative trace from one preparation: amplitude in mV against time in s.",
    "Figure 2. Peak amplitude across ten trials, control arm shown for comparison.",
]


def draw_text_block(c, text, x, y, width, font="Helvetica", size=10.5, leading=14):
    from reportlab.lib.utils import simpleSplit
    for line in simpleSplit(text, font, size, width):
        c.drawString(x, y, line)
        y -= leading
    return y


def build_pdf(path):
    c = rl_canvas.Canvas(path, pagesize=A4)
    W, H = A4
    c.setFont("Helvetica-Bold", 16)
    y = H - 70
    for line in _wrap(TITLE, "Helvetica-Bold", 16, W - 120):
        c.drawString(60, y, line)
        y -= 22
    c.setFont("Helvetica", 10.5)
    c.drawString(60, y - 6, AUTHORS)
    y -= 40

    for i, (head, body) in enumerate(SECTIONS):
        if y < 140:
            c.showPage()
            y = H - 70
        c.setFont("Helvetica-Bold", 12 if head[0].isdigit() else 13)
        c.drawString(60, y, head)
        y -= 20
        c.setFont("Helvetica", 10.5)
        y = draw_text_block(c, body, 60, y, W - 120)
        if i == 2:
            y -= 6
            c.setFillColorRGB(0.9, 0.9, 0.9)
            c.rect(60, y - 150, W - 120, 150, stroke=0, fill=1)
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(70, y - 165, CAPTIONS[0])
            y -= 190
        if i == 3:
            c.setFont("Helvetica-Oblique", 9)
            y -= 6
            for line in _wrap(CAPTIONS[1], "Helvetica-Oblique", 9, W - 120):
                c.drawString(60, y, line)
                y -= 12
        y -= 16
    c.showPage()
    c.save()


def _wrap(text, font, size, width):
    from reportlab.lib.utils import simpleSplit
    return simpleSplit(text, font, size, width)


def build_template(path):
    from pptx import Presentation
    from pptx.util import Inches
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    prs.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="case/artifacts")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    build_pdf(os.path.join(a.outdir, "paper.pdf"))
    build_template(os.path.join(a.outdir, "org_template.pptx"))
    print("wrote paper.pdf and org_template.pptx in %s" % a.outdir)


if __name__ == "__main__":
    main()
