# 学术 PPT Skill：paper-to-deck

把论文转成**可逐页编辑、带讲稿、可核验**的学术演示文稿。三种任务形态共用一套接口：从论文生成、按模板适配、对已有页结构再编辑。

## 设计取舍

PPT 任务最容易失分的地方是"看起来像 PPT，但打不开、改不动、讲不清"。本 Skill 用三层结构避免这一点：

1. **plan 是唯一事实源。** 页序、标题、要点、claim、证据页码、讲稿都在 `plan.json` 里，人可以改 plan 再重建，不必在 pptx 里手工挪框。
2. **预览不依赖 PowerPoint。** 没有 LibreOffice 的机器上，`preview.py` 仍按同一坐标画出 PDF 与 PNG，页序和内容可核对；`result.json` 明说预览不是 PowerPoint 渲染。
3. **审计回答具体问题。** 页数、空标题、备注缺失、文字溢出风险、引用字体、预览页数是否一致——逐条给出，而不是"生成成功"四个字。

## 目录

```
SKILL.md                  调用说明、流程、异常处置、质量闸门
scripts/read_paper.py     PDF / 文本 / JATS XML → 结构（含页码）
scripts/plan.py           结构 → 页级计划（claim、证据、备注）
scripts/build_pptx.py     计划 → pptx（模板版式与主题）
scripts/preview.py        计划 → PDF 预览 + PNG 缩略图
scripts/audit.py          pptx 结构审计
scripts/run_case.py       一条命令跑完并装配 result.json
examples/                 合成论文与模板、示意输出（已标注为示例）
benchmark/                六个合成案例的自建基准
docs/quickstart.md        三分钟上手
```

## 依赖

- Python 3.9+
- 必需：`python-pptx`（生成 pptx）、`reportlab`（预览）、`Pillow`（缩略图）、`PyMuPDF`（读 PDF 与核对预览页数）
- 不需要 Microsoft Office、LibreOffice 或任何外部二进制

## 用法

```bash
# 一条命令
python scripts/run_case.py --input /input --work /app/work --output /app/output --minutes 12

# 分步：先把论文读成结构，再生成计划，必要时手改 plan.json
python scripts/read_paper.py --input paper.pdf --output work/structure.json
python scripts/plan.py --structure work/structure.json --output work/plan.json --minutes 12
python scripts/build_pptx.py --plan work/plan.json --output out/deck.pptx --template org_template.pptx
python scripts/preview.py --plan work/plan.json --output-dir out
python scripts/audit.py --pptx out/deck.pptx --plan work/plan.json --preview out/deck_preview.pdf
```

安装到平台约定位置：

```bash
python install.py            # 复制到 /app/submission，幂等
python install.py --force    # 覆盖已有 SKILL.md
```

## 自检与基准

```bash
python selftest.py
python benchmark/run_benchmark.py
```

自检覆盖：论文 + 模板路线（页数、备注、尺寸、审计、预览一致）、手改 plan 后页数跟随、文字溢出被检出、无材料时拒答、不支持的文件类型被点名。

基准为六个合成案例：英文论文含图注、中文手稿、非默认尺寸模板、手改 plan、无图论文、空输入。**自建基准，不是官方三个固定案例，通过率不能当作官方得分。**

## 适用范围与限制

- 适用：期刊论文、预印本、技术报告转组会/答辩/评审用 PPT；按单位模板出稿；批量生成同一结构的系列汇报。
- 不适用：需要复杂动画或视觉设计的演示；论文精读结论本身（本 Skill 只负责把已有结论组织成可讲的稿）。
- 预览为程序绘制，不等同于 PowerPoint 排版；字体差异以 pptx 为准。
- 若模板版式结构异常（无标题占位符），会回退到最接近的版式并在审计中标注。

## 版本

- 1.0.0：读论文/计划/生成/预览/审计全链路；模板适配；手改 plan 重生成；自检与 6 例基准。
