---
name: paper-to-deck
description: 把论文或研究材料转成可编辑、可讲解、可核验的学术演示文稿：抽取主线与证据页号、生成页级结构、按模板生成 pptx 与讲稿备注，并在没有 PowerPoint 的环境里产出 PDF 预览与结构审计（页数、备注、文字溢出、字体、预览一致性）。
---

# 论文转学术 PPT：从主线到可讲解的稿子

本 Skill 处理"论文如何变成一场能讲、能查、能改的报告"。它读论文、定页结构、写讲稿，产出可逐页编辑的 `.pptx`，并在没有 PowerPoint 的机器上给出 PDF 预览与结构审计。它不负责论文精读结论本身，也不负责图表美化——那些由相邻环节提供。

## 适用条件

- 手上有论文（PDF、纯文本、JATS XML）或已有页结构（plan JSON），要变成一份学术汇报。
- 要求交付 pptx，且要求可编辑、带讲稿、能追溯每页证据来自哪一页原文。
- 要求适配给定模板（`*.pptx`/`*.potx`）的主题与版式。

不适用于：纯视觉设计、动画制作、把论文写成综述文章。

## 输入

| 位置 | 内容 |
|-|-|
| `/input/case.json` | 案例标识与 `output_contract`，可能含 `minutes` |
| `/input/task.md` | 汇报场景、听众、时长、页数约束 |
| `/input/artifacts/` | 论文 PDF/TXT/XML、模板 pptx、图片、已给的 `plan*.json` 或 `structure*.json` |

## 处理流程

1. **读数材料。** `read_paper.py` 抽出标题、作者、摘要、各节标题与正文、图表题注，并为每块记页码。PDF 用版式信息判断标题层级；纯文本与 XML 走各自分支。抽不到任何章节时报错，不硬凑。
2. **定主线与页结构。** `plan.py` 生成 `plan.json`：封面、目录、每节一页、图页、结论页。每页含标题、要点、一句主张（claim）、证据页码、讲稿备注。页数由时长与 `--max-slides` 控制，默认约 1.4 页/分钟。
3. **按模板生成 pptx。** `build_pptx.py` 优先使用模板的版式与主题，模板缺失时用内置 16:9 版式并给出警告。图页把材料里的图放进去，讲稿写入备注。
4. **出预览与导出。** `export_pdf.py` 先尝试 LibreOffice（`soffice --headless --convert-to pdf`）把真正的 pptx 渲染成 PDF；本机没有 LibreOffice 时回退到 `preview.py` 用同一份 plan 绘制，二者都会在 `export_info.json` 里记明渲染器。没有 PowerPoint 或 LibreOffice 也能看到页序、标题与要点。
5. **审计。** `audit.py` 打开 pptx 核对页数、标题是否为空、备注是否齐全、文字是否可能溢出、引用字体，以及预览页数是否等于幻灯片页数。
6. **装配结果。** `run_case.py` 汇总 `result.json`：可编辑稿、预览、页级结构、证据映射与状态。

一条命令：

```bash
python scripts/run_case.py --input /input --work /app/work --output /app/output --minutes 12
```

## 三种任务形态的落地方式

**从论文生成。** 读 PDF → 结构 → plan → pptx → 预览 → 审计。页结构与 claim 都在 plan 里，评审可以直接对照"这一页讲什么、依据第几页"。

**按模板适配。** `artifacts` 里出现文件名含 `template` 的 pptx 时，按其母版与版式生成；审计记录 `template_used` 与最终尺寸，便于核对是否真的用了模板。模板缺失时明确告警，而不是静默改变版式。

**已有结构再编辑。** 若给了 `plan*.json`，直接按它建稿；团队可以先手改 plan（删页、改标题、换 claim），再重新生成，不必动 pptx。这就是"生成与编辑"的稳定接口。

## 异常处置

