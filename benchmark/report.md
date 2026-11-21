# 自建基准报告（学术 PPT）

说明：本基准由本题作品自行构建，论文与模板均为合成材料，**不是**平台官方的三个固定案例，
通过率不能当作官方得分。它检验文档声明的行为：读论文、出页结构、带讲稿、
适配模板尺寸、跟随人工改过的 plan、无材料时拒答。

| 案例 | 期望 | 结果 | 页数 | 说明 |
|-|-|-|-:|-|
| english-paper | success | ✓ | 8 | status=True, min_slides=True, notes=True, audit=True, figure_slide=True |
| chinese-manuscript | success | ✓ | 7 | status=True, min_slides=True, notes=True, audit=True, language=True |
| template-4x3 | success | ✓ | 7 | status=True, min_slides=True, notes=True, audit=True, size=True |
| edited-plan | plan | ✓ | 3 | deck followed the edited plan |
| no-figures | success | ✓ | 6 | status=True, min_slides=True, notes=True, audit=True, figure_slide=True |
| empty-input | insufficient_evidence | ✓ | - | refused and said why |

通过 **6/6**。
