import json
import sys

path = sys.argv[1]
d = json.load(open(path, encoding="utf-8"))
d["example"] = True
d["example_notice"] = ("示例输出：由合成论文与合成模板产生，用于说明接口与字段，"
                       "不是平台正式案例的结果")
json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("marked example:", path)
