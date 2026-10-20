"""Prompts, format repair, code checks, judge prompts and the clean rule for both formats.

A generated text goes through `check(task, mode, seed, raw)`, which repairs format and returns the
repaired text, the parsed record (record format only), and a failure reason or None. Only texts that
pass go to the judge; `is_clean` combines the judge's verdict with the mode's requirements.
"""
import json, re

SECTIONS = ["主诉", "现病史", "既往史", "入院检查", "诊断", "诊疗经过", "出院医嘱"]

# ---------- prompts

NARRATIVE = ("请写一份虚构的中文住院病历摘要，用作模型训练数据。300 到 500 字。第一行写“患者，性别，年龄岁。”，"
             "如“患者，男，56岁。”；之后依次包含【主诉】【现病史】【既往史】"
             "【入院检查】【诊断】【诊疗经过】【出院医嘱】七个部分。不要写患者姓名，用“患者”指代。"
             "内容需临床上合理、前后一致。{seed}只输出病历正文。")
_DEMOGRAPHICS = re.compile(r"(男|女)性?[，,、\s]*(\d{1,3})\s*岁")
RECORD = ("请生成一份虚构的中文住院病历摘要，用作模型训练数据。只输出一个 JSON 对象，字段如下："
          "sex（“男”或“女”）、age（18 到 95 的整数）、department（科室）、chief_complaint（主诉，一句话）、"
          "diagnosis（主要诊断）、allergies（过敏药物名称数组，没有则为空数组）、"
          "prescriptions（出院带药名称数组，1 到 4 个）。处方不得包含患者过敏的药物或与其同类的药物。"
          "内容需临床上合理。{seed}不要解释。")
SEED_TEXT = "患者为{department}住院患者，{sex}性，年龄在 {age_lo} 到 {age_hi} 岁之间。"


def prompt(task, seed):
    s = SEED_TEXT.format(**seed) if seed else ""
    return (NARRATIVE if task == "narrative" else RECORD).format(seed=s)


# ---------- format repair (headers and wrappers only, never clinical content)

_ALIASES = {"患者主诉": "主诉", "入院诊断": "诊断", "初步诊断": "诊断", "出院诊断": "诊断"}
_HEAD = re.compile(
    r"^[ \t]*(?:#+[ \t]*)?(?:\*\*)?[ \t]*[【\[]?[ \t]*"
    r"(患者主诉|主诉|现病史|既往史|入院检查|入院诊断|初步诊断|出院诊断|诊断|诊疗经过|出院医嘱)"
    r"[ \t]*[】\]]?[ \t]*(?:\*\*)?[ \t]*[：:]?[ \t]*(?:\*\*)?[ \t]*", re.M)
_PREAMBLE = re.compile(r"^\s*(?:好的|以下|这是)[^\n]*[：:]\s*\n+")
_LEAD_COMPLAINT = re.compile(r"^(?P<lead>[^【]*?(?:因|主诉[：:]?)\s*[“\"](?P<cc>[^”\"]+)[”\"][^\n【]*)\n")
_FENCE = re.compile(r"^```[a-zA-Z]*\n?|\n?```$")


def repair_narrative(text):
    t = _FENCE.sub("", text.strip()).strip()
    t = _PREAMBLE.sub("", t)
    t = _HEAD.sub(lambda m: f"【{_ALIASES.get(m.group(1), m.group(1))}】", t)
    if "【主诉】" not in t:
        def lead(m):
            d = _DEMOGRAPHICS.search(m.group("lead"))
            demo = f"患者，{d.group(1)}，{d.group(2)}岁。\n" if d else ""
            return f"{demo}【主诉】{m.group('cc')}\n"
        t = _LEAD_COMPLAINT.sub(lead, t, count=1)
    return t.strip()


def section(text, name):
    m = re.search(rf"【{name}】([^【]*)", text)
    return m.group(1).strip() if m else ""


# ---------- code checks

DRUG_CLASSES = {
    "penicillin": ["青霉素", "阿莫西林", "氨苄西林", "哌拉西林", "苯唑西林", "西林"],
    "cephalosporin": ["头孢"],
    "macrolide": ["红霉素", "阿奇霉素", "克拉霉素", "罗红霉素"],
    "quinolone": ["沙星"],
    "sulfonamide": ["磺胺"],
    "nsaid": ["阿司匹林", "布洛芬", "双氯芬酸", "萘普生", "吲哚美辛"],
    "tetracycline": ["环素"],
    "aminoglycoside": ["庆大霉素", "阿米卡星", "链霉素"],
}


def drug_classes(name):
    return {c for c, keys in DRUG_CLASSES.items() if any(k in name for k in keys)}


def _parse_json(text):
    t = _FENCE.sub("", text.strip()).strip()
    m = re.search(r"\{.*\}", t, re.S)
    return json.loads(m.group(0) if m else t)


