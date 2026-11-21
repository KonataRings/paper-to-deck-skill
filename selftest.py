#!/usr/bin/env python3
"""Self-test for the deck skill: paper route, plan route, template, refusals."""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "scripts")
TMP = os.path.join(HERE, "_selftest")


def run(args, expect=0):
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True)
    if expect is not None and p.returncode != expect:
        sys.stderr.write(p.stdout + p.stderr)
        raise AssertionError("%s exited %d, expected %s" % (
            os.path.basename(args[0]), p.returncode, expect))
    return p


def last_json(text):
    for line in reversed(text.strip().splitlines()):
        if line.strip().startswith("{"):
            return json.loads(line)
    raise AssertionError("no JSON line in output: %s" % text[-300:])


def main():
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP)
    try:
        _run_checks()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)


def _run_checks():
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP)
    case = os.path.join(HERE, "examples", "case")
    work, out = os.path.join(TMP, "work"), os.path.join(TMP, "out")

    # 1. paper + template route
    p = run([os.path.join(SCRIPTS, "run_case.py"), "--input", case, "--work", work,
             "--output", out, "--minutes", "10"])
    summary = last_json(p.stdout)
    assert summary["status"] == "success", summary
    assert summary["slides"] >= 6, summary
    assert summary["template"] is True, summary

    from pptx import Presentation
    prs = Presentation(os.path.join(out, "deck.pptx"))
    sizes = (round(prs.slide_width / 914400, 2), round(prs.slide_height / 914400, 2))
    assert sizes == (13.33, 7.5), sizes
    notes = [s.notes_slide.notes_text_frame.text.strip() for s in prs.slides
             if s.has_notes_slide]
    assert len(notes) == len(prs.slides._sldIdLst) and all(notes), notes

    audit = json.load(open(os.path.join(out, "deck_audit.json"), encoding="utf-8"))
    assert audit["ok"] is True, audit
    assert audit["preview_pages"] == audit["slide_count"], audit

    res = json.load(open(os.path.join(out, "result.json"), encoding="utf-8"))
    assert res["editable_deck"] and res["preview"] and res["outline"], res
    assert res["contract_missing"] == [], res["contract_missing"]
    assert any(e["page"] for e in res["evidence_map"]), res["evidence_map"][:2]

    # 2. plan route: edit the plan, rebuild, the deck must follow
    plan = json.load(open(os.path.join(work, "plan.json"), encoding="utf-8"))
    plan["slides"] = plan["slides"][:5]
    for i, s in enumerate(plan["slides"], start=1):
        s["index"] = i
        s["footer"] = "%d / 5" % i
    trimmed = os.path.join(TMP, "plan_trimmed.json")
    json.dump(plan, open(trimmed, "w", encoding="utf-8"), ensure_ascii=False)
    deck2 = os.path.join(TMP, "deck5.pptx")
    p = run([os.path.join(SCRIPTS, "build_pptx.py"), "--plan", trimmed, "--output", deck2,
             "--template", os.path.join(case, "artifacts", "org_template.pptx")])
    assert last_json(p.stdout)["slides"] == 5
    assert len(Presentation(deck2).slides._sldIdLst) == 5

    # 3. audit catches an overfull text box
    fat = json.loads(json.dumps(plan))
    fat["slides"][2]["bullets"] = ["a sentence that keeps going " * 120]
    fat_path = os.path.join(TMP, "plan_fat.json")
    json.dump(fat, open(fat_path, "w", encoding="utf-8"), ensure_ascii=False)
    deck3 = os.path.join(TMP, "deck_fat.pptx")
    run([os.path.join(SCRIPTS, "build_pptx.py"), "--plan", fat_path, "--output", deck3])
    p = run([os.path.join(SCRIPTS, "audit.py"), "--pptx", deck3, "--plan", fat_path,
             "--output", os.path.join(TMP, "fat_audit.json")])
    assert "overflow" in p.stdout, p.stdout

    # 4. refusal: no material at all
    empty = os.path.join(TMP, "empty_in")
    os.makedirs(os.path.join(empty, "artifacts"))
    json.dump({"case_id": "EMPTY", "output_contract": {"required": ["editable_deck"]}},
              open(os.path.join(empty, "case.json"), "w", encoding="utf-8"))
    p = run([os.path.join(SCRIPTS, "run_case.py"), "--input", empty,
             "--work", os.path.join(TMP, "w2"), "--output", os.path.join(TMP, "o2")], expect=1)
    empty_summary = last_json(p.stdout)
    assert empty_summary["status"] == "insufficient_evidence", empty_summary
    res2 = json.load(open(os.path.join(TMP, "o2", "result.json"), encoding="utf-8"))
    assert res2["editable_deck"] is None and res2["notes"], res2

    # 5. refusal: an unsupported file type is named, not guessed
    weird = os.path.join(TMP, "weird")
    os.makedirs(os.path.join(weird, "artifacts"))
    open(os.path.join(weird, "artifacts", "data.bin"), "wb").write(b"\x00\x01")
    p = run([os.path.join(SCRIPTS, "read_paper.py"), "--input",
             os.path.join(weird, "artifacts", "data.bin"),
             "--output", os.path.join(TMP, "s.json")], expect=1)
    assert "unsupported input type" in p.stderr

    print(json.dumps({"slides": summary["slides"], "template_used": True,
                      "plan_route_slides": 5, "notes_on_all_slides": True,
                      "overflow_detected": True,
                      "refusals": ["no material", "unsupported type"],
                      "result": "PASS"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

