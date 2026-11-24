"""Tax-form loops: can a model write a value whose inputs it hasn't written yet?

python -m bench.taxloop.run {generate,score,all} --run NAME [--probe]

Each request gives one fictional taxpayer's facts and asks for a filled return of five forms as one
flat JSON object. The forms reference each other in four loops. Each other form reads a value from
the main 1040 (name, SSN, wages or AGI), and the 1040 then needs a result from that form further down:
- 2441 reads 1040 line 1a (wages), and 1040 line 1e is 2441 line 26
- SE reads 1040 line 1a, and 1040 lines 10 and 23 are SE lines 13 and 12
- A reads 1040 line 11 (AGI), and 1040 line 12 is the larger of A line 17 and the standard deduction
- 8812 reads 1040 lines 11 and 16, and 1040 line 19 is 8812 line 14

Order `main_first` asks for every 1040 line first, as the forms are printed, so the five 1040 lines
that close a loop must be written before the form that computes them. Order `topo` asks for the same
keys in dependency order, so every value can be computed from text already written.
Order `main_first_strict` is `main_first` with an added instruction never to move a key, since in
`main_first` the dLLM often wrote the dependent forms first anyway. Three more variants of it test
why: `strict_t0` at temperature 0, `strict_rules_in_order` with the rules listed in output order
rather than grouped by form, and `strict_skeleton` with a JSON template of null values to fill in.
Two counterfactuals: `strict_no_loops` gives the five forward 1040 lines as facts, so nothing loops,
and `strict_t0_rep2` and `strict_t0_rep3` repeat `strict_t0` with other seeds to check determinism. The rules are
fictional and stated in full. Every check is code.
"""
import argparse, asyncio, dataclasses, datetime, json, random, re, subprocess, time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from bench.synthdata import arms
from bench.tabdlm.longrange import bootstrap

RESULTS = Path(__file__).resolve().parents[1] / "results"
ORDERS = ("main_first", "topo", "main_first_strict", "strict_t0", "strict_rules_in_order", "strict_skeleton",
          "strict_no_loops", "strict_t0_rep2", "strict_t0_rep3")
TEMPS = {"strict_t0": 0.0, "strict_t0_rep2": 0.0, "strict_t0_rep3": 0.0}
STANDARD = {"single": 15000, "head_of_household": 22500, "married_filing_jointly": 30000}
CTC_THRESHOLD = {"single": 120000, "head_of_household": 120000, "married_filing_jointly": 200000}
WAGE_BASE = 150000


@dataclass(frozen=True)
class Config:
    arms: tuple = ("dllm", "qwen")
    # One matched temperature, as in the constraints run: a precision task, and the dLLM degrades above 0.8.
    temp: float = 0.6
    n: int = 30
    first: int = 0  # first case index, so a replication can use new cases
    max_tokens: int = 3000
    concurrency: int = 8
    orders: tuple = ORDERS


def pct(x, p100):
    """p100 is the percentage times 10, so 75 means 7.5%. Rounds down to a whole dollar."""
    return x * p100 // 1000


def tax(t):
    return pct(min(t, 50000), 100) + pct(max(0, t - 50000), 220)


