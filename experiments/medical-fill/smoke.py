"""Smoke test: is rewriting the whole medical record ever better than generating only the changes?

Three tasks on one fictional record:
  fill    the PDF case: six [MASK_*] slots with fixed rules (allergy twice = 青霉素, antibiotic from a list).
  swap    a correction at the end that ripples: allergy becomes 左氧氟沙星, so the prescribed
          左氧氟沙星 must become 阿奇霉素. No slots are marked.
  gender  a correction at the end: the patient is male, so 性别 and every 她 must change. No slots.

Output modes:
  full    model rewrites the whole record.
  fields  model returns the six slot values as JSON; code fills the template (fill only).
  edits   model returns [{"old","new"}] find/replace pairs; code applies them in order (all tasks).
  patch   same pairs, but every old is located in the original text and all apply at once, so order
          can't matter; a patch that can't be applied is sent back once with the error.

Each output is checked by code against the exact expected text, so "pass" means byte-equal after
stripping outer whitespace and code fences.
"""
import argparse, asyncio, json, os, re, time
from pathlib import Path

from openai import AsyncOpenAI

TEMPLATE = """患者基本信息：姓名 {NAME}，性别 {GENDER}，年龄 {AGE}。
【主诉】：反复胸闷、气促 2 周，加重 3 天。{P1}自诉夜间不能平卧，活动后症状明显。
【既往史】：患者有10年高血压病史，规律服用氨氯地平 5 mg 每日一次。2型糖尿病 4 年，服用二甲双胍。需要特别注意：患者对 {ALLERGY}（某种抗生素）有严重过敏史，曾发生过敏性休克。
【个人史】：无吸烟史，偶有饮酒。{P2}的父亲有冠心病史。
【入院检查】：血压 160/95 mmHg，心率 92 次/分，体温 38.2℃。双下肺可闻及湿啰音。
【辅助检查】：血常规 WBC 12.4×10^9/L，中性粒细胞 82%；CRP 46 mg/L；胸片提示右下肺斑片影。肌酐 88 μmol/L，空腹血糖 8.1 mmol/L。
【诊疗经过】：入院后予降压、扩冠治疗。因合并肺部感染，主管医生在选择抗感染药物时，必须严格规避其过敏药物。最终医生开具了 {ANTIBIOTIC}（抗生素名称）进行静脉滴注，疗程 7 天。治疗后{P3}体温恢复正常，胸闷缓解。
【出院医嘱】：1. 继续服用降压药及降糖药；2. 嘱患者终身避免接触 {ALLERGY_CONFIRM}（再次确认过敏药物）；3. 嘱{P4}低盐低脂饮食，2 周后门诊复查血常规及胸片。"""

SLOTS = ["NAME", "GENDER", "AGE", "ALLERGY", "ANTIBIOTIC", "ALLERGY_CONFIRM"]
PRON = {f"P{i}": "患者" for i in range(1, 5)}  # fill/swap use neutral wording


def render(**kw):
    return TEMPLATE.format(**{**PRON, **kw})


MASKED = render(**{s: f"[MASK_{s}]" for s in SLOTS})
FILLED = dict(NAME="方若溪", GENDER="女", AGE="62岁", ALLERGY="青霉素", ANTIBIOTIC="左氧氟沙星",
              ALLERGY_CONFIRM="青霉素")
SWAP_IN = render(**FILLED)
SWAP_OUT = render(**{**FILLED, "ALLERGY": "左氧氟沙星", "ALLERGY_CONFIRM": "左氧氟沙星",
                     "ANTIBIOTIC": "阿奇霉素"})
SHE = {f"P{i}": "她" for i in range(1, 5)}
GENDER_IN = TEMPLATE.format(**{**SHE, **FILLED, "ANTIBIOTIC": "阿奇霉素"})
GENDER_OUT = TEMPLATE.format(**{**{k: "他" for k in SHE}, **FILLED, "ANTIBIOTIC": "阿奇霉素",
                                "GENDER": "男"})

FILL_RULES = ("填写规则：[MASK_NAME] 填一个虚构中文姓名；[MASK_GENDER] 填“男”或“女”；[MASK_AGE] 填“数字+岁”，如“58岁”；"
              "[MASK_ALLERGY] 与 [MASK_ALLERGY_CONFIRM] 都填“青霉素”；[MASK_ANTIBIOTIC] 从“红霉素、阿奇霉素”中选一个。")
