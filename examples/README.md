# 示例（合成，非正式案例）

本目录只用于说明接口与字段，**不是**平台任何固定案例的结果。

| 文件 | 内容 |
|-|-|
| `case/case.json` | 合成案例的契约：`editable_deck`、`preview`、`outline`、`evidence_map`、`status` |
| `make_example_inputs.py` | 生成合成论文 `paper.pdf` 与合成模板 `org_template.pptx` |
| `expected_output/result.json` | 由合成材料实际跑出的结果，已标 `"example": true` |

**只发文本资源。** 平台把 PDF/PPTX/PNG 判为不支持的文件类型，会让整次提交在预检被拒。因此本包不带任何二进制文件：合成论文与模板由脚本即时生成，成稿与预览也在运行时产出。

复现：

```bash
python examples/make_example_inputs.py --outdir examples/case/artifacts
python scripts/run_case.py --input examples/case --work /tmp/work --output /tmp/out --minutes 10
```

跑完在 `/tmp/out` 下会得到 `deck.pptx`、`deck_export.pdf`（有 LibreOffice 时是真正的 pptx 渲染，否则为 plan 绘制，`export_info.json` 会写明）、`deck_preview.pdf`、`preview_p*.png` 与 `deck_audit.json`。

`expected_output/result.json` 里的路径是运行时路径，用于说明字段结构；它对应的二进制产物不随包发布。

论文内容是编的（"relay gain adapts to repeated stimulation"），不要把其中的数值当作文献数据。