def check(task, seed, raw):
    """Returns (repaired_text, record_or_None, reason_or_None)."""
    if task == "narrative":
        t = repair_narrative(raw)
        if not 150 <= len(t) <= 1500:
            return t, None, f"length {len(t)}"
        missing = [s for s in SECTIONS if f"【{s}】" not in t]
        if missing:
            return t, None, f"missing {'、'.join(missing)}"
        m = _DEMOGRAPHICS.search(t.split("【主诉】", 1)[0]) or _DEMOGRAPHICS.search(section(t, "主诉"))
        if not m:
            return t, None, "missing demographics"
        if seed and (m.group(1) != seed["sex"] or not seed["age_lo"] <= int(m.group(2)) <= seed["age_hi"]):
            return t, None, "off seed"
        return t, None, None
    try:
        d = _parse_json(raw)
    except Exception:
        return raw, None, "json"
    if not isinstance(d, dict):
        return raw, None, "json"
    for k in ["sex", "age", "department", "chief_complaint", "diagnosis", "allergies", "prescriptions"]:
        if k not in d:
            return raw, d, f"missing {k}"
    if d["sex"] not in ("男", "女"):
        return raw, d, "sex"
    if not isinstance(d["age"], int) or not 18 <= d["age"] <= 95:
        return raw, d, "age"
    for k in ["department", "chief_complaint", "diagnosis"]:
        if not isinstance(d[k], str) or not d[k].strip():
            return raw, d, k
    al, rx = d["allergies"], d["prescriptions"]
    if not isinstance(al, list) or not isinstance(rx, list) or not all(isinstance(x, str) for x in al + rx):
        return raw, d, "lists"
    if not 1 <= len(rx) <= 4:
        return raw, d, "rx count"
    allergic = set().union(*map(drug_classes, al)) if al else set()
    for p in rx:
        if any(a and (a in p or p in a) for a in al) or drug_classes(p) & allergic:
            return raw, d, "allergy conflict"
    if seed:
        if d["sex"] != seed["sex"] or not seed["age_lo"] <= d["age"] <= seed["age_hi"]:
            return raw, d, "off seed"
    text = json.dumps(d, ensure_ascii=False, sort_keys=True)
    return text, d, None


def raw_format_ok(task, seed, raw):
    """Whether the output met the format before any repair (records get no repair beyond fences)."""
    if task == "record":
        return check(task, seed, raw)[2] is None
    t = raw.strip()
    return (150 <= len(t) <= 1500 and all(f"【{s}】" in t for s in SECTIONS)
            and bool(_DEMOGRAPHICS.search(t.split("【主诉】", 1)[0])))


# ---------- what gets compared for distinctness

def content(task, text, record):
    """Text embedded for similarity. Records leave out sex and age, which the seed fixes."""
    if task == "narrative":
        return text
    return (f"科室：{record['department']}；主诉：{record['chief_complaint']}；诊断：{record['diagnosis']}；"
            f"过敏：{'、'.join(record['allergies']) or '无'}；带药：{'、'.join(record['prescriptions'])}")


def case_key(task, text, record):
    """Exact-duplicate key: chief complaint with durations removed, plus the primary diagnosis.
    Numbers are stripped only from the complaint, so 1型 and 2型糖尿病 stay different."""
    punct = r"[\s，。,.；;、：:（）()“”\"]"
    if task == "narrative":
        cc, dx = section(text, "主诉"), section(text, "诊断")
    else:
        cc, dx = record["chief_complaint"], record["diagnosis"]
    cc = re.sub(r"[0-9一二三四五六七八九十半数余多]+\s*(?:个)?(?:月|年|天|周|日|小时|h)", "", cc)
    dx = re.split(r"[；;。\n]|(?<![0-9])2[\.、](?![0-9])", re.sub(r"^\s*1[\.、]\s*", "", dx.strip()))[0]
    return re.sub(punct, "", cc) + "|" + re.sub(punct, "", dx)


# ---------- judge

JUDGE_NARRATIVE = """You are checking a fictional Chinese inpatient summary written as model training data.
It should be clinically plausible and internally consistent, not real.{seed}

Summary:
{text}

Return only a JSON object with these keys:
"real_diagnosis": true if every diagnosis is a real condition in recognisable medical terms.
"fake_drugs": array of drug names that do not exist as real drugs or drug classes (empty if none).
"consistent": true if history, findings, diagnosis and treatment agree with each other.
"treatment_fits": true if the treatment and discharge drugs are reasonable for the diagnosis.
"garbled": true if any part has broken, mixed-language or nonsense text.
"matches_request": true if it fits the requested department, sex and age range (true if none was requested).
"note": one short sentence naming the main problem, or "" if none."""

JUDGE_RECORD = """You are checking a fictional Chinese inpatient summary used as model training data.
It should be clinically plausible, not real.{seed}

Record:
{text}

Return only a JSON object with these keys:
"real_diagnosis": true if the diagnosis names real condition(s) in recognisable medical terms.
"fake_drugs": array of drug names from prescriptions or allergies that don't exist (empty if none).
"consistent": true if the chief complaint fits the diagnosis.
"treatment_fits": true if every prescription is a reasonable discharge medication for this diagnosis.
"garbled": true if any field has broken, mixed-language or nonsense text.
"matches_request": true if it fits the requested department, sex and age range (true if none was requested).
"note": one short sentence naming the main problem, or "" if none."""

SEED_NOTE = "\nRequested: department {department}, sex {sex}, age {age_lo} to {age_hi}."


def judge_prompt(task, seed, text):
    s = SEED_NOTE.format(**seed) if seed else ""
    return (JUDGE_NARRATIVE if task == "narrative" else JUDGE_RECORD).format(seed=s, text=text)


def is_clean(verdict):
    v = verdict or {}
    return bool(v) and "error" not in v and all(
        [v.get("real_diagnosis") is True, not v.get("fake_drugs"), v.get("consistent") is True,
         v.get("treatment_fits") is True, v.get("garbled") is False, v.get("matches_request") is True])