SWAP_RULE = "更正：经核实，患者的过敏药物应为左氧氟沙星，而非青霉素。原处方的左氧氟沙星因此必须改为阿奇霉素。除此之外的内容一字不改。"
GENDER_RULE = "更正：经核实，该患者实际为男性。请把性别更正为男，并把文中所有指代患者的“她”改为“他”。除此之外的内容一字不改。"

FMT = {
    "full": "只输出完整病历正文，不要任何解释、标题或代码块，其余文字、标点、空格和换行与原文保持一致。",
    "fields": "只输出一个 JSON 对象，键为 MASK_NAME、MASK_GENDER、MASK_AGE、MASK_ALLERGY、MASK_ANTIBIOTIC、"
              "MASK_ALLERGY_CONFIRM，值为要填入的文字。不要输出病历正文，不要解释。",
    "edits": "不要输出病历正文。只输出一个 JSON 数组，每项为 {\"old\": 原文片段, \"new\": 替换后的片段}。"
             "old 必须在当前文本中逐字出现且只出现一次（必要时带上前后几个字以保证唯一）。"
             "程序会按数组顺序依次应用替换，每次替换后的文本是下一项的“当前文本”。不要解释。",
    "patch": "不要输出病历正文。只输出一个 JSON 数组，每项为 {\"old\": 原文片段, \"new\": 替换后的片段}。"
             "所有 old 都在上面给出的原文中定位：必须逐字出现且只出现一次（必要时带上前后几个字以保证唯一），"
             "各项之间不能重叠。程序会在原文上同时应用全部替换，所以不必考虑先后顺序。不要解释。",
}


def prompt(task, mode):
    if task == "fill":
        return f"下面是一份病历模板，请填写其中的空位。\n\n{MASKED}\n\n{FILL_RULES}\n\n{FMT[mode]}"
    src, rule = (SWAP_IN, SWAP_RULE) if task == "swap" else (GENDER_IN, GENDER_RULE)
    return f"下面是一份病历初稿。\n\n{src}\n\n{rule}\n\n{FMT[mode]}"


def strip(text):
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
    t = re.sub(r"\n?```$", "", t)
    return t.strip()


def fill_ok(values):
    """values: slot -> text. Returns None if valid, else a reason."""
    v = values
    if not v.get("NAME") or "MASK" in v["NAME"] or len(v["NAME"]) > 4:
        return "name"
    if v.get("GENDER") not in ("男", "女"):
        return "gender"
    if not re.fullmatch(r"\d{1,3}岁", v.get("AGE", "")):
        return "age"
    if v.get("ALLERGY") != "青霉素" or v.get("ALLERGY_CONFIRM") != "青霉素":
        return "allergy"
    if v.get("ANTIBIOTIC") not in ("红霉素", "阿奇霉素"):
        return "antibiotic"
    return None


def parse_json(text):
    t = strip(text)
    m = re.search(r"[\[{].*[\]}]", t, re.S)
    return json.loads(m.group(0) if m else t)


def source(task):
    return MASKED if task == "fill" else SWAP_IN if task == "swap" else GENDER_IN


def apply_patch(text, out):
    """Applies all {"old","new"} pairs against the original text at once.
    Returns (final_text, None) or (None, error message for the model)."""
    try:
        edits = parse_json(out)
        spans = []
        for e in edits:
            old, new = e["old"], e["new"]
            n = text.count(old)
            if n != 1:
                return None, f"old 片段在原文中出现了 {n} 次（应为 1 次）：{old}"
            i = text.index(old)
            spans.append((i, i + len(old), new))
    except Exception as e:
        return None, f"无法解析为 JSON 数组：{type(e).__name__}"
    spans.sort()
    for (a0, a1, _), (b0, _, _) in zip(spans, spans[1:]):
        if b0 < a1:
            return None, f"两个 old 片段重叠：{text[a0:a1]} / {text[b0:b0 + 20]}"
    for i, j, new in reversed(spans):
        text = text[:i] + new + text[j:]
    return text, None


