#!/usr/bin/env python3
"""One command for a deck case: read the paper, plan, build, preview, audit.

    python run_case.py --input /input --work /app/work --output /app/output

Routes follow the material: a paper (PDF/TXT/XML) is read into a structure; a
plan JSON may be supplied or generated; a template pptx, when present, supplies
theme and layouts. The result always names the deck, the preview and the evidence
map, and says plainly which parts could not be produced.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    p = subprocess.run([sys.executable] + cmd, capture_output=True, text=True)
    return {"cmd": os.path.basename(cmd[0]), "rc": p.returncode,
            "out": (p.stdout or "").strip()[-700:], "err": (p.stderr or "").strip()[-500:]}


def find(patterns, roots):
    hits = []
    for pat in patterns:
        for root in roots:
            hits += glob.glob(os.path.join(root, pat))
            hits += glob.glob(os.path.join(root, "**", pat), recursive=True)
    return sorted(set(h for h in hits if os.path.isfile(h)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--output", default="/app/output")
    ap.add_argument("--minutes", type=int, default=12)
    ap.add_argument("--max-slides", type=int, default=14)
    a = ap.parse_args()

    os.makedirs(a.work, exist_ok=True)
    os.makedirs(a.output, exist_ok=True)
    case_path = os.path.join(a.input, "case.json")
    case = json.load(open(case_path, encoding="utf-8-sig")) if os.path.exists(case_path) else {}
    artifacts = os.path.join(a.input, "artifacts")
    roots = [r for r in (a.input, artifacts) if os.path.isdir(r)]

    inventory = {"case_id": case.get("case_id") or case.get("id") or "unknown", "artifacts": []}
    for root in roots:
        for path in sorted(glob.glob(os.path.join(root, "**", "*"), recursive=True)):
            if os.path.isfile(path):
                inventory["artifacts"].append({"path": os.path.relpath(path, a.input),
                                               "bytes": os.path.getsize(path),
                                               "ext": os.path.splitext(path)[1].lower()})

    papers = find(["*.pdf", "*.txt", "*.md", "*.xml", "*.nxml", "*.docx"], roots)
    templates = [p for p in find(["*.pptx", "*.potx"], roots) if "template" in os.path.basename(p).lower()]
    given_plan = find(["plan*.json"], roots)
    given_struct = find(["structure*.json"], roots)

    steps, notes = [], []
    status = "success"

    structure_path = os.path.join(a.work, "structure.json")
    if given_struct:
        structure_path = given_struct[0]
    elif papers:
        steps.append(run([os.path.join(HERE, "read_paper.py"), "--input", papers[0],
                          "--output", structure_path]))
        if steps[-1]["rc"] != 0:
            status = "failed"
            notes.append("could not read the paper: %s" % (steps[-1]["err"] or steps[-1]["out"])[:200])
    else:
        status = "insufficient_evidence"
        notes.append("no paper, structure or plan was found in the input; "
                     "report the missing material instead of inventing a talk")

    plan_path = os.path.join(a.work, "plan.json")
    if given_plan:
        plan_path = given_plan[0]
    elif status == "success":
        cmd = [os.path.join(HERE, "plan.py"), "--structure", structure_path,
               "--output", plan_path, "--minutes", str(a.minutes),
               "--max-slides", str(a.max_slides)]
        if templates:
            cmd += ["--template", templates[0]]
        steps.append(run(cmd))
        if steps[-1]["rc"] != 0:
            status = "failed"
            notes.append("planning failed: %s" % (steps[-1]["out"] or steps[-1]["err"])[:200])

    deck_path = os.path.join(a.output, "deck.pptx")
    preview_dir = a.output
    if status == "success":
        cmd = [os.path.join(HERE, "build_pptx.py"), "--plan", plan_path, "--output", deck_path]
        if templates:
            cmd += ["--template", templates[0]]
        if artifacts:
            cmd += ["--artifacts", artifacts]
        steps.append(run(cmd))
        if steps[-1]["rc"] != 0:
            status = "failed"
            notes.append("deck build failed: %s" % (steps[-1]["err"] or steps[-1]["out"])[:200])

        steps.append(run([os.path.join(HERE, "export_pdf.py"), "--pptx", deck_path,
                          "--plan", plan_path, "--output-dir", preview_dir]))
        steps.append(run([os.path.join(HERE, "preview.py"), "--plan", plan_path,
                          "--output-dir", preview_dir, "--basename", "deck_preview",
                          "--png-slides", "3"]))

    audit_path = os.path.join(a.output, "deck_audit.json")
    if status == "success":
        check_pdf = os.path.join(preview_dir, "deck_export.pdf")
        if not os.path.exists(check_pdf):
            check_pdf = os.path.join(preview_dir, "deck_preview.pdf")
        steps.append(run([os.path.join(HERE, "audit.py"), "--pptx", deck_path,
                          "--plan", plan_path, "--preview", check_pdf,
                          "--output", audit_path]))
        if steps[-1]["rc"] != 0:
            status = "partial"
            notes.append("audit reported problems; see deck_audit.json")

    outline = []
    if os.path.exists(plan_path):
        plan = json.load(open(plan_path, encoding="utf-8-sig"))
        outline = [{"index": s.get("index"), "layout": s.get("layout"), "title": s.get("title"),
                    "claim": s.get("claim"), "page": (s.get("evidence") or {}).get("page"),
                    "has_notes": bool(s.get("notes"))} for s in plan.get("slides") or []]

    outputs = {name: os.path.join(a.output, name) for name in
               ("deck.pptx", "deck_export.pdf", "deck_preview.pdf", "deck_audit.json")
               if os.path.exists(os.path.join(a.output, name))}
    export_info = {}
    export_path = os.path.join(a.output, "export_info.json")
    if os.path.exists(export_path):
        export_info = json.load(open(export_path, encoding="utf-8-sig"))

    result = {
        "case_id": inventory["case_id"],
        "status": status,
        "editable_deck": outputs.get("deck.pptx"),
        "preview": {k: v for k, v in outputs.items() if k != "deck.pptx"},
        "outline": outline,
        "evidence_map": [{"slide": s["index"], "page": s["page"], "claim": s["claim"]}
                         for s in outline if s.get("page")],
        "template_used": templates[0] if templates else None,
        "export_renderer": export_info.get("renderer"),
        "notes": notes,
        "uncertainty": ("PDF 由 %s 渲染；换机打开时的实际字体仍以 pptx 为准" % (
            "LibreOffice" if export_info.get("renderer") == "libreoffice" else
            "同一份 plan 用 reportlab 绘制（本机无 LibreOffice，非 pptx 渲染）")
            if export_info else "没有预览文件"),
    }

    contract = case.get("output_contract") or {}
    required = []
    if isinstance(contract, dict):
        required = list(contract.get("required") or (contract.get("properties") or {}).keys() or [])
    missing = [f for f in required if f not in result]
    for f in missing:
        result[f] = {"status": "insufficient_evidence",
                     "reason": "material did not support this field"}
    if missing and result["status"] == "success":
        result["status"] = "partial"
    result["contract_fields"] = required
    result["contract_missing"] = missing

    json.dump(result, open(os.path.join(a.output, "result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump({"inventory": inventory, "steps": steps, "notes": notes},
              open(os.path.join(a.work, "run_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(json.dumps({"case_id": result["case_id"], "status": status,
                      "slides": len(outline), "outputs": sorted(outputs),
                      "template": bool(templates), "missing_contract": missing},
                     ensure_ascii=False))
    return 0 if status in ("success", "partial") else 1


if __name__ == "__main__":
    sys.exit(main())
