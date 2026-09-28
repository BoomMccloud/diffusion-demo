#!/usr/bin/env python3
"""Exploratory 12-case pilot: Nemotron-Labs-Diffusion vs public AR endpoints.

This is not the frozen 36-case business screen. It reuses the business fixtures
and validator, runs fixture 0 of each problem with thinking off and greedy
decoding, and keeps its rows separate from any launch registration.

Subcommands:
  fixtures    write the 12 pilot fixtures to JSON (local, stdlib only)
  nemotron    run Nemotron in diffusion and/or AR mode (Colab GPU, needs torch)
  openrouter  run one OpenRouter model (local, reads OPENROUTER_API_KEY)
  score       score run files against the fixtures and print a summary
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import statistics
import time
import urllib.error
import urllib.request

try:
    from . import business_fixtures as fixtures
except ImportError:
    import business_fixtures as fixtures


PILOT_SCHEMA = "nemotron-pilot-v1"
ITEM_LISTS = {
    "L0": "items", "L1": "items",
    "D1": "transactions", "D2": "tickets", "D3": "orders",
    "M1": "lines", "M2": "expenses", "M3": "groups",
    "C1": "events", "C2": "movements", "C3": "periods",
    "G1": "slots", "G2": "orders", "G3": "attendees",
}
GROUPED = {"M1", "M2", "M3"}
KEY_FIELDS = {"C3": "period"}  # v4 keyed output: field that names each item; M3 has no per-value id

# Easier ladder rungs below the business problems, pilot-only.
# Longer inputs extend the same random sequence, so a shorter case is a prefix of a longer one.
def _generate_l0(rng, count=fixtures.DECISION_COUNT):
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return {"items": [{"id": f"K{i + 1:02d}", "code": "".join(rng.choice(alphabet) for _ in range(6))}
                      for i in range(count)]}


def _generate_l1(rng, count=fixtures.DECISION_COUNT):
    return {"threshold_cents": 50_000,
            "items": [{"id": f"A{i + 1:02d}", "amount_cents": rng.randrange(1_000, 100_001)}
                      for i in range(count)]}


LADDER = {
    "L0": ("copy", "copy-code", _generate_l0, lambda d: [item["code"] for item in d["items"]]),
    "L1": ("threshold", "amount-threshold", _generate_l1,
           lambda d: ["HIGH" if item["amount_cents"] >= d["threshold_cents"] else "LOW" for item in d["items"]]),
}
SOLVERS = {**fixtures.SOLVERS, **{pid: spec[3] for pid, spec in LADDER.items()}}  # four output values per group

# v2 prompts state the exact value grammar and rule precedence the frozen v1
# prompts left implicit, plus a worked example that is not from the input.
V2_RULES = {
    "L0": ("one value per item: the item's code, copied exactly.", 'item {id:"K99",code:"Q7XR2M"} -> "Q7XR2M"'),
    "L1": ("one value per item: HIGH if amount_cents >= threshold_cents, otherwise LOW.",
           'threshold 50000: amount 50000 -> "HIGH"; amount 49999 -> "LOW"'),
    "D1": ("one value per transaction: account_rules[transaction.category].",
           'category "legal" -> "PROFESSIONAL_LEGAL"'),
    "D2": ("one value per ticket, formatted PREFIX_PRODUCT_ISSUE joined by underscores. "
           "PREFIX is REGION_ENT when tier is ENTERPRISE; otherwise the language when language is not EN; otherwise the region.",
           '{tier:ENTERPRISE,region:EU,product:PAY,issue:ACCESS} -> "EU_ENT_PAY_ACCESS"; '
           '{tier:STANDARD,language:JA,region:US,product:CORE,issue:OUTAGE} -> "JA_CORE_OUTAGE"; '
           '{tier:STANDARD,language:EN,region:JP,product:DATA,issue:BILLING} -> "JP_DATA_BILLING"'),
    "D3": ("one value per order, exactly REJECT, REVIEW, or APPROVE, checked in this order: "
           "REJECT if supplier_status is SANCTIONED or jurisdiction is RESTRICTED; "
           "REVIEW if supplier_status is not APPROVED; "
           "REVIEW if contract is false and amount_cents > review_threshold_cents[category]; otherwise APPROVE.",
           '{supplier_status:APPROVED,jurisdiction:DOMESTIC,contract:false,category:IT,amount_cents:130000} -> "REVIEW"'),
    "M1": ("one value per line, including SUBTOTAL lines. For an ITEM line: net = quantity*unit_cents; "
           "tax = round_half_up(net*tax_bps/10000); value is PRICE_ERROR if reported_net_cents != net, "
           "else TAX_ERROR if reported_tax_cents != tax, else VALID. For a SUBTOTAL line: VALID if reported_total_cents "
           "equals the sum of (net+tax) of the three ITEM lines just before it, using the recomputed values, else SUBTOTAL_ERROR.",
           'item {quantity:2,unit_cents:150,tax_bps:750,reported_net_cents:300,reported_tax_cents:23} -> "VALID" (tax 22.5 rounds to 23)'),
    "M2": ("one value per expense, exactly one of APPROVE:OK, DENY:NO_RECEIPT, DENY:ITEM_LIMIT, DENY:DAILY_MEAL_CAP, "
           "checked in this order: DENY:NO_RECEIPT if amount_cents > receipt_required_above_cents and receipt is false; "
           "DENY:ITEM_LIMIT if amount_cents > item_limit_cents[category]; DENY:DAILY_MEAL_CAP if category is MEAL and "
           "(sum of already APPROVED meals on that day + amount_cents) > daily_meal_cap_cents; otherwise APPROVE:OK. "
           "Denied meals do not count toward the daily cap.",
           'day 3: MEAL 5000 approved -> "APPROVE:OK"; next MEAL 4800 on day 3 -> 9800 > 9000 -> "DENY:DAILY_MEAL_CAP"'),
    "M3": ("four values per group, in group order: first one value per component, FULFILL if current stock[sku] >= quantity "
           "else BACKORDER; then one bundle value: INVALID_BUNDLE if required_line_ids is not exactly the component ids in order, "
           "else BACKORDER if any component is BACKORDER, else FULFILL. Only a FULFILL bundle subtracts its component "
           "quantities from stock, which affects later groups.",
           'components stock ok, ok, short -> "FULFILL","FULFILL","BACKORDER","BACKORDER"'),
    "C1": ("one value per event: the running balance in cents after the event, as a decimal string. "
           "DEPOSIT adds amount_cents; WITHDRAWAL and FEE subtract amount_cents; INTEREST adds "
           "round_half_up(balance*rate_bps/10000). Start from opening_balance_cents.",
           'balance 100000, INTEREST rate_bps 5 -> "100050"'),
    "C2": ("one value per movement, formatted STOCK:STATUS. RECEIPT and RETURN add quantity and are ACCEPT. "
           "SALE, DAMAGE, and TRANSFER_OUT subtract quantity and are ACCEPT if quantity <= current stock; otherwise "
           "stock is unchanged and the status is REJECT. STOCK is the stock after the movement. Start from opening_stock.",
           'stock 10, SALE 4 -> "6:ACCEPT"; then DAMAGE 9 -> "6:REJECT"'),
    "C3": ("one value per period: ending principal in cents as a decimal string. interest = round_half_up(principal*periodic_rate_bps/10000); "
           "due = principal + interest; payment = min(due, fixed_payment_cents + extra_payment_cents); new principal = due - payment.",
           'principal 1000000, rate 50, fixed 32000, extra 0 -> interest 5000 -> "973000"'),
    "G1": ("one value per slot, in slot order: the id of the employee assigned, like \"E03\". The slot's position (0-based) must "
           "be in the employee's available_slots, the employee must have the slot's required_skill, each employee works at most "
           "max_shifts slots, and any two slots given to the same employee must start at least minimum_rest_hours apart.",
           'slot S00 needs OPS -> "E04" if E04 has OPS and 0 in available_slots'),
    "G2": ("one value per order, in order: the warehouse id, like \"W2\". The order's region must be in the warehouse's regions, "
           "no warehouse gets more than capacity_orders orders, per-SKU quantities must not exceed stock, and "
           "total cost (cost_per_order per assigned order) must be <= maximum_total_cost.",
           'order in region S -> a warehouse whose regions include S'),
    "G3": ("one value per attendee, in order: the table id, like \"T5\". Each table holds at most capacity attendees and exactly "
           "one host; attendees with needs_accessible go only to accessible tables; no two attendees from the same team share "
           "a table; attendee language must equal table language.",
           'attendee {needs_accessible:true,language:EN} -> an accessible EN table'),
}
PILOT_FIXTURE_INDEX = 0
LONG_GENERATORS = {"D1": fixtures._generate_d1}  # business problems that may exceed 48 decisions
DEFAULT_MAX_NEW_TOKENS = 2048
DEFAULT_REVISION = "0d51902da1f8869f83413ce642fab402fa5641e0"  # Nemotron-Labs-Diffusion-3B used by the first pilot
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_rows(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def append_row(path, row):
    with open(path, "a") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def pending(fixture_list, out, arm):
    done = {(row["case_id"], row["arm"]) for row in load_rows(out)}
    return [fixture for fixture in fixture_list if (fixture["case_id"], arm) not in done]


def strip_thinking(text):
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return text.strip()


def thinking_text(text):
    return text.split("</think>")[0].replace("<think>", "").strip() if "</think>" in text else None


def parse_lines(text, lenient=False):
    """v5: one ID=VALUE line per item -> ordered {id: value}; None if any line is malformed."""
    answer = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        key, sep, value = line.partition("=")
        if not sep:
            if lenient:
                continue
            return None
        key, value = key.strip(), value.strip()
        if lenient:
            key, value = key.strip('"'), value.strip().strip('"').strip()
        if key in answer:
            return None
        answer[key] = value
    return answer


def truncate_input(problem_id, data, decisions):
    data = json.loads(json.dumps(data))
    key = ITEM_LISTS[problem_id]
    data[key] = data[key][: decisions // 4 if problem_id == "M3" else decisions]
    return data


def output_keys(problem_id, data):
    if problem_id == "M3":
        raise SystemExit("M3 has no per-value ids; keyed v4 output is not supported")
    field = KEY_FIELDS.get(problem_id, "id")
    return [str(item[field]) for item in data[ITEM_LISTS[problem_id]]]


def v4_prompt(problem_id, data, keys):
    rule, example = V2_RULES[problem_id]
    rule = rule.replace("one value per", "the value for each")
    return (
        f'Return only one JSON object that maps each input id to its value, like {{"{keys[0]}":"...","{keys[1]}":"..."}}, '
        f"with exactly one key per input item, in source order, from {keys[0]} to {keys[-1]}. "
        'Each value is a plain JSON string such as "HIGH" or "123". No markdown, no code fences, no explanation. '
        f"Produce {rule} Example: {example}. Input:" + fixtures.compact_json(data)
    )


def v5_prompt(problem_id, data, keys):
    rule, example = V2_RULES[problem_id]
    rule = rule.replace("one value per", "the value for each").replace('"', "")
    return (
        f"Return only plain text lines, one line per input item, in source order from {keys[0]} to {keys[-1]}. "
        f"Each line is the item id, an equals sign, and the value, like {keys[0]}=VALUE. "
        "No quotes, no JSON, no markdown, no code fences, no explanation. "
        f"Produce {rule} Example: {example.replace(chr(34), '')}. Input:" + fixtures.compact_json(data)
    )


def v2_prompt(problem_id, data, decisions, version="v2"):
    rule, example = V2_RULES[problem_id]
    quoting = (
        "Every value is a JSON string, including numbers. " if version == "v2"
        else 'Each value is a plain JSON string such as "HIGH" or "123", never nested quotes. '
    )
    return (
        f'Return only one JSON object of the form {{"values":["...", ...]}} with exactly {decisions} string values, '
        "one per input item in source order. " + quoting +
        "No markdown, no code fences, no explanation. "
        f"Produce {rule} Example: {example}. Input:" + fixtures.compact_json(data)
    )


def ladder_base(problem_id, index=PILOT_FIXTURE_INDEX, count=fixtures.DECISION_COUNT):
    dependency_class, name, generate, solve = LADDER[problem_id]
    seed = fixtures.BASE_SEED + 7_000_001 + list(LADDER).index(problem_id) * 100_003 + index * 9_973
    data = generate(random.Random(seed), count)
    return {"problem_id": problem_id, "problem_name": name, "dependency_class": dependency_class,
            "fixture_index": index, "seed": seed, "scoring_mode": "exact",
            "case_id": f"ladder-{problem_id.lower()}-{index:03d}", "input": data,
            "fixture_hash": fixtures.stable_hash(data), "prompt": None}


def long_base(problem_id, index, count):
    """A business fixture with more than 48 items, from the same seed as make_fixture."""
    seed = fixtures._seed(problem_id, index, fixtures.BASE_SEED)
    data = LONG_GENERATORS[problem_id](random.Random(seed), count)
    dependency_class, name = fixtures.PROBLEMS[problem_id]
    return {"problem_id": problem_id, "problem_name": name, "dependency_class": dependency_class,
            "fixture_index": index, "seed": seed, "scoring_mode": "exact",
            "case_id": f"business-{problem_id.lower()}-{index:03d}", "input": data,
            "fixture_hash": fixtures.stable_hash(data), "prompt": None}


def pilot_fixture(problem_id, decisions, prompt_version, index=PILOT_FIXTURE_INDEX):
    count = max(decisions, fixtures.DECISION_COUNT)
    if problem_id in LADDER:
        base = ladder_base(problem_id, index, count)
    elif decisions > fixtures.DECISION_COUNT:
        if problem_id not in LONG_GENERATORS:
            raise SystemExit(f"{problem_id} supports at most {fixtures.DECISION_COUNT} decisions")
        base = long_base(problem_id, index, count)
    else:
        base = fixtures.make_fixture(problem_id, index)
        assert fixtures.validate_fixture(base)
    if problem_id in GROUPED and decisions % 4:
        raise SystemExit("--decisions must be a multiple of 4")
    data = truncate_input(problem_id, base["input"], decisions)
    keys = output_keys(problem_id, data) if prompt_version in ("v4", "v5") else None
    if prompt_version == "v1":
        prompt = base["prompt"]
    elif prompt_version == "v4":
        prompt = v4_prompt(problem_id, data, keys)
    elif prompt_version == "v5":
        prompt = v5_prompt(problem_id, data, keys)
    else:
        prompt = v2_prompt(problem_id, data, decisions, prompt_version)
    if prompt_version == "v1" and decisions != fixtures.DECISION_COUNT:
        raise SystemExit("v1 prompts exist only at 48 decisions")
    fixture = {
        **{k: base[k] for k in ("problem_id", "problem_name", "dependency_class", "fixture_index", "seed", "scoring_mode")},
        "case_id": f"{base['case_id']}-n{decisions}-{prompt_version}",
        "base_fixture_hash": base["fixture_hash"],
        "decision_count": decisions,
        "prompt_version": prompt_version,
        "input": data,
        "prompt": prompt,
        "prompt_hash": fixtures.stable_hash(prompt),
    }
    if keys is not None:
        fixture["output_keys"] = keys
    fixture["fixture_hash"] = fixtures.stable_hash(fixture)
    return fixture


def cmd_fixtures(args):
    pilot = [
        pilot_fixture(pid, n, args.prompt_version, index)
        for index in args.fixture_indices
        for n in args.decisions
        for pid in (args.problems or fixtures.PROBLEM_IDS)
    ]
    Path(args.out).write_text(json.dumps({"schema": PILOT_SCHEMA, "fixtures": pilot}, indent=1))
    print(f"wrote {len(pilot)} fixtures to {args.out}")


def cmd_nemotron(args):
    import torch
    from transformers import AutoModel, AutoTokenizer

    fixture_list = json.loads(Path(args.fixtures).read_text())["fixtures"]
    import transformers
    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision, trust_remote_code=True)
    model = AutoModel.from_pretrained(
        args.model, revision=args.revision, trust_remote_code=True, dtype=torch.bfloat16,
    ).cuda().eval()
    stop_ids = {tokenizer.eos_token_id, tokenizer.convert_tokens_to_ids("<|im_end|>")} - {None}
    gpu = torch.cuda.get_device_name(0)
    revision = getattr(model.config, "_commit_hash", None)

    def encode(prompt):
        text = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}], tokenize=False,
            add_generation_prompt=True, enable_thinking=args.thinking,
        )
        return tokenizer(text, return_tensors="pt").input_ids.cuda()

    def cap_for(fixture):
        if not args.tokens_per_value:
            return args.max_new_tokens
        wanted = fixture["decision_count"] * args.tokens_per_value + 64
        return min(args.max_new_tokens, -(-wanted // args.block_length) * args.block_length)

    def run(mode, ids, cap=None):
        cap = cap or args.max_new_tokens
        with torch.no_grad():
            if mode == "ar":
                return model.ar_generate(ids, max_new_tokens=cap)
            if mode == "linear_spec":
                return model.linear_spec_generate(ids, max_new_tokens=cap, block_length=args.block_length)
            return model.generate(
                ids, max_new_tokens=cap,
                block_length=args.block_length, threshold=args.threshold,
            )

    for mode in args.modes.split(","):
        arm = f"{args.arm_prefix}-{mode}"
        todo = pending(fixture_list, args.out, arm)
        run(mode, encode('Return exactly {"values":["READY"]} and no other text.'))
        for fixture in todo:
            ids = encode(fixture["prompt"])
            started_at = utc_now()
            torch.cuda.synchronize()
            start = time.perf_counter()
            error = None
            try:
                out, nfe = run(mode, ids, cap_for(fixture))
            except Exception as exc:  # retain the failure as a row
                out, nfe, error = None, None, {"type": type(exc).__name__, "message": str(exc)}
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - start
            generated = out[0, ids.shape[1]:].tolist() if out is not None else []
            stop_at = next((i for i, tok in enumerate(generated) if tok in stop_ids), None)
            kept = generated if stop_at is None else generated[:stop_at]
            raw = tokenizer.decode(kept, skip_special_tokens=False)
            row = {
                "schema": PILOT_SCHEMA,
                "arm": arm,
                "mode": mode,
                "model": args.model,
                "model_revision": revision,
                "gpu": gpu,
                "torch_version": torch.__version__,
                "transformers_version": transformers.__version__,
                "thinking": args.thinking,
                "case_id": fixture["case_id"],
                "fixture_hash": fixture["fixture_hash"],
                "prompt_hash": fixture["prompt_hash"],
                "prompt_tokens": int(ids.shape[1]),
                "output_tokens": len(kept),
                "stop_reason": "error" if error else ("eos" if stop_at is not None else "max_new_tokens"),
                "nfe": int(nfe) if nfe is not None else None,
                "max_new_tokens": cap_for(fixture),
                "block_length": args.block_length if mode != "ar" else None,
                "threshold": args.threshold if mode == "diffusion" else None,
                "elapsed_seconds": round(elapsed, 4),
                "started_at": started_at,
                "completed_at": utc_now(),
                "raw_output": raw,
                "reasoning": thinking_text(raw),
                "final_output": strip_thinking(raw),
                "error": error,
            }
            append_row(args.out, row)
            print(json.dumps({k: row[k] for k in ("arm", "case_id", "stop_reason", "output_tokens", "nfe", "elapsed_seconds")}), flush=True)


def read_api_key(env_file):
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    for line in Path(env_file).read_text().splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "OPENROUTER_API_KEY":
            return value.strip().strip('"').strip("'")
    raise SystemExit(f"OPENROUTER_API_KEY not found in environment or {env_file}")


def cmd_openrouter(args):
    fixture_list = json.loads(Path(args.fixtures).read_text())["fixtures"]
    api_key = read_api_key(args.env_file)
    arm = f"openrouter-{args.model.split('/')[-1]}"
    for fixture in pending(fixture_list, args.out, arm):
        body = {
            "model": args.model,
            "messages": [{"role": "user", "content": fixture["prompt"]}],
            "temperature": 0,
            "max_tokens": args.max_new_tokens,
        }
        if args.reasoning_off:
            body["reasoning"] = {"enabled": False}
        request = urllib.request.Request(
            OPENROUTER_URL, data=json.dumps(body).encode(), method="POST",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        started_at = utc_now()
        start = time.perf_counter()
        response, error = None, None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=args.timeout) as handle:
                    response = json.loads(handle.read())
                error = response.get("error")
                break
            except urllib.error.HTTPError as exc:
                error = {"type": "HTTPError", "status": exc.code, "message": exc.read().decode(errors="replace")[:500]}
                if exc.code not in (429, 500, 502, 503, 504):
                    break
            except (urllib.error.URLError, TimeoutError) as exc:
                error = {"type": type(exc).__name__, "message": str(exc)}
            time.sleep(2 ** attempt * 2)
        elapsed = time.perf_counter() - start
        choice = (response or {}).get("choices", [{}])[0]
        message = choice.get("message") or {}
        raw = message.get("content") or ""
        usage = (response or {}).get("usage") or {}
        row = {
            "schema": PILOT_SCHEMA,
            "arm": arm,
            "mode": "ar-endpoint",
            "model": args.model,
            "served_model": (response or {}).get("model"),
            "provider": (response or {}).get("provider"),
            "generation_id": (response or {}).get("id"),
            "thinking": False,
            "case_id": fixture["case_id"],
            "fixture_hash": fixture["fixture_hash"],
            "prompt_hash": fixture["prompt_hash"],
            "prompt_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "stop_reason": "error" if error else choice.get("finish_reason"),
            "max_new_tokens": args.max_new_tokens,
            "elapsed_seconds": round(elapsed, 4),
            "started_at": started_at,
            "completed_at": utc_now(),
            "raw_output": raw,
            "reasoning_content": message.get("reasoning"),
            "final_output": strip_thinking(raw),
            "error": error,
        }
        append_row(args.out, row)
        print(json.dumps({k: row[k] for k in ("arm", "case_id", "stop_reason", "output_tokens", "elapsed_seconds", "provider")}), flush=True)


def _lenient_answer(text):
    """Largest {...} span, to tell formatting failures from wrong answers."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def keyed_to_values(fixture, answer):
    """v4: {id: value} with exactly the registered ids, in order -> {"values": [...]}."""
    keys = fixture.get("output_keys")
    if keys is None or not isinstance(answer, dict) or "values" in answer:
        return answer
    if list(answer) != keys:
        return {}
    return {"values": [answer[k] for k in keys]}


