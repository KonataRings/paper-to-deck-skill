# 示例（合成，非正式案例）

本目录只用于说明接口与字段，**不是**平台任何固定案例的结果。

| 文件 | 内容 |
|-|-|
| `case/case.json` | 合成案例的契约：`editable_deck`、`preview`、`outline`、`evidence_map`、`status` |
| `case/artifacts/paper.pdf` | 合成论文：标题、作者、摘要、四节、两条图注，用于演示读文与页码引用 |
| `case/artifacts/org_template.pptx` | 合成模板：16:9 版式，用于演示模板适配 |
| `make_example_inputs.py` | 重新生成上面两份合成材料的脚本 |
| `expected_output/` | 由上面输入实际跑出的结果，`result.json` 已标 `"example": true` |

复现：

```bash
python examples/make_example_inputs.py --outdir examples/case/artifacts
python scripts/run_case.py --input examples/case --work /tmp/work --output /tmp/out --minutes 10
```

打开 `expected_output/deck.pptx` 可以看到：11 页，每页都有讲稿备注，页脚标注 `页码 · 原文页码`；`deck_audit.json` 记录页数、备注、字体与预览一致性；`deck_preview.pdf` 用于没有 PowerPoint 的机器上核对页序。

论文内容是编的（"relay gain adapts to repeated stimulation"），不要把其中的数值当作文献数据。