| 情形 | 识别方式 | 处置 |
|-|-|-|
| 输入类型不支持 | `read_paper.py` 报 `unsupported input type` | 说明支持的类型，不猜测文件内容 |
| 论文读不出章节 | 结构里 `sections` 为空 | 报失败并保留已抽到的文本块 |
| 没有模板 | 构建时告警 | 用内置版式，结果里记 `template_used: null` |
| 模板版式不含占位符 | 版式回退到最接近的一页 | 审计标注页数与备注，仍可交付 |
| 文字可能溢出 | 审计按字号与框尺寸估算 | 提示具体页码，交人工缩短或调整 |
| 备注缺失 | 审计列出页码 | 视为质量缺口，不当作通过 |
| 图找不到对应文件 | 图页只放题注与说明 | 明确写"未找到图文件"，不伪造插图 |
| 预览页数与页数不符 | 审计报 `preview has N pages for M slides` | 视为失败，重跑预览 |

## 运行状态口径

- `success`：pptx、预览、审计齐备且审计通过，契约字段全部填写。
- `partial`：稿子可用但审计有缺口（备注缺失、文字溢出风险、契约字段缺项）。
- `insufficient_evidence`：没有可读材料，`result.json` 说明缺什么。
- `failed`：读取或生成失败，保留中间产物与错误信息。

## 输出约定

```
/app/output/
  deck.pptx          可逐页编辑的演示文件，含讲稿备注
  deck_preview.pdf   每页一页的预览
  preview_p1..3.png  前几页缩略图
  deck_audit.json    结构审计（页数、备注、溢出、字体、预览一致性）
  result.json        editable_deck / preview / outline / evidence_map / status
```

**关于预览的性质**：预览由同一份 plan 用 reportlab 绘制，不是 PowerPoint 渲染。换机打开的实际字体以 pptx 为准，`result.json` 的 `uncertainty` 会写明这一点，避免把预览当成最终排版。

## 失败处理

先读 `work/run_report.json` 的 `rc` 与 `stderr`，区分参数问题与材料问题。已生成的 plan 可复用：只重跑 `build_pptx.py` 与 `audit.py`，避免重复读论文。

## 质量闸门

1. 每页有标题与讲稿备注。
2. 每页 claim 能在原文找到对应页，`evidence_map` 的页码非空。
3. 审计 `ok` 为真，预览页数等于幻灯片页数。
4. 模板存在时，成品尺寸与模板一致。
5. plan 与 pptx 页数一致；改过 plan 必须重新生成。

## 预算分配

单案例建议不超过 18 次模型调用：读材料 2 次、页结构 6 次、生成与预览 3 次、审计与回改 5 次、复核 2 次。脚本不消耗模型请求，重复性核对交给脚本。

## 输出片段示例

以下为合成示例（`examples/case`）的真实输出节选，**不是**正式案例结果：

```json
{
 "case_id": "EXAMPLE-DECK",
 "status": "success",
 "editable_deck": "/app/output/deck.pptx",
 "preview": {"/app/output/deck_preview.pdf": "11 pages"},
 "outline": [{"index": 3, "layout": "bullets", "title": "Abstract", "page": 1,
              "has_notes": true}],
 "evidence_map": [{"slide": 3, "page": 1, "claim": "Repeated stimuli reduce the response."}],
 "uncertainty": "预览由 plan 绘制，不是 PowerPoint 渲染"
}
```

## 资源

- `scripts/read_paper.py`：PDF/文本/XML → 结构（含页码）。
- `scripts/plan.py`：结构 → 页级计划（claim、证据、备注）。
- `scripts/build_pptx.py`：计划 → pptx（用模板版式与主题）。
- `scripts/preview.py`：计划 → PDF 预览与 PNG 缩略图。
- `scripts/export_pdf.py`：优先用 LibreOffice 渲染 pptx 为 PDF，无则回退 plan 绘制并记明渲染器。
- `scripts/audit.py`：pptx 结构审计。
- `scripts/run_case.py`：一条命令跑完并装配 `result.json`。
- `docs/quickstart.md`：三分钟上手。
- `benchmark/`：六个合成案例的自建基准。
