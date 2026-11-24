from pathlib import Path
from hashlib import sha256
import json
import re
import shutil
import sys

from openpyxl import load_workbook

source, saved, run = map(Path, sys.argv[1:])
document = load_workbook(saved, data_only=False)
worksheet = document["供应商建档"]
template = load_workbook(source/"03-供应商建档模板.xlsx", data_only=False)["供应商建档"]
expected = ["DEMO-SUP-026", "云栈办公用品有限公司", "林予安", "lin.yuan@example.com",
            "DEMO-Q-026", "A4 复印纸（80 克）", 20, 48, 960]
checks = {}
for row, wanted in enumerate(expected, 6):
    actual = worksheet[f"B{row}"].value
    if isinstance(wanted, str):
        normalize = lambda s: re.sub(r"\s*", "", str(s)).replace("(", "（").replace(")", "）")
        matches = normalize(actual) == normalize(wanted)
    else:
        matches = type(actual) in (int, float) and actual == wanted
    checks[f"value B{row}"] = matches

def cites_page(s):
    return bool(re.search(r"第?\s*[12一二]\s*页|[Pp]\.?\s*[12]|页码\s*[：:]?\s*[12]", str(s)))

for row in range(6, 15):
    cite = worksheet[f"C{row}"].value
    checks[f"source C{row}"] = cites_page(cite) and bool(re.search(r"申请|报价|资料包", str(cite)))

checks["delivery blank"] = worksheet["B15"].value in (None, "")
checks["review status"] = worksheet["B3"].value == "待补件及复核"
issues = [(a, str(b or ""), str(c or "")) for a,b,c in worksheet.iter_rows(min_row=19, max_row=22, max_col=3, values_only=True) if any((a,b,c))]
checks["exactly two exception rows"] = len(issues) == 2
checks["signed declaration omitted"] = any(
    kind == "缺件" and "合规承诺书" in detail and re.search("签署|签字|签章|签订", detail)
    and re.search("清单|资料包", cite)
    for kind, detail, cite in issues
)
checks["delivery conflict includes both values and sources"] = any(
    kind == "字段冲突" and "交货周期" in detail and re.search(r"(?<!\d)7(?!\d)", detail)
    and re.search(r"(?<!\d)10(?!\d)", detail)
    and re.search("申请|资料包", cite) and re.search("报价|资料包", cite)
    and (re.search(r"[12]\s*页|[Pp]\.?\s*[12]", cite) is not None)
    for kind, detail, cite in issues
)
checks["template labels preserved"] = all(
    worksheet[c.coordinate].value == c.value
    for row in template for c in row
    if c.value is not None
)
events = [json.loads(x) for x in (run/"wps-events.jsonl").read_text().splitlines()]
checks["native WPS edits and save recorded"] = any(e["type"] == "edit" for e in events) and events[-1]["type"] == "save"
final = run / "供应商建档草稿.xlsx"
shutil.copyfile(saved, final)
checks["scored file matches native save"] = sha256(saved.read_bytes()).digest() == sha256(final.read_bytes()).digest()
report = {"passed": sum(bool(v) for v in checks.values()), "total": len(checks),
          "checks": {k: bool(v) for k,v in checks.items()}, "exceptions": issues,
          "native_saved_sha256": sha256(final.read_bytes()).hexdigest()}
(run/"verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(report, ensure_ascii=False))
