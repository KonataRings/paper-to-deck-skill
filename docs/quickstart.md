# 三分钟上手

## 1. 一条命令

```bash
python scripts/run_case.py --input /input --work /app/work --output /app/output --minutes 12
```

它会读材料、出页结构、生成 pptx、画预览、做审计，最后打印：

```json
{"case_id": "EXAMPLE-DECK", "status": "success", "slides": 11,
 "outputs": ["deck.pptx", "deck_audit.json", "deck_preview.pdf"], "template": true}
```

## 2. 想改故事，改 plan 而不是改 PPT

```bash
python scripts/plan.py --structure work/structure.json --output work/plan.json --minutes 10
# 打开 work/plan.json：删页、改标题、把 claim 换成你真正要讲的那句话
python scripts/build_pptx.py --plan work/plan.json --output out/deck.pptx
python scripts/preview.py --plan work/plan.json --output-dir out
```

`plan.json` 里每页长这样：

```json
{"index": 3, "layout": "bullets", "title": "Abstract",
 "bullets": ["重复施加刺激后响应单调下降。"],
 "claim": "重复刺激使响应单调下降，且休息后仍存在。",
 "evidence": {"page": 1, "figure": null},
 "notes": "先讲主张，再用要点支撑。"}
```

`evidence.page` 是原文页码，审计与 `result.json` 都会核对它是否为空。

## 3. 用单位模板

把模板放在 `artifacts/` 下，文件名含 `template` 即可被自动识别：

```bash
python scripts/build_pptx.py --plan work/plan.json --output out/deck.pptx \
    --template artifacts/org_template.pptx
```

审计会记录 `template_used` 与最终尺寸，便于确认模板确实生效。

## 4. 交付前检查

```bash
python scripts/audit.py --pptx out/deck.pptx --plan work/plan.json \
    --preview out/deck_preview.pdf --output out/deck_audit.json
python selftest.py
python benchmark/run_benchmark.py
```

审计打印 `ok`、页数、问题与警告；`selftest.py` 验证包本身可用；基准给出六个合成案例的通过率（不是官方得分）。

## 5. 没有材料时

若摘要里 `status` 为 `insufficient_evidence`，说明输入里没有可读论文也没有 plan。此时在 `result.json` 里写明缺什么（论文、结构或计划），不要凭领域常识编一份汇报。