def evaluate(fixture, answer):
    answer = keyed_to_values(fixture, answer)
    n = fixture["decision_count"]
    values = answer.get("values") if isinstance(answer, dict) and set(answer) == {"values"} else None
    if not isinstance(values, list) or len(values) != n or not all(isinstance(v, str) for v in values):
        return {"valid": False, "per_decision_correct": 0, "first_error": 0,
                "constraint_violations": ["canonical_answer_contract"], "objective_value": None}
    pid = fixture["problem_id"]
    if pid in SOLVERS:
        expected = [str(v) for v in SOLVERS[pid](fixture["input"])]
        correct = [a == b for a, b in zip(values, expected)]
        return {"valid": all(correct), "per_decision_correct": sum(correct),
                "first_error": next((i for i, ok in enumerate(correct) if not ok), None),
                "constraint_violations": [], "objective_value": None}
    violations, objective = fixtures.GLOBAL_VALIDATORS[pid](fixture["input"], values)
    return {"valid": not violations, "per_decision_correct": None, "first_error": None,
            "constraint_violations": violations, "objective_value": objective}


def _coerce(answer):
    """Normalize format-only quirks: numbers, padding, and doubled quotes."""
    if isinstance(answer, dict) and "values" not in answer:
        return {k: str(v).strip().strip('"').strip() for k, v in answer.items()}
    if isinstance(answer, dict) and isinstance(answer.get("values"), list):
        return {"values": [str(v).strip().strip('"').strip() for v in answer["values"]]}
    return None