# (key, rule shown to the model, formula over v). Listed in dependency order, which is the `topo` order.
# A formula of None means the value is copied from the facts.
LINES = [
    ("f1040_name", "taxpayer name, from the facts", None),
    ("f1040_ssn", "taxpayer SSN, from the facts", None),
    ("f1040_filing_status", "filing status, from the facts", None),
    ("f1040_l1a", "wages from Form W-2", None),
    ("f2441_name", "name shown on Form 1040", lambda v: v["f1040_name"]),
    ("f2441_ssn", "SSN shown on Form 1040", lambda v: v["f1040_ssn"]),
    ("f2441_l12", "dependent care benefits from Form W-2 box 10", None),
    ("f2441_l18", "earned income: Form 1040 line 1a", lambda v: v["f1040_l1a"]),
    ("f2441_l24", "excluded benefits: the smallest of line 12, 5000, and 4% of line 18",
     lambda v: min(v["f2441_l12"], 5000, pct(v["f2441_l18"], 40))),
    ("f2441_l26", "taxable benefits: line 12 minus line 24", lambda v: v["f2441_l12"] - v["f2441_l24"]),
    ("f1040_l1e", "taxable dependent care benefits: Form 2441 line 26", lambda v: v["f2441_l26"]),
    ("f1040_l1z", "line 1a plus line 1e", lambda v: v["f1040_l1a"] + v["f1040_l1e"]),
    ("fse_name", "name shown on Form 1040", lambda v: v["f1040_name"]),
    ("fse_ssn", "SSN shown on Form 1040", lambda v: v["f1040_ssn"]),
    ("fse_l2", "net business profit: business receipts minus business expenses", None),
    ("fse_l7", f"wage base: {WAGE_BASE}", lambda v: WAGE_BASE),
    ("fse_l8", "wages: Form 1040 line 1a", lambda v: v["f1040_l1a"]),
    ("fse_l9", "line 7 minus line 8, but not less than 0", lambda v: max(0, v["fse_l7"] - v["fse_l8"])),
    ("fse_l10", "12% of the smaller of line 2 and line 9", lambda v: pct(min(v["fse_l2"], v["fse_l9"]), 120)),
    ("fse_l11", "3% of line 2", lambda v: pct(v["fse_l2"], 30)),
    ("fse_l12", "self-employment tax: line 10 plus line 11", lambda v: v["fse_l10"] + v["fse_l11"]),
    ("fse_l13", "deduction: half of line 12", lambda v: v["fse_l12"] // 2),
    ("f1040_l8", "business income: Schedule SE line 2", lambda v: v["fse_l2"]),
    ("f1040_l9", "total income: line 1z plus line 8", lambda v: v["f1040_l1z"] + v["f1040_l8"]),
    ("f1040_l10", "adjustments: Schedule SE line 13", lambda v: v["fse_l13"]),
    ("f1040_l11", "adjusted gross income: line 9 minus line 10", lambda v: v["f1040_l9"] - v["f1040_l10"]),
    ("fa_name", "name shown on Form 1040", lambda v: v["f1040_name"]),
    ("fa_ssn", "SSN shown on Form 1040", lambda v: v["f1040_ssn"]),
    ("fa_l1", "medical expenses, from the facts", None),
    ("fa_l2", "Form 1040 line 11", lambda v: v["f1040_l11"]),
    ("fa_l3", "7.5% of line 2", lambda v: pct(v["fa_l2"], 75)),
    ("fa_l4", "line 1 minus line 3, but not less than 0", lambda v: max(0, v["fa_l1"] - v["fa_l3"])),
    ("fa_l5", "state and local taxes paid, but not more than 10000", None),
    ("fa_l8", "mortgage interest, from the facts", None),
    ("fa_l11", "charitable gifts, from the facts", None),
    ("fa_l17", "itemized deductions: line 4 plus line 5 plus line 8 plus line 11",
     lambda v: v["fa_l4"] + v["fa_l5"] + v["fa_l8"] + v["fa_l11"]),
    ("f1040_l12", "deduction: the larger of Schedule A line 17 and the standard deduction "
     "(single 15000, head_of_household 22500, married_filing_jointly 30000)",
     lambda v: max(STANDARD[v["f1040_filing_status"]], v["fa_l17"])),
    ("f1040_l15", "taxable income: line 11 minus line 12, but not less than 0",
     lambda v: max(0, v["f1040_l11"] - v["f1040_l12"])),
    ("f1040_l16", "tax: 10% of the first 50000 of line 15, plus 22% of line 15 above 50000",
     lambda v: tax(v["f1040_l15"])),
    ("f8812_name", "name shown on Form 1040", lambda v: v["f1040_name"]),
    ("f8812_ssn", "SSN shown on Form 1040", lambda v: v["f1040_ssn"]),
    ("f8812_l4", "number of qualifying children, from the facts", None),
    ("f8812_l5", "line 4 times 2000", lambda v: v["f8812_l4"] * 2000),
    ("f8812_l6", "Form 1040 line 11", lambda v: v["f1040_l11"]),
    ("f8812_l7", "threshold: 200000 if married_filing_jointly, otherwise 120000",
     lambda v: CTC_THRESHOLD[v["f1040_filing_status"]]),
    ("f8812_l8", "line 6 minus line 7, but not less than 0", lambda v: max(0, v["f8812_l6"] - v["f8812_l7"])),
    ("f8812_l9", "5% of line 8", lambda v: pct(v["f8812_l8"], 50)),
    ("f8812_l10", "line 5 minus line 9, but not less than 0", lambda v: max(0, v["f8812_l5"] - v["f8812_l9"])),
    ("f8812_l13", "tax: Form 1040 line 16", lambda v: v["f1040_l16"]),
    ("f8812_l14", "credit: the smaller of line 10 and line 13", lambda v: min(v["f8812_l10"], v["f8812_l13"])),
    ("f1040_l19", "child tax credit: Form 8812 line 14", lambda v: v["f8812_l14"]),
    ("f1040_l22", "line 16 minus line 19, but not less than 0", lambda v: max(0, v["f1040_l16"] - v["f1040_l19"])),
    ("f1040_l23", "other taxes: Schedule SE line 12", lambda v: v["fse_l12"]),
    ("f1040_l24", "total tax: line 22 plus line 23", lambda v: v["f1040_l22"] + v["f1040_l23"]),
    ("f1040_l25", "federal tax withheld from Form W-2", None),
    ("f1040_l34", "refund: line 25 minus line 24, if positive, otherwise 0",
     lambda v: max(0, v["f1040_l25"] - v["f1040_l24"])),
    ("f1040_l37", "amount owed: line 24 minus line 25, if positive, otherwise 0",
     lambda v: max(0, v["f1040_l24"] - v["f1040_l25"])),
]
RULE = {k: r for k, r, _ in LINES}
FORMULA = {k: f for k, _, f in LINES}
FORMS = [("f1040", "Form 1040 (main return)"), ("f2441", "Form 2441 (dependent care benefits)"),
         ("fse", "Schedule SE (self-employment tax)"), ("fa", "Schedule A (itemized deductions)"),
         ("f8812", "Form 8812 (child tax credit)")]
TOPO = [k for k, _, _ in LINES]
MAIN_FIRST = [k for f, _ in FORMS for k in TOPO if k.split("_")[0] == f]
KEYS = {"topo": TOPO, **{o: MAIN_FIRST for o in ORDERS if o != "topo"}}
# 1040 lines that take their value from a form printed after the 1040.
FORWARD = ("f1040_l1e", "f1040_l10", "f1040_l12", "f1040_l19", "f1040_l23")
# Other-form lines that read an earlier 1040 value.
BACKWARD = ("f2441_l18", "fse_l8", "fa_l2", "f8812_l6", "f8812_l13")
TEXT = {"f1040_name", "f1040_ssn", "f1040_filing_status", "f2441_name", "f2441_ssn", "fse_name", "fse_ssn",
        "fa_name", "fa_ssn", "f8812_name", "f8812_ssn"}


class _Rec(dict):
    def __getitem__(self, k):
        self.read.append(k)
        return super().__getitem__(k)


def _deps():
    """Which keys each formula reads, found by running it on the first case's truth."""
    v = _Rec(truth(case(0)))
    out = {}
    for k, f in FORMULA.items():
        v.read = []
        if f:
            f(v)
        out[k] = tuple(v.read)
    return out


# ---------- cases

FIRST = ["Maria", "James", "Aisha", "Wei", "Daniel", "Priya", "Carlos", "Hannah", "Kwame", "Sofia",
         "Liam", "Yuki", "Omar", "Elena", "Noah", "Fatima", "Ethan", "Grace", "Mateo", "Leila"]
LAST = ["Okafor", "Lindqvist", "Ramirez", "Chen", "Kowalski", "Haddad", "Nguyen", "Brennan", "Patel",
        "Moreau", "Silva", "Tanaka", "Adeyemi", "Fischer", "Rossi", "Murphy", "Kim", "Novak", "Duarte", "Bauer"]


def case(idx):
    rng = random.Random(10_000 + idx)
    r100 = lambda lo, hi: rng.randrange(lo, hi) * 100
    status = rng.choice(list(STANDARD))
    wages = r100(600, 1700)
    receipts = r100(400, 1800)
    return {"idx": idx, "name": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
            "ssn": f"9{rng.randrange(10, 99)}-{rng.randrange(70, 99)}-{rng.randrange(1000, 9999)}",
            "filing_status": status, "wages": wages, "withheld": pct(wages, rng.randrange(100, 200)),
            "dependent_care_benefits": r100(20, 90), "business_receipts": receipts,
            "business_expenses": r100(50, receipts // 100 - 50), "medical": r100(0, 250),
            "salt_paid": r100(30, 150), "mortgage_interest": r100(0, 200) if rng.random() < 0.7 else 0,
            "charity": r100(0, 80), "children": rng.randint(1, 3)}


def truth(c):
    facts = {"f1040_name": c["name"], "f1040_ssn": c["ssn"], "f1040_filing_status": c["filing_status"],
             "f1040_l1a": c["wages"], "f2441_l12": c["dependent_care_benefits"],
             "fse_l2": c["business_receipts"] - c["business_expenses"], "fa_l1": c["medical"],
             "fa_l5": min(c["salt_paid"], 10000), "fa_l8": c["mortgage_interest"], "fa_l11": c["charity"],
             "f8812_l4": c["children"], "f1040_l25": c["withheld"]}
    v = {}
    for k, _, f in LINES:
        v[k] = f(v) if f else facts[k]
    return v


DEPS = _deps()


# ---------- prompt

PROMPT = """You are preparing a tax return for a fictional test. The forms and rules below are invented for this test and are not real tax law. Follow them exactly.

Taxpayer facts:
- Name: {name}
- SSN: {ssn}
- Filing status: {filing_status}
- Form W-2: wages {wages}, federal tax withheld {withheld}, dependent care benefits (box 10) {dependent_care_benefits}
- Side business: receipts {business_receipts}, expenses {business_expenses}
- Medical expenses paid: {medical}
- State and local taxes paid: {salt_paid}
- Mortgage interest paid: {mortgage_interest}
- Charitable gifts: {charity}
- Qualifying children: {children}
{given}
The return has five forms that reference each other.

{rules}

Every amount is a whole number of dollars. Round every percentage down to a whole dollar.

Answer with one flat JSON object. Use exactly these keys, in exactly this order:
{keys}
{skeleton}{strict}
Name, SSN and filing status are strings. Every other value is an integer. Output only the JSON object, with no other text."""


# For `strict_no_loops`: the five forward 1040 lines, given as facts instead of read from later forms.
GIVEN = {"f1040_l1e": "Taxable dependent care benefits", "f1040_l10": "Adjustments to income",
         "f1040_l12": "Deduction", "f1040_l19": "Child tax credit", "f1040_l23": "Other taxes"}


def prompt(c, order):
    rule, given = RULE, ""
    if order == "strict_no_loops":
        t = truth(c)
        rule = {**RULE, **{k: f"{GIVEN[k].lower()}, from the facts" for k in FORWARD}}
        rule["f1040_l8"] = "business income: business receipts minus business expenses"
        given = "".join(f"- {GIVEN[k]} (already worked out): {t[k]}\n" for k in FORWARD)
    rules = []
    if order == "strict_rules_in_order":
        title = {f: t.split(" (")[0] for f, t in FORMS}
        rules += [f"- {k} ({title[k.split('_')[0]]}): {rule[k]}" for k in KEYS[order]]
    else:
        for f, t in FORMS:
            rules.append(f"{t}:")
            rules += [f"- {k}: {rule[k]}" for k in TOPO if k.split("_")[0] == f]
            rules.append("")
    skeleton = ("\nFill in this template, replacing every null:\n"
                + json.dumps({k: None for k in KEYS[order]}, indent=1) + "\n") if order == "strict_skeleton" else ""
    return PROMPT.format(rules="\n".join(rules).strip(), keys=", ".join(KEYS[order]), skeleton=skeleton, given=given,
                         strict=STRICT if "strict" in order else "", **c)


STRICT = """
Write the keys in exactly the order listed. Do not move any key earlier or later, even when its value depends on keys listed after it. An answer with any key out of order is rejected.
"""


# ---------- scoring

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def parse(raw):
    """Returns (object or None, key order, reason)."""
    t = (raw or "").strip()
    m = _FENCE.search(t)
    body = m.group(1) if m else t
    start = body.find("{")
    if start < 0:
        return None, [], "no json"
    try:
        pairs, _ = json.JSONDecoder(object_pairs_hook=lambda p: p).raw_decode(body[start:])
    except json.JSONDecodeError:
        return None, [], "bad json"
    return dict(pairs), [k for k, _ in pairs], None


def _same(a, b):
    if isinstance(b, str):
        return isinstance(a, str) and a.strip().lower() == b.lower()
    return isinstance(a, int) and not isinstance(a, bool) and a == b


def score_request(row):
    """`correct`: equals the true value. `step`: equals its formula applied to the model's own values,
    so an error upstream doesn't count against it. A step is scored only when every input it reads is
    present and of the right type."""
    t = truth(case(row["idx"]))
    obj = row["obj"]
    out = {"parsed": obj is not None}
    if obj is None:
        return out
    out["order_ok"] = row["key_order"] == KEYS[row["order"]]
    out["correct"] = {k: _same(obj.get(k), t[k]) for k in TOPO}
    step = {}
    for k in TOPO:
        if FORMULA[k] is None or not all(type(obj.get(d)) is type(t[d]) for d in DEPS[k]):
            continue
        try:
            step[k] = _same(obj.get(k), FORMULA[k](obj))
        except Exception:
            continue
    out["step"] = step
    out["all_correct"] = all(out["correct"].values())
    # The forward links again, with a reordered answer counting as a failure on every one.
    out["forward_strict"] = {k: out["order_ok"] and step.get(k, False) for k in FORWARD}
    return out


def key(r):
    return (r["order"], r["arm"], r["idx"])


# ---------- generate

async def generate(cfg, out):
    done = {key(r) for r in map(json.loads, open(out)) if "error" not in r} if out.exists() else set()
    todo = [(o, a, i) for o in cfg.orders for a in cfg.arms for i in range(cfg.first, cfg.first + cfg.n)
            if (o, a, i) not in done]
    print(f"generate: {len(todo)} to run, {len(done)} already done", flush=True)

    async def one(client, job):
        order, arm, idx = job
        a = arms.ARMS[arm]
        temp = TEMPS.get(order, cfg.temp)
        row = {"order": order, "arm": arm, "model": a["model"], "temp": temp, "idx": idx}
        t0 = time.time()
        try:
            r = await client.chat.completions.create(
                model=a["model"], temperature=temp, max_tokens=cfg.max_tokens,
                seed=ORDERS.index(order) * 1_000 + idx, extra_body=a["extra"],
                messages=[{"role": "user", "content": prompt(case(idx), order)}])
            row.update(raw=r.choices[0].message.content or "", finish_reason=r.choices[0].finish_reason,
                       prompt_tokens=r.usage.prompt_tokens if r.usage else None,
                       completion_tokens=r.usage.completion_tokens if r.usage else None, served_model=r.model)
        except Exception as e:
            row.update(raw="", error=repr(e)[:300])
        row["latency_s"] = round(time.time() - t0, 3)
        obj, order_keys, reason = parse(row["raw"])
        row.update(obj=obj, key_order=order_keys, parse_reason=reason or "ok")
        return row

    async def arm_run(arm, js):
        client = arms.client(arm)
        sem = asyncio.Semaphore(cfg.concurrency)

        async def go(job):
            async with sem:
                row = await one(client, job)
            with out.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        await asyncio.gather(*(go(j) for j in js))

    by_arm = defaultdict(list)
    for j in todo:
        by_arm[j[1]].append(j)
    await asyncio.gather(*(arm_run(a, js) for a, js in by_arm.items()))


# ---------- score

def _median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


def _rate(items, field, keys):
    hits = [s[field][k] for s in items for k in keys if k in s.get(field, {})]
    return round(100 * sum(hits) / len(hits), 1) if hits else None


def _strict(items):
    """Forward-link step % over every request, so an unparsed or reordered answer fails all five."""
    hits = [s.get("forward_strict", {}).get(k, False) for _, s in items for k in FORWARD]
    return round(100 * sum(hits) / len(hits), 1) if hits else 0


def score(cfg, run_dir):
    rows = {key(r): r for r in map(json.loads, open(run_dir / "generations.jsonl"))}
    cells = defaultdict(list)
    for r in rows.values():
        cells[(r["order"], r["arm"])].append((r, score_request(r)))
    computed = [k for k in TOPO if FORMULA[k] and k not in TEXT]
    m = {"cells": {}, "tests": {}}
    for (order, arm), items in sorted(cells.items()):
        ss = [s for _, s in items if s["parsed"]]
        m["cells"][f"{order}/{arm}"] = {
            "requests": len(items), "parsed": len(ss),
            "order_ok_pct": round(100 * sum(s["order_ok"] for s in ss) / len(ss), 1) if ss else None,
            "all_correct_pct": round(100 * sum(s["all_correct"] for s in ss) / len(items), 1),
            "correct_pct": _rate(ss, "correct", TOPO),
            "forward_correct_pct": _rate(ss, "correct", FORWARD),
            "forward_step_pct": _rate(ss, "step", FORWARD),
            "forward_strict_pct": _strict(items),
            "backward_step_pct": _rate(ss, "step", BACKWARD),
            "other_step_pct": _rate(ss, "step", [k for k in computed if k not in FORWARD + BACKWARD]),
            "refund_or_owed_correct_pct": _rate(ss, "correct", ("f1040_l34", "f1040_l37")),
            "per_forward_step_pct": {k: _rate(ss, "step", (k,)) for k in FORWARD},
            "median_latency_s": _median([r["latency_s"] for r, _ in items]),
            "median_completion_tokens": _median([r.get("completion_tokens") or 0 for r, _ in items])}
    # The test: dLLM minus Qwen on the forward links, with reordered or unparsed answers as failures.
    for order in ORDERS:
        g = {arm: cells.get((order, arm), []) for arm in cfg.arms}
        if all(g.values()):
            f = lambda s: _strict(s["dllm"]) - _strict(s["qwen"])
            m["tests"][order] = {"dllm_minus_qwen_forward_strict": round(f(g), 1), "ci": bootstrap(g, f)}
            # Lenient: reordered answers count, as long as the line matches the model's own later value.
            gp = {arm: [s for _, s in v if s["parsed"]] for arm, v in g.items()}
            fl = lambda s: (_rate(s["dllm"], "step", FORWARD) or 0) - (_rate(s["qwen"], "step", FORWARD) or 0)
            m["tests"][order].update(dllm_minus_qwen_forward_lenient=round(fl(gp), 1), ci_lenient=bootstrap(gp, fl))
    (run_dir / "metrics.json").write_text(json.dumps(m, indent=1))
    lines = ["# Tax-form loops", "", f"Temperature {cfg.temp} for both arms ({TEMPS} where listed); thinking off. "
             "Step % scores a line against its rule applied to the model's own inputs. "
             "Forward strict % counts a reordered or unparsed answer as failing all five forward links.", "",
             "| order | arm | requests | parsed | key order ok % | all correct % | lines correct % | forward correct % "
             "| forward step % | forward strict % | backward step % | other step % | refund/owed correct % | median latency s | median tokens |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, c in m["cells"].items():
        order, arm = k.split("/")
        lines.append(f"| {order} | {arm} | {c['requests']} | {c['parsed']} | {c['order_ok_pct']} | {c['all_correct_pct']} | "
                     f"{c['correct_pct']} | {c['forward_correct_pct']} | {c['forward_step_pct']} | {c['forward_strict_pct']} | {c['backward_step_pct']} | "
                     f"{c['other_step_pct']} | {c['refund_or_owed_correct_pct']} | {c['median_latency_s']} | "
                     f"{c['median_completion_tokens']} |")
    lines += ["", "## Forward step % by line", "", "| order | arm | " + " | ".join(FORWARD) + " |",
              "|---|---|" + "---|" * len(FORWARD)]
    for k, c in m["cells"].items():
        lines.append(f"| {' | '.join(k.split('/'))} | " + " | ".join(str(c["per_forward_step_pct"][f]) for f in FORWARD) + " |")
    lines += ["", "## dLLM minus Qwen, forward strict % (95% bootstrap interval)", ""]
    lines += [f"- `{a}`: {v['dllm_minus_qwen_forward_strict']:+.1f} ({v['ci'][0]:+.1f} to {v['ci'][1]:+.1f}); "
              f"lenient {v['dllm_minus_qwen_forward_lenient']:+.1f} ({v['ci_lenient'][0]:+.1f} to {v['ci_lenient'][1]:+.1f})"
              for a, v in m["tests"].items()]
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n")
    print((run_dir / "summary.md").read_text())


def main():
    p = argparse.ArgumentParser(prog="python -m bench.taxloop.run")
    p.add_argument("stage", choices=["generate", "score", "all", "show"])
    p.add_argument("--run", required=True, help="output goes to bench/results/taxloop-<run>/")
    p.add_argument("--orders", default=",".join(ORDERS), help="comma-separated orders to generate")
    p.add_argument("--arms", default="dllm,qwen", help="comma-separated arms")
    p.add_argument("--n", type=int, default=Config.n, help="cases per cell")
    p.add_argument("--first", type=int, default=0, help="first case index")
    p.add_argument("--probe", action="store_true", help="three requests per cell, to check the pipeline")
    a = p.parse_args()
    cfg = dataclasses.replace(Config(), orders=tuple(a.orders.split(",")), arms=tuple(a.arms.split(",")), n=a.n, first=a.first)
    cfg = dataclasses.replace(cfg, n=3) if a.probe else cfg
    if a.stage == "show":
        print(prompt(case(0), a.run))
        print(json.dumps(truth(case(0)), indent=1))
        return
    run_dir = RESULTS / f"taxloop-{a.run}"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = run_dir / "manifest.json"
    if a.stage != "score" and not manifest.exists():
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        manifest.write_text(json.dumps({
            "started": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "git_commit": commit,
            "config": dataclasses.asdict(cfg), "arms": arms.fingerprint()}, indent=1, default=list))
    if a.stage in ("generate", "all"):
        asyncio.run(generate(cfg, run_dir / "generations.jsonl"))
    if a.stage in ("score", "all"):
        score(cfg, run_dir)


if __name__ == "__main__":
    main()