def score(task, mode, out):
    """Returns (passed, reason, final_text)."""
    try:
        if mode == "patch":
            final, err = apply_patch(source(task), out)
            if err:
                return False, f"patch: {err[:40]}", out
        elif task == "fill" and mode == "fields":
            d = parse_json(out)
            vals = {s: str(d.get(f"MASK_{s}", "")) for s in SLOTS}
            r = fill_ok(vals)
            return r is None, r or "ok", render(**vals)
        elif mode == "edits":
            text = MASKED if task == "fill" else SWAP_IN if task == "swap" else GENDER_IN
            for e in parse_json(out):
                n = text.count(e["old"])
                if n != 1:
                    return False, f"old found {n}x: {e['old'][:20]}", text
                text = text.replace(e["old"], e["new"])
            final = text
        else:
            final = strip(out)
    except Exception as e:
        return False, f"parse: {type(e).__name__}", out
    if task == "fill":
        pat = re.escape(MASKED)
        for s in SLOTS:
            pat = pat.replace(re.escape(f"[MASK_{s}]"), f"(?P<{s}>.+?)", 1)
        m = re.fullmatch(pat, final, re.S)
        if not m:
            return False, "body changed" if "MASK" not in final else "mask left", final
        r = fill_ok(m.groupdict())
        return r is None, r or "ok", final
    want = SWAP_OUT if task == "swap" else GENDER_OUT
    if final == want:
        return True, "ok", final
    if re.sub(r"\s", "", final) == re.sub(r"\s", "", want):
        return False, "whitespace only", final
    return False, "content differs", final


ARMS = {
    "dllm": dict(base=lambda: os.environ["DIFFUSION_BASE_URL"].removesuffix("/chat/completions"),
                 key=lambda: "none", model="qwen36-iter22000-blk16-arverify-best",
                 extra={"chat_template_kwargs": {"enable_thinking": False}}),
    "qwen": dict(base=lambda: "https://openrouter.ai/api/v1", key=lambda: os.environ["OPENROUTER_API_KEY"],
                 model="qwen/qwen3.6-35b-a3b", extra={"reasoning": {"enabled": False}}),
}
JOBS = [("fill", "full"), ("fill", "fields"), ("fill", "edits"),
        ("swap", "full"), ("swap", "edits"), ("gender", "full"), ("gender", "edits"),
        ("fill", "patch"), ("swap", "patch"), ("gender", "patch")]


async def one(client, arm, task, mode, rep, retries):
    """In patch mode, a patch that can't be applied (bad JSON, old not found exactly once, overlap)
    goes back to the model with the error, up to `retries` times. Wrong content is never fed back."""
    a = ARMS[arm]
    t0 = time.time()
    messages = [{"role": "user", "content": prompt(task, mode)}]
    toks = calls = 0
    while True:
        r = await client.chat.completions.create(
            model=a["model"], temperature=0.8, max_tokens=4096, seed=rep + 100 * calls,
            extra_body=a["extra"], messages=messages)
        out = r.choices[0].message.content or ""
        toks += r.usage.completion_tokens
        calls += 1
        err = apply_patch(source(task), out)[1] if mode == "patch" else None
        if not err or calls > retries:
            break
        messages += [{"role": "assistant", "content": out},
                     {"role": "user", "content": f"无法应用：{err}。请输出修正后的完整 JSON 数组，不要解释。"}]
    ok, why, final = score(task, mode, out)
    return {"arm": arm, "task": task, "mode": mode, "rep": rep, "pass": ok, "reason": why,
            "latency_s": round(time.time() - t0, 2), "completion_tokens": toks, "calls": calls,
            "prompt_tokens": r.usage.prompt_tokens, "finish": r.choices[0].finish_reason,
            "output": out, "final": final}


async def main(a):
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    clients = {k: AsyncOpenAI(base_url=v["base"](), api_key=v["key"](), timeout=600, max_retries=1)
               for k, v in ARMS.items() if k in a.arms}
    sem = asyncio.Semaphore(a.concurrency)

    async def run(arm, task, mode, rep):
        async with sem:
            try:
                rec = await one(clients[arm], arm, task, mode, rep, a.retries)
            except Exception as e:
                rec = {"arm": arm, "task": task, "mode": mode, "rep": rep, "pass": False,
                       "reason": f"error {repr(e)[:200]}"}
            with out.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(arm, task, mode, rep, rec["pass"], rec["reason"], rec.get("latency_s"), flush=True)

    await asyncio.gather(*(run(arm, t, m, r) for arm in a.arms for t, m in JOBS if m in a.modes for r in range(a.reps)))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--arms", nargs="+", default=list(ARMS))
    p.add_argument("--reps", type=int, default=4)
    p.add_argument("--modes", nargs="+", default=["full", "fields", "edits", "patch"])
    p.add_argument("--retries", type=int, default=1, help="patch mode: resend unappliable patches")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--out", default="experiments/medical-fill/results/smoke.jsonl")
    main_args = p.parse_args()
    asyncio.run(main(main_args))
