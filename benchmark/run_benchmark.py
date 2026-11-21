#!/usr/bin/env python3
"""Run the deck benchmark and report which documented behaviours hold.

    python run_benchmark.py --output report.md
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "scripts")
TMP = os.path.join(HERE, "_tmp")


def run(args):
    return subprocess.run([sys.executable] + args, capture_output=True, text=True)


def last_json(text):
    for line in reversed((text or "").strip().splitlines()):
        if line.strip().startswith("{"):
            return json.loads(line)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=os.path.join(HERE, "report.md"))
    a = ap.parse_args()

    sys.path.insert(0, HERE)
    from build_cases import CASES, build

    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP, exist_ok=True)
    made = build(TMP)
    details = []

    for case, cdir in made:
        out = os.path.join(TMP, "out_" + case["id"])
        work = os.path.join(TMP, "work_" + case["id"])
        d = {"id": case["id"], "expect": case["expect"], "ok": False, "why": ""}

        if case["expect"] == "plan":
            # hand-edited plan route
            p = run([os.path.join(SCRIPTS, "run_case.py"), "--input", cdir, "--work", work,
                     "--output", out])
            plan_path = os.path.join(work, "plan.json")
            if not os.path.exists(plan_path):
                d["why"] = "no plan was produced to edit"
                details.append(d)
                continue
            plan = json.load(open(plan_path, encoding="utf-8"))
            plan["slides"] = plan["slides"][:case["plan_slides"]]
            for i, s in enumerate(plan["slides"], 1):
                s["index"], s["footer"] = i, "%d / %d" % (i, case["plan_slides"])
            edited = os.path.join(cdir, "artifacts", "plan.json")
            json.dump(plan, open(edited, "w", encoding="utf-8"), ensure_ascii=False)
            p = run([os.path.join(SCRIPTS, "run_case.py"), "--input", cdir,
                     "--work", work + "_2", "--output", out + "_2"])
            summary = last_json(p.stdout)
            deck = os.path.join(out + "_2", "deck.pptx")
            ok = bool(summary and summary.get("slides") == case["plan_slides"]
                      and os.path.exists(deck))
            d["ok"] = ok
            d["slides"] = summary.get("slides") if summary else None
            d["why"] = "deck followed the edited plan" if ok else "deck ignored the plan"
            details.append(d)
            continue

        p = run([os.path.join(SCRIPTS, "run_case.py"), "--input", cdir, "--work", work,
                 "--output", out])
        summary = last_json(p.stdout)
        if case["expect"] == "insufficient_evidence":
            res = os.path.join(out, "result.json")
            ok = bool(summary and summary.get("status") == "insufficient_evidence"
                      and os.path.exists(res))
            if ok:
                data = json.load(open(res, encoding="utf-8"))
                ok = bool(data.get("notes"))
            d["ok"] = ok
            d["why"] = "refused and said why" if ok else "did not refuse cleanly"
            details.append(d)
            continue

        if not summary:
            d["why"] = "run produced no summary: %s" % (p.stderr or p.stdout)[-160:]
            details.append(d)
            continue
        d["slides"] = summary.get("slides")
        deck = os.path.join(out, "deck.pptx")
        if not os.path.exists(deck):
            d["why"] = "no deck"
            details.append(d)
            continue

        from pptx import Presentation
        prs = Presentation(deck)
        size = [round(prs.slide_width / 914400, 2), round(prs.slide_height / 914400, 2)]
        notes_ok = all(s.notes_slide.notes_text_frame.text.strip() for s in prs.slides
                       if s.has_notes_slide)
        audit_path = os.path.join(out, "deck_audit.json")
        audit = json.load(open(audit_path, encoding="utf-8")) if os.path.exists(audit_path) else {}
        checks = {
            "status": summary.get("status") == "success",
            "min_slides": (summary.get("slides") or 0) >= case.get("min_slides", 1),
            "notes": notes_ok,
            "audit": audit.get("ok") is True,
        }
        if "expect_size" in case:
            checks["size"] = size == case["expect_size"]
        if "expect_language" in case:
            res = json.load(open(os.path.join(out, "result.json"), encoding="utf-8"))
            checks["language"] = any("中" in (s.get("title") or "") for s in res.get("outline", []))
        if "expect_figure_slide" in case:
            res = json.load(open(os.path.join(out, "result.json"), encoding="utf-8"))
            has_fig = any(s.get("layout") == "figure" for s in res.get("outline", []))
            checks["figure_slide"] = has_fig == case["expect_figure_slide"]
        d["checks"] = checks
        d["ok"] = all(checks.values())
        d["size"] = size
        d["why"] = ", ".join("%s=%s" % (k, v) for k, v in checks.items())
        details.append(d)

    passed = sum(1 for d in details if d["ok"])
    lines = ["# 自建基准报告（学术 PPT）", "",
             "说明：本基准由本题作品自行构建，论文与模板均为合成材料，**不是**平台官方的三个固定案例，",
             "通过率不能当作官方得分。它检验文档声明的行为：读论文、出页结构、带讲稿、",
             "适配模板尺寸、跟随人工改过的 plan、无材料时拒答。", "",
             "| 案例 | 期望 | 结果 | 页数 | 说明 |", "|-|-|-|-:|-|"]
    for d in details:
        lines.append("| %s | %s | %s | %s | %s |" % (
            d["id"], d["expect"], "✓" if d["ok"] else "✗", d.get("slides", "-"), d["why"]))
    lines += ["", "通过 **%d/%d**。" % (passed, len(details)), ""]
    open(a.output, "w", encoding="utf-8").write("\n".join(lines))
    json.dump({"passed": passed, "total": len(details), "cases": details},
              open(os.path.join(HERE, "report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"passed": passed, "total": len(details), "output": a.output},
                     ensure_ascii=False))
    return 0 if passed == len(details) else 1


if __name__ == "__main__":
    sys.exit(main())
