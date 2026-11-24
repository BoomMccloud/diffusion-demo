#!/usr/bin/env python3
"""Addition-in-words benchmark against the hosted DLLM endpoint.

Repeats https://github.com/simonw/research/tree/main/qwen38-addition-in-words
on the same frozen cases. Standard library only.

    python3 addition_in_words.py self-test
    python3 addition_in_words.py prepare --config off
    python3 addition_in_words.py smoke --config off
    python3 addition_in_words.py run --config off
    python3 addition_in_words.py summarize --config off
    python3 addition_in_words.py compare
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import random
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RESULTS = HERE / "results"

UPSTREAM = (
    "https://raw.githubusercontent.com/simonw/research/main/qwen38-addition-in-words/"
    "runs/qwen3.8-27b-q4_k_m-seed-20260929/"
)
UPSTREAM_PAIRS_SHA256 = "a1bbd56ef958aa30c2d76c52d57bac43b4e0e96d43e75ae18f1110c82b4053aa"
UPSTREAM_RESULTS = UPSTREAM + "results.csv"

PROMPT_TEMPLATE = (
    "What is {a} + {b}? Please write your answer in words. "
    "Do not include any other text or information, just the answer in words."
)
DIGIT_MAX = 13
REQUEST_TIMEOUT_SECONDS = 1800
MAX_ATTEMPTS = 3

# The upstream thinking run used max_tokens=-1 on a 32,768-token context.
# SGLang rejects -1, so the cap is the same context less the longest prompt.
CONFIGS: dict[str, dict[str, Any]] = {
    "off": {
        "run": "thinking-off-full",
        "thinking": False,
        "max_tokens": 128,
        "selection": "all 5,070 frozen cases in the upstream shuffled order",
    },
    "on": {
        "run": "thinking-on-one-per-cell-easiest-first",
        "thinking": True,
        "max_tokens": 32_000,
        "selection": "replicate r01 from each of the 169 cells, easiest first",
    },
}

ONES = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen"
).split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
SCALES = ["", "thousand", "million", "billion", "trillion", "quadrillion"]
SMALL_VALUE = {word: value for value, word in enumerate(ONES)}
TENS_VALUE = {word: value * 10 for value, word in enumerate(TENS) if value >= 2}
SCALE_VALUE = {word: 1000**power for power, word in enumerate(SCALES) if word}
MAX_PARSED = 20_000_000_000_000

RESULT_FIELDS = [
    "case_id", "a_digits", "b_digits", "replicate", "request_order", "a", "b",
    "correct_answer", "result_digits", "carry_count", "longest_carry_chain",
    "expected_words", "prompt", "raw_response", "reasoning_content", "parsed_answer",
    "numeric_correct", "instruction_compliant", "canonical_text_correct", "parse_error",
    "finish_reason", "matched_stop", "completion_tokens", "reasoning_tokens",
    "prompt_tokens", "request_elapsed_seconds", "attempts", "response_id", "created",
]


# Number words ---------------------------------------------------------------


def number_to_words(number: int) -> str:
    if number == 0:
        return "zero"
    groups = []
    power = 0
    while number:
        number, chunk = divmod(number, 1000)
        if chunk:
            hundreds, rest = divmod(chunk, 100)
            words = []
            if hundreds:
                words += [ONES[hundreds], "hundred"]
            if rest >= 20:
                tens, ones = divmod(rest, 10)
                words.append(f"{TENS[tens]}-{ONES[ones]}" if ones else TENS[tens])
            elif rest:
                words.append(ONES[rest])
            if SCALES[power]:
                words.append(SCALES[power])
            groups.append(" ".join(words))
        power += 1
    return " ".join(reversed(groups))


def number_tokens(text: str) -> tuple[list[str] | None, str]:
    """Normalize a visible answer into number-word tokens, or explain why not."""
    if not text or not text.strip():
        return None, "empty_response"
    text = text.strip().lower().replace("–", "-").replace("—", "-")
    text = re.sub(r"[.!?]+$", "", text).strip()
    tokens = text.replace(",", " ").replace("-", " ").split()
    if not tokens:
        return None, "empty_response"
    for token in tokens:
        if not token.isascii() or not token.isalpha():
            return None, f"non_word_token:{token}"
        if not (
            token in SMALL_VALUE or token in TENS_VALUE or token in SCALE_VALUE
            or token in ("hundred", "and")
        ):
            return None, f"unknown_word:{token}"
    return tokens, ""


def parse_number_words(text: str) -> tuple[int | None, str]:
    """Parse a whole response as one English number. Same rules as upstream."""
    tokens, error = number_tokens(text)
    if tokens is None:
        return None, error
    if tokens == ["zero"]:
        return 0, ""
    if "zero" in tokens:
        return None, "zero_in_nonzero_number"
    total = group = 0
    last_scale = math.inf
    previous = "start"
    for index, token in enumerate(tokens):
        if token == "and":
            following = tokens[index + 1] if index + 1 < len(tokens) else None
            if previous not in ("hundred", "scale"):
                return None, "misplaced_and"
            if following is None:
                return None, "incomplete_number"
            if following == "zero" or (following not in SMALL_VALUE and following not in TENS_VALUE):
                return None, "misplaced_and"
            previous = "and"
        elif token in SMALL_VALUE:
            value = SMALL_VALUE[token]
            if previous == "small":
                return None, "invalid_small_number_sequence"
            if previous == "tens" and not 0 < value < 10:
                return None, "invalid_small_number_after_tens"
            group += value
            previous = "small"
        elif token in TENS_VALUE:
            if previous in ("small", "tens"):
                return None, "invalid_tens_sequence"
            group += TENS_VALUE[token]
            previous = "tens"
        elif token == "hundred":
            if previous != "small" or not 0 < group < 10:
                return None, "invalid_hundred"
            group *= 100
            previous = "hundred"
        else:
            scale = SCALE_VALUE[token]
            if group <= 0:
                return None, "scale_without_value"
            if scale >= last_scale:
                return None, "non_descending_scale"
            total += group * scale
            group = 0
            last_scale = scale
            previous = "scale"
    if previous in ("start", "and"):
        return None, "incomplete_number"
    value = total + group
    if value > MAX_PARSED:
        return None, "number_above_supported_maximum"
    return value, ""


def canonical(text: str) -> str | None:
    tokens, _ = number_tokens(text)
    return None if tokens is None else " ".join(tokens)


# Files ----------------------------------------------------------------------


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run_dir(config: str) -> Path:
    return RESULTS / CONFIGS[config]["run"]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, value: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def log(config: str, message: str) -> None:
    line = f"{utc_now()} {message}"
    print(line, flush=True)
    with (run_dir(config) / "run.log").open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


# Endpoint -------------------------------------------------------------------


def load_env() -> None:
    env = REPO / ".env.local"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() and not key.lstrip().startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def server_root() -> str:
    """Accept either a base URL or a full /chat/completions URL."""
    load_env()
    url = os.environ.get("DIFFUSION_BASE_URL")
    if not url:
        sys.exit("DIFFUSION_BASE_URL is not set (expected in .env.local)")
    url = url.rstrip("/")
    for suffix in ("/chat/completions", "/v1"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return url


def get_json(url: str, timeout: float = 30) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict[str, Any]) -> tuple[int, Any, float]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        body = error.read()
        status = error.code
    elapsed = time.perf_counter() - started
    try:
        return status, json.loads(body.decode("utf-8")), elapsed
    except ValueError:
        return status, {"raw_body": body.decode("utf-8", "replace")}, elapsed


def payload(case: dict[str, Any], config: str, model: str) -> dict[str, Any]:
    seed = int.from_bytes(hashlib.sha256(case["case_id"].encode()).digest()[:4], "big")
    return {
        "model": model,
        "messages": [{"role": "user", "content": case["prompt"]}],
        "temperature": 0,
        "top_k": -1,  # SGLang's "disabled"; upstream llama-server used 0.
        "top_p": 1,
        "min_p": 0,
        "repetition_penalty": 1,
        "max_tokens": CONFIGS[config]["max_tokens"],
        "seed": seed,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": CONFIGS[config]["thinking"]},
    }


# Cases ----------------------------------------------------------------------


def load_upstream_pairs(dest: Path) -> list[dict[str, Any]]:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(UPSTREAM + "pairs.csv", dest)
    if sha256(dest) != UPSTREAM_PAIRS_SHA256:
        sys.exit(f"{dest} does not match the upstream pairs.csv hash")
    rows: list[dict[str, Any]] = []
    for row in read_csv(dest):
        case = dict(row)
        for key in ("a_digits", "b_digits", "replicate", "request_order", "a", "b",
                    "correct_answer", "result_digits", "carry_count", "longest_carry_chain"):
            case[key] = int(case[key])
        if case["a"] + case["b"] != case["correct_answer"]:
            sys.exit(f"bad sum in {case['case_id']}")
        if case["expected_words"] != number_to_words(case["correct_answer"]):
            sys.exit(f"expected_words disagrees with our renderer in {case['case_id']}")
        if case["prompt"] != PROMPT_TEMPLATE.format(a=case["a"], b=case["b"]):
            sys.exit(f"prompt differs from template in {case['case_id']}")
        rows.append(case)
    if len(rows) != DIGIT_MAX * DIGIT_MAX * 30:
        sys.exit(f"expected 5070 pairs, got {len(rows)}")
    return rows


def select_cases(config: str, pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if config == "off":
        return sorted(pairs, key=lambda row: row["request_order"])
    rows = [dict(row) for row in pairs if row["replicate"] == 1]
    # Upstream's easiest-first key. request_order here is the shuffled order.
    rows.sort(key=lambda row: (
        max(row["a_digits"], row["b_digits"]),
        min(row["a_digits"], row["b_digits"]),
        row["carry_count"], row["longest_carry_chain"], row["result_digits"],
        row["request_order"],
    ))
    for order, row in enumerate(rows, start=1):
        row["request_order"] = order
    return rows


def load_cases(config: str) -> list[dict[str, Any]]:
    directory = run_dir(config)
    if not (directory / "cases.csv").exists():
        sys.exit(f"run `prepare --config {config}` first")
    rows = []
    for row in read_csv(directory / "cases.csv"):
        for key in ("a_digits", "b_digits", "replicate", "request_order", "a", "b",
                    "correct_answer", "result_digits", "carry_count", "longest_carry_chain"):
            row[key] = int(row[key])
        rows.append(row)
    return rows


# Grading --------------------------------------------------------------------


def grade(case: dict[str, Any], response: dict[str, Any], elapsed: float, attempts: int) -> dict[str, Any]:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content") or ""
    parsed, error = parse_number_words(content)
    usage = response.get("usage") or {}
    return {
        **case,
        "raw_response": content,
        "reasoning_content": message.get("reasoning_content") or "",
        "parsed_answer": "" if parsed is None else parsed,
        "numeric_correct": parsed == case["correct_answer"],
        "instruction_compliant": parsed is not None,
        "canonical_text_correct": canonical(content) == canonical(case["expected_words"]),
        "parse_error": error,
        "finish_reason": choice.get("finish_reason") or "",
        "matched_stop": choice.get("matched_stop"),
        "completion_tokens": usage.get("completion_tokens", ""),
        "reasoning_tokens": usage.get("reasoning_tokens", ""),
        "prompt_tokens": usage.get("prompt_tokens", ""),
        "request_elapsed_seconds": round(elapsed, 6),
        "attempts": attempts,
        "response_id": response.get("id", ""),
        "created": response.get("created", ""),
    }


def load_graded(config: str) -> dict[str, dict[str, Any]]:
    """Rebuild graded rows from attempts.jsonl so grading never depends on run-time state."""
    cases = {case["case_id"]: case for case in load_cases(config)}
    path = run_dir(config) / "attempts.jsonl"
    graded: dict[str, dict[str, Any]] = {}
    tries: Counter[str] = Counter()
    if not path.exists():
        return graded
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        case_id = record["case_id"]
        tries[case_id] += 1
        if record["status"] == 200 and case_id in cases and case_id not in graded:
            graded[case_id] = grade(cases[case_id], record["response"], record["elapsed_seconds"], tries[case_id])
    return graded


# Commands -------------------------------------------------------------------


def cmd_self_test(_: argparse.Namespace) -> None:
    samples = {
        0: "zero", 11: "eleven", 21: "twenty-one", 105: "one hundred five",
        1_001: "one thousand one",
        93_847_696: "ninety-three million eight hundred forty-seven thousand six hundred ninety-six",
    }
    for number, words in samples.items():
        assert number_to_words(number) == words, (number, number_to_words(number))
        assert parse_number_words(words) == (number, ""), words
    assert parse_number_words(
        "Ninety-three million, eight hundred and forty-seven thousand, six hundred and ninety-six."
    ) == (93_847_696, "")
    for bad in ["The answer is eleven", "11", "one one", "one million two billion",
                "one hundred and", "twenty ten", "one hundred hundred", "one million million",
                "one and two", "one and thousand", "one hundred and thousand", "zero one",
                "one thousand zero", "twenty trillion one", "", "**sixteen**"]:
        assert parse_number_words(bad)[0] is None, bad
    for words, number in {"one hundred and one": 101, "one thousand and one": 1001,
                          "twenty trillion": 20_000_000_000_000}.items():
        assert parse_number_words(words) == (number, ""), words
    rng = random.Random(8675309)
    for _ in range(10_000):
        number = rng.randint(0, MAX_PARSED)
        assert parse_number_words(number_to_words(number)) == (number, ""), number
    print("self-test passed")


def cmd_prepare(args: argparse.Namespace) -> None:
    config = args.config
    directory = run_dir(config)
    pairs = load_upstream_pairs(RESULTS / "upstream_pairs.csv")
    cases = select_cases(config, pairs)
    directory.mkdir(parents=True, exist_ok=True)
    write_csv(directory / "cases.csv", cases, list(cases[0].keys()))
    root = server_root()
    models = get_json(root + "/v1/models")
    info = get_json(root + "/get_server_info")
    write_json(directory / "server_models.json", models)
    write_json(directory / "server_info.json", info)
    model = models["data"][0]["id"]
    write_json(directory / "manifest.json", {
        "benchmark": "addition-in-words, repeat of simonw/research qwen38-addition-in-words",
        "config": config,
        "selection": CONFIGS[config]["selection"],
        "expected_cases": len(cases),
        "upstream_pairs_url": UPSTREAM + "pairs.csv",
        "upstream_pairs_sha256": UPSTREAM_PAIRS_SHA256,
        "cases_csv_sha256": sha256(directory / "cases.csv"),
        "prompt_template": PROMPT_TEMPLATE,
        "endpoint": "DIFFUSION_BASE_URL from .env.local (kept out of the repo)",
        "model": model,
        "model_path": info.get("model_path"),
        "server_version": info.get("version"),
        "speculative_algorithm": info.get("speculative_algorithm"),
        "dllm_block_size": info.get("dllm_block_size"),
        "dllm_spec_accept_rule": info.get("dllm_spec_accept_rule"),
        "client_concurrency": 1,
        "request_template": payload(cases[0], config, model),
        "runner_sha256": sha256(Path(__file__)),
        "prepared_at": utc_now(),
    })
    print(f"prepared {len(cases)} cases in {directory.relative_to(REPO)}; model {model}")


def call(case: dict[str, Any], config: str, model: str, root: str, attempts_path: Path) -> dict[str, Any] | None:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        body = payload(case, config, model)
        try:
            status, response, elapsed = post_json(root + "/v1/chat/completions", body)
        except (OSError, TimeoutError) as error:
            status, response, elapsed = 0, {"error": repr(error)}, 0.0
        append_jsonl(attempts_path, {
            "case_id": case["case_id"], "attempt": attempt, "at": utc_now(),
            "request": body, "status": status, "response": response,
            "elapsed_seconds": elapsed,
        })
        if status == 200:
            return grade(case, response, elapsed, attempt)
        time.sleep(2 * attempt)
    return None


def cmd_smoke(args: argparse.Namespace) -> None:
    config = args.config
    manifest = json.loads((run_dir(config) / "manifest.json").read_text())
    cases = load_cases(config)
    picks = [cases[0], cases[len(cases) // 2], cases[-1]] if config == "on" else cases[:5]
    path = run_dir(config) / "smoke.jsonl"
    for case in picks:
        row = call(case, config, manifest["model"], server_root(), path)
        if row is None:
            print(f"{case['case_id']}: failed, see {path}")
            continue
        print(f"{case['case_id']} {case['a']} + {case['b']}: correct={row['numeric_correct']} "
              f"finish={row['finish_reason']} tokens={row['completion_tokens']} "
              f"reasoning={row['reasoning_tokens']} {row['request_elapsed_seconds']:.2f}s")
        print(f"  expected: {case['expected_words']}")
        print(f"  answer:   {row['raw_response'][:300]!r}")


def cmd_run(args: argparse.Namespace) -> None:
    config = args.config
    directory = run_dir(config)
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest["runner_sha256"] != sha256(Path(__file__)):
        log(config, "warning: runner changed since prepare")
    cases = load_cases(config)
    done = load_graded(config)
    todo = [case for case in cases if case["case_id"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    log(config, f"run start: {len(done)} done, {len(todo)} to go")
    attempts_path = directory / "attempts.jsonl"
    root = server_root()
    started = time.time()
    correct = sum(bool(row["numeric_correct"]) for row in done.values())
    for index, case in enumerate(todo, start=1):
        row = call(case, config, manifest["model"], root, attempts_path)
        if row is None:
            log(config, f"{case['case_id']}: failed after {MAX_ATTEMPTS} attempts")
            continue
        correct += bool(row["numeric_correct"])
        if index % args.progress_every == 0 or index == len(todo):
            rate = (time.time() - started) / index
            log(config, f"{len(done) + index}/{len(cases)} correct so far {correct}, "
                        f"{rate:.2f}s per case, eta {rate * (len(todo) - index) / 60:.1f} min")
    log(config, "run end")


def pct(numerator: int, denominator: int) -> float | None:
    return round(100 * numerator / denominator, 2) if denominator else None


def cmd_summarize(args: argparse.Namespace) -> None:
    config = args.config
    directory = run_dir(config)
    cases = load_cases(config)
    graded = load_graded(config)
    rows = [graded[case["case_id"]] for case in cases if case["case_id"] in graded]
    write_csv(directory / "results.csv", rows, RESULT_FIELDS)
    n = len(rows)
    by_cell: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_cell[(row["a_digits"], row["b_digits"])].append(row)
    cell_rows = []
    for a_digits in range(1, DIGIT_MAX + 1):
        for b_digits in range(1, DIGIT_MAX + 1):
            cell = by_cell.get((a_digits, b_digits), [])
            good = sum(row["numeric_correct"] for row in cell)
            cell_rows.append({"a_digits": a_digits, "b_digits": b_digits, "n": len(cell),
                              "correct": good, "accuracy_pct": pct(good, len(cell))})
    write_csv(directory / "cell_accuracy.csv", cell_rows, list(cell_rows[0].keys()))
    matrix = [{"a_digits": a, **{f"b{b}": next(c["accuracy_pct"] for c in cell_rows
                                               if c["a_digits"] == a and c["b_digits"] == b)
                                  for b in range(1, DIGIT_MAX + 1)}}
              for a in range(1, DIGIT_MAX + 1)]
    write_csv(directory / "accuracy_matrix.csv", matrix, list(matrix[0].keys()))
    write_heatmap(directory / "heatmap.svg", cell_rows, config, n)

    def band(lo: int, hi: int) -> float | None:
        subset = [row for row in rows if lo <= max(row["a_digits"], row["b_digits"]) <= hi]
        return pct(sum(row["numeric_correct"] for row in subset), len(subset))

    latency = [row["request_elapsed_seconds"] for row in rows]
    tokens = [int(row["completion_tokens"]) for row in rows if row["completion_tokens"] != ""]
    reasoning = [int(row["reasoning_tokens"] or 0) for row in rows]
    summary = {
        "config": config,
        "expected_cases": len(cases),
        "graded_cases": n,
        "numeric_correct": sum(row["numeric_correct"] for row in rows),
        "instruction_compliant": sum(row["instruction_compliant"] for row in rows),
        "canonical_text_correct": sum(row["canonical_text_correct"] for row in rows),
        "accuracy_by_longer_operand_pct": {"1-3": band(1, 3), "4-6": band(4, 6),
                                           "7-9": band(7, 9), "10-13": band(10, 13)},
        "latency_seconds": {"median": statistics.median(latency) if latency else None,
                            "mean": statistics.fmean(latency) if latency else None,
                            "total": sum(latency)},
        "completion_tokens": {"median": statistics.median(tokens) if tokens else None,
                              "total": sum(tokens)},
        "reasoning_tokens": {"median": statistics.median(reasoning) if reasoning else None,
                             "total": sum(reasoning)},
        "first_attempt_successes": sum(row["attempts"] == 1 for row in rows),
        "finish_reasons": dict(Counter(row["finish_reason"] for row in rows)),
        "parse_errors": dict(Counter(row["parse_error"].split(":")[0] for row in rows if row["parse_error"])),
        "think_tag_leaks": sum("<think" in row["raw_response"] or "</think" in row["raw_response"] for row in rows),
        "empty_answers": sum(not row["raw_response"].strip() for row in rows),
        "summarized_at": utc_now(),
    }
    for key in ("numeric_correct", "instruction_compliant", "canonical_text_correct"):
        summary[key + "_pct"] = pct(summary[key], n)
    write_json(directory / "summary.json", summary)
    print(json.dumps(summary, indent=2))


def write_heatmap(path: Path, cells: list[dict[str, Any]], config: str, n: int) -> None:
    """Orange (0%) to neutral to blue (100%), the upstream colorblind-safe scheme, as SVG."""
    size, left, top = 44, 70, 70
    stops = [(0.0, (230, 97, 1)), (0.5, (247, 247, 247)), (1.0, (33, 102, 172))]

    def color(value: float) -> str:
        for (x0, c0), (x1, c1) in zip(stops, stops[1:]):
            if value <= x1:
                t = (value - x0) / (x1 - x0)
                return "#%02x%02x%02x" % tuple(round(a + (b - a) * t) for a, b in zip(c0, c1))
        return "#2166ac"

    title = ("Thinking off, 30 cases per cell" if config == "off"
             else "Thinking on, one case per cell, easiest first")
    width = left + size * DIGIT_MAX + 20
    height = top + size * DIGIT_MAX + 50
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'font-family="sans-serif" font-size="11">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<text x="{left}" y="22" font-size="14" font-weight="bold">Addition in words: {title} (n = {n})</text>',
        f'<text x="{left + size * DIGIT_MAX / 2}" y="{top - 22}" text-anchor="middle">digits in b</text>',
        f'<text x="18" y="{top + size * DIGIT_MAX / 2}" text-anchor="middle" '
        f'transform="rotate(-90 18 {top + size * DIGIT_MAX / 2})">digits in a</text>',
    ]
    for i in range(1, DIGIT_MAX + 1):
        parts.append(f'<text x="{left + (i - 0.5) * size}" y="{top - 6}" text-anchor="middle">{i}</text>')
        parts.append(f'<text x="{left - 8}" y="{top + (i - 0.5) * size + 4}" text-anchor="end">{i}</text>')
    for cell in cells:
        x = left + (cell["b_digits"] - 1) * size
        y = top + (cell["a_digits"] - 1) * size
        if cell["accuracy_pct"] is None:
            parts.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="#dddddd" stroke="white"/>')
            continue
        value = cell["accuracy_pct"] / 100
        ink = "white" if value < 0.2 or value > 0.8 else "black"
        parts.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="{color(value)}" stroke="white"/>')
        parts.append(f'<text x="{x + size / 2}" y="{y + size / 2 + 4}" text-anchor="middle" fill="{ink}">'
                     f'{cell["accuracy_pct"]:.0f}</text>')
    parts.append(f'<text x="{left}" y="{height - 18}">Cell value: numeric accuracy, %. '
                 f'Orange 0%, blue 100%.</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def cmd_compare(_: argparse.Namespace) -> None:
    """Paired 169-case table: ours off vs on, plus upstream Qwen3.8 no-thinking on the same cases."""
    on = {row["case_id"]: row for row in load_graded("on").values()}
    off = load_graded("off")
    upstream_path = RESULTS / "upstream_results_no_thinking.csv"
    if not upstream_path.exists():
        urllib.request.urlretrieve(UPSTREAM_RESULTS, upstream_path)
    upstream = {row["case_id"]: row for row in read_csv(upstream_path)}
    ids = [case_id for case_id in on if case_id in off]
    out: dict[str, Any] = {"paired_cases": len(ids)}
    for name, source in (("off", off), ("on", on)):
        rows = [source[case_id] for case_id in ids]
        out[name] = {
            "numeric_correct": sum(row["numeric_correct"] for row in rows),
            "instruction_compliant": sum(row["instruction_compliant"] for row in rows),
            "canonical_text_correct": sum(row["canonical_text_correct"] for row in rows),
            "median_latency": statistics.median(row["request_elapsed_seconds"] for row in rows) if rows else None,
            "mean_latency": statistics.fmean(row["request_elapsed_seconds"] for row in rows) if rows else None,
            "median_completion_tokens": statistics.median(int(row["completion_tokens"]) for row in rows) if rows else None,
            "total_completion_tokens": sum(int(row["completion_tokens"]) for row in rows),
            "median_reasoning_tokens": statistics.median(int(row["reasoning_tokens"] or 0) for row in rows) if rows else None,
        }
    out["overlap"] = {
        "both": sum(off[i]["numeric_correct"] and on[i]["numeric_correct"] for i in ids),
        "on_only": sum(on[i]["numeric_correct"] and not off[i]["numeric_correct"] for i in ids),
        "off_only": sum(off[i]["numeric_correct"] and not on[i]["numeric_correct"] for i in ids),
        "neither": sum(not off[i]["numeric_correct"] and not on[i]["numeric_correct"] for i in ids),
    }
    out["on_failures"] = [
        {"case_id": i, "a": on[i]["a"], "b": on[i]["b"], "expected": on[i]["correct_answer"],
         "answer": on[i]["raw_response"], "parsed": on[i]["parsed_answer"],
         "finish_reason": on[i]["finish_reason"], "parse_error": on[i]["parse_error"]}
        for i in ids if not on[i]["numeric_correct"]
    ]
    full_ids = [i for i in off if i in upstream]
    out["vs_upstream_no_thinking_full"] = {
        "cases": len(full_ids),
        "ours_correct": sum(off[i]["numeric_correct"] for i in full_ids),
        "upstream_correct": sum(upstream[i]["numeric_correct"] == "True" for i in full_ids),
    }
    write_json(RESULTS / "comparison.json", out)
    print(json.dumps(out, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test").set_defaults(func=cmd_self_test)
    for name, func in (("prepare", cmd_prepare), ("smoke", cmd_smoke),
                       ("run", cmd_run), ("summarize", cmd_summarize)):
        command = sub.add_parser(name)
        command.add_argument("--config", choices=sorted(CONFIGS), required=True)
        command.set_defaults(func=func)
        if name == "run":
            command.add_argument("--limit", type=int, default=0)
            command.add_argument("--progress-every", type=int, default=50)
    sub.add_parser("compare").set_defaults(func=cmd_compare)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