def score_row(fixture, row):
    if fixture["prompt_version"] == "v5":
        parsed = parse_lines(row["final_output"])
        lenient_answer = parse_lines(row["final_output"], lenient=True)
    else:
        try:
            parsed = json.loads(row["final_output"])
        except json.JSONDecodeError:
            parsed = None
        lenient_answer = _coerce(_lenient_answer(row["final_output"]))
    semantic = evaluate(fixture, parsed if isinstance(parsed, dict) else {})
    lenient = evaluate(fixture, lenient_answer or {})
    contract_ok = semantic["constraint_violations"] != ["canonical_answer_contract"]
    if row.get("error"):
        outcome = "error"
    elif row["stop_reason"] not in ("eos", "stop"):
        outcome = "truncated"
    elif semantic["valid"]:
        outcome = "correct"
    elif contract_ok:
        outcome = "incorrect"
    else:
        outcome = "invalid_format"
    return {
        **semantic,
        "outcome": outcome,
        "lenient_valid": lenient["valid"],
        "lenient_per_decision_correct": lenient["per_decision_correct"],
    }


def cmd_score(args):
    by_case = {f["case_id"]: f for f in json.loads(Path(args.fixtures).read_text())["fixtures"]}
    scored = []
    for path in args.runs:
        for row in load_rows(path):
            fixture = by_case[row["case_id"]]
            assert row["fixture_hash"] == fixture["fixture_hash"], row["case_id"]
            scored.append({**row, **score_row(fixture, row)})
    arms = sorted({row["arm"] for row in scored})
    summary = {}
    for arm in arms:
        rows = [row for row in scored if row["arm"] == arm]
        exact = [row for row in rows if row["per_decision_correct"] is not None]
        summary[arm] = {
            "attempts": len(rows),
            "valid": sum(row["valid"] and row["outcome"] == "correct" for row in rows),
            "lenient_valid": sum(bool(row["lenient_valid"]) for row in rows),
            "outcomes": {o: sum(r["outcome"] == o for r in rows) for o in sorted({r["outcome"] for r in rows})},
            "exact_case_decisions_correct": f"{sum(r['per_decision_correct'] for r in exact)}/{sum(by_case[r['case_id']]['decision_count'] for r in exact)}",
            "lenient_exact_decisions_correct": f"{sum(r['lenient_per_decision_correct'] or 0 for r in exact)}/{sum(by_case[r['case_id']]['decision_count'] for r in exact)}",
            "by_class": {
                cls: f"{sum(r['valid'] and r['outcome'] == 'correct' for r in rows if by_case[r['case_id']]['dependency_class'] == cls)}"
                     f"/{sum(by_case[r['case_id']]['dependency_class'] == cls for r in rows)}"
                for cls in ("direct", "mixed", "chained", "global")
            },
            "median_seconds": statistics.median(r["elapsed_seconds"] for r in rows) if rows else None,
            "median_output_tokens": statistics.median(r["output_tokens"] or 0 for r in rows) if rows else None,
            "median_nfe": statistics.median(r["nfe"] for r in rows) if rows and all(r.get("nfe") is not None for r in rows) else None,
        }
    if args.out:
        Path(args.out).write_text(json.dumps({"schema": PILOT_SCHEMA, "summary": summary, "rows": [
            {k: r.get(k) for k in ("arm", "case_id", "outcome", "valid", "per_decision_correct", "first_error",
                                    "constraint_violations", "objective_value", "lenient_valid",
                                    "stop_reason", "output_tokens", "nfe", "elapsed_seconds")}
            for r in scored]}, indent=1))
    print(json.dumps(summary, indent=1))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fixtures")
    p.add_argument("--out", required=True)
    p.add_argument("--prompt-version", choices=("v1", "v2", "v3", "v4", "v5"), default="v4")
    p.add_argument("--decisions", type=int, nargs="+", default=[fixtures.DECISION_COUNT])
    p.add_argument("--fixture-indices", type=int, nargs="+", default=[PILOT_FIXTURE_INDEX])
    p.add_argument("--problems", nargs="+")
    p.set_defaults(func=cmd_fixtures)

    p = sub.add_parser("nemotron")
    p.add_argument("--fixtures", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--model", default="nvidia/Nemotron-Labs-Diffusion-3B")
    p.add_argument("--revision", default=DEFAULT_REVISION)
    p.add_argument("--thinking", action="store_true", help="render the chat template with enable_thinking=True")
    p.add_argument("--arm-prefix", default="nemotron-3b")
    p.add_argument("--modes", default="diffusion,ar")
    p.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    p.add_argument("--block-length", type=int, default=32)
    p.add_argument("--threshold", type=float, default=0.9)
    p.add_argument("--tokens-per-value", type=int, default=0, help="scale the cap to N values; 0 keeps --max-new-tokens")
    p.set_defaults(func=cmd_nemotron)

    p = sub.add_parser("openrouter")
    p.add_argument("--fixtures", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--env-file", default=str(Path(__file__).resolve().parents[1] / ".env.local"))
    p.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    p.add_argument("--reasoning-off", action="store_true")
    p.add_argument("--timeout", type=float, default=300)
    p.set_defaults(func=cmd_openrouter)

    p = sub.add_parser("score")
    p.add_argument("--fixtures", required=True)
    p.add_argument("--out")
    p.add_argument("runs", nargs="+")
    p.set_defaults(func=cmd_score)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
