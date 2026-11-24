"""Run the supplier onboarding demo using an authorized chat-completions route."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request

if not __debug__:
    raise SystemExit("Run without Python optimization to retain tool argument validation.")

source = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("mode", choices=("preflight", "quick", "full"))
parser.add_argument("--run-dir", type=Path, help="Prepared workspace with the disposable workbook and click helper")
options = parser.parse_args()
if options.mode != "preflight" and options.run_dir is None:
    parser.error("--run-dir is required for quick and full")
base = options.run_dir.resolve() if options.run_dir else None
workbook = base / "供应商建档草稿.xlsx" if base else None
events = Path(os.environ.get("WPS_DEMO_EVENTS", str(base / "wps-events.jsonl"))) if base else None
model = os.environ.get("CLOVER_MODEL", "Clover-35B-A3B-Preview")

def timestamp():
    return datetime.now(timezone.utc).isoformat()

def api(messages, tools, choice):
    endpoint = os.environ.get("CLOVER_CHAT_URL")
    key = os.environ.get("CLOVER_API_KEY")
    if not endpoint or not key:
        raise SystemExit("Set CLOVER_CHAT_URL and CLOVER_API_KEY before running the demo.")
    data = {
        "model": model, "messages": messages, "tools": tools, "tool_choice": choice,
        "temperature": 0, "max_tokens": 2200,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(endpoint, json.dumps(data).encode(), headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + key,
    }, method="POST")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=85) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise SystemExit(f"Clover pilot endpoint returned HTTP {error.code}") from None
    print(json.dumps({"type": "api_result", "__timestamp": timestamp(), "model": payload.get("model"),
                      "usage": payload.get("usage"), "elapsed_seconds": round(time.monotonic() - started, 3)}), flush=True)
    return payload["choices"][0]["message"]

def tool(name, description, props, required):
    return {"type": "function", "function": {
        "name": name, "description": description, "parameters": {
            "type": "object", "properties": props, "required": required, "additionalProperties": False,
        },
    }}

def extract_call(message, name):
    calls = message.get("tool_calls") or []
    if len(calls) != 1 or calls[0]["function"]["name"] != name:
        raise RuntimeError("Clover did not return the expected tool call")
    call = calls[0]
    args = json.loads(call["function"]["arguments"])
    print(json.dumps({"type": "assistant", "__timestamp": timestamp(), "message": {"content": [
        {"type": "tool_use", "id": call["id"], "name": name, "input": args},
    ]}}, ensure_ascii=False), flush=True)
    return call, args

def forced(name):
    return {"type": "function", "function": {"name": name}}

def log(kind, location):
    with events.open("a") as file:
        print(json.dumps({"timestamp": timestamp(), "type": kind, "location": location}, ensure_ascii=False), file=file)

def write_block(address, values):
    data = "\n".join("\t".join("" if v is None else str(v) for v in row) for row in values)
    if workbook.is_symlink() or not workbook.is_file():
        raise RuntimeError("Disposable WPS workbook is unavailable")
    subprocess.run(
        ["/usr/bin/osascript", str(source / "write.applescript"), workbook.name, address, data, "0.8", str(base/"click")],
        check=True, timeout=15,
    )
    log("edit", "供应商建档 " + address)

def safe_text(value, *, blank=False):
    assert isinstance(value, str) and len(value) <= 180
    assert not re.search(r"[\x00-\x1f\x7f]", value)
    assert not value.startswith(("=", "+", "-", "@"))
    assert blank or value.strip()
    return value

fields = {
    "申请编号": 6, "供应商名称": 7, "联系人": 8, "联系邮箱": 9, "报价单编号": 10,
    "采购品名": 11, "数量（盒）": 12, "含税单价（元）": 13, "含税总额（元）": 14,
    "交货周期（工作日）": 15,
}

def paint(args):
    if set(args) != {"status", "entries", "exceptions"}:
        raise ValueError("Unexpected tool arguments")
    status = args["status"]
    assert status in ("待补件及复核", "可提交复核")
    entries = {}
    assert isinstance(args["entries"], list) and len(args["entries"]) <= len(fields)
    for entry in args["entries"]:
        assert set(entry) == {"field", "value", "source"}
        field, value, cite = entry["field"], entry["value"], entry["source"]
        assert field in fields and field not in entries
        if fields[field] < 12:
            safe_text(value)
        else:
            assert type(value) in (int, float) and 0 <= value < 100000000
        entries[field] = [value, safe_text(cite)]
    issues = []
    assert isinstance(args["exceptions"], list) and len(args["exceptions"]) <= 4
    for issue in args["exceptions"]:
        assert set(issue) == {"kind", "detail", "source"}
        assert issue["kind"] in ("缺件", "字段冲突", "其他")
        issues.append([safe_text(issue[k]) for k in ("kind", "detail", "source")])
    filled = [(fields[field], entry) for field, entry in entries.items()]
    filled.sort()
    blocks = []
    for row, entry in filled:
        if blocks and blocks[-1][0] + len(blocks[-1][1]) == row:
            blocks[-1][1].append(entry)
        else:
            blocks.append((row, [entry]))
    write_block("B3", [[status]])
    for row, block in blocks:
        write_block(f"B{row}", block)
    if issues:
        write_block("A19", issues)
    log("save", workbook.name)
    return {"saved": workbook.name, "fields_written": len(entries), "exceptions_written": len(issues)}

def receive_inputs():
    inbox = events.parent / "received"
    inbox.mkdir()
    for filename in ("01-供应商入驻资料包.pdf", "02-供应商入驻核对清单.pdf"):
        shutil.copyfile(source / filename, inbox / filename)
    log("receive", "01-供应商入驻资料包.pdf")
    time.sleep(1.2)
    return inbox

def read_page(path, page, stage, label):
    text = subprocess.check_output(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(path), "-"],
        text=True,
    )
    if not text.strip():
        raise RuntimeError(f"Page {page} is empty")
    log(stage, label)
    time.sleep(3.0)
    return text

def main():
    string = {"type": "string"}
    if options.mode == "preflight":
        probe = tool("report_probe", "Return the supplied short text.", {"text": string}, ["text"])
        call, arguments = extract_call(api(
            [{"role": "user", "content": "Call report_probe with text ready."}], [probe], forced("report_probe"),
        ), "report_probe")
        assert arguments == {"text": "ready"}
        return
    records = {"type": "array", "maxItems": 10, "items": {"type": "object", "properties": {
        "field": {"type": "string", "enum": list(fields)}, "value": {"anyOf": [string, {"type": "number"}]},
        "source": string,
    }, "required": ["field", "value", "source"], "additionalProperties": False}}
    exceptions = {"type": "array", "maxItems": 4, "items": {"type": "object", "properties": {
        "kind": {"type": "string", "enum": ["缺件", "字段冲突", "其他"]}, "detail": string, "source": string,
    }, "required": ["kind", "detail", "source"], "additionalProperties": False}}
    writer = tool("save_wps_workbook", "将可核实的字段、状态和异常写入已打开的 WPS 工作簿并保存。", {
        "status": {"type": "string", "enum": ["待补件及复核", "可提交复核"]},
        "entries": records, "exceptions": exceptions,
    }, ["status", "entries", "exceptions"])
    if options.mode == "full":
        inbox = receive_inputs()
        packet = inbox / "01-供应商入驻资料包.pdf"
        application = read_page(packet, 1, "read_application", "资料包第 1 页 · 供应商入驻申请表")
        quotation = read_page(packet, 2, "read_quotation", "资料包第 2 页 · 采购报价单")
        checklist = read_page(inbox / "02-供应商入驻核对清单.pdf", 1,
                              "read_checklist", "核对必需附件和跨文件字段")
        packet_text = application + "\n" + quotation
        exception_rule = "异常表只列需要承办人处理的问题，核对无误或计算相符的项目不写入异常表。"
    else:
        packet_text, checklist = [
            subprocess.check_output(["pdftotext", "-layout", str(source / name), "-"], text=True)
            for name in ("01-供应商入驻资料包.pdf", "02-供应商入驻核对清单.pdf")
        ]
        exception_rule = ""
    prompt = (
        "你负责供应商入驻初审。阅读下面的资料和核对清单，然后调用 save_wps_workbook 完成任务。"
        "按模板字段原名写入可核实的值，数量、金额和工作日用数字。冲突字段不提交给工具。"
        "异常写清具体证据、来源页码和下一步。缺少必需文件归为「缺件」，两个来源的同一字段值不同归为「字段冲突」。"
        + exception_rule + "用简体中文。\n\n"
        "【资料包】\n" + packet_text +
        "\n【核对清单】\n" + checklist
    )
    (base/"prompt.txt").write_text(prompt)
    messages = [{"role": "user", "content": prompt}]
    if options.mode == "full":
        log("review", "用收件清单交叉核对资料")
    msg = api(messages, [writer], forced("save_wps_workbook"))
    if options.mode == "full":
        time.sleep(1.8)
    call, args = extract_call(msg, "save_wps_workbook")
    result = paint(args)
    print(json.dumps({"type": "result", "__timestamp": timestamp(), "result": result}, ensure_ascii=False), flush=True)
    time.sleep(5 if options.mode == "full" else 3)

if __name__ == "__main__":
    main()
