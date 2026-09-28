#!/usr/bin/env python3
"""Paired AR versus diffusion dependency-density benchmark.

The offline ``selftest`` needs only the Python standard library. The ``run``
mode is intended for a persistent Colab A100 session after Cells 2 and 3 have
defined AR_MODEL_PATH, DIFF_MODEL_PATH, and RUNNER_LOCAL_PATH.
"""

from __future__ import annotations

import argparse
import codecs
import hashlib
import importlib.metadata
import math
import json
import os
import random
import re
import selectors
import signal
import uuid
import statistics
import subprocess
import sys
import time
import threading
import tempfile
from datetime import datetime, timezone
from pathlib import Path


TARGET_OUTPUT_SIZES = (256, 1024, 2048)
DEPENDENCY_DENSITIES = ("direct", "mixed", "chained")
BASE_SEED = 20260904
DEFAULT_CASES_PER_CELL = 20
PILOT_CASES_PER_CELL = 1
RESULT_FIELDS = {
    "run_id",
    "case_id",
    "workflow",
    "condition",
    "model",
    "model_artifact",
    "hardware",
    "seed",
    "prompt_hash",
    "case_hash",
    "execution_order",
    "valid",
    "canonical",
    "task_score",
    "prompt_tokens",
    "output_tokens",
    "load_seconds",
    "warm_wall_seconds",
    "internal_compute_seconds",
    "status",
    "raw_output",
}
ANSI_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
TELEMETRY_TOTAL_RE = re.compile(r"total time:\s*([0-9.]+)ms", re.IGNORECASE)
TELEMETRY_TOKEN_RE = re.compile(r"\(([0-9]+) tok in", re.IGNORECASE)


def compact_json(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def stable_hash(value):
    if not isinstance(value, str):
        value = compact_json(value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def target_item_count(target_output_size):
    # A one-character JSON string plus punctuation is about three model tokens
    # for these Gemma tokenizers. Actual prompt/output counts are always logged.
    return max(8, (int(target_output_size) - 8) // 3)


def solve_records(records):
    values = []
    previous_bit = None
    for index, record in enumerate(records):
        mode = record[0]
        bit = int(record[1])
        if mode == "D":
            value = bit
        elif mode == "C" and previous_bit is not None:
            value = previous_bit ^ bit
        else:
            raise ValueError(f"invalid record at {index}: {record!r}")
        values.append("A" if value == 0 else "B")
        previous_bit = value
    return {"values": values}


def make_case(target_output_size, dependency_density, case_index, base_seed=BASE_SEED, item_count=None):
    if dependency_density not in DEPENDENCY_DENSITIES:
        raise ValueError(f"unknown dependency density: {dependency_density}")
    seed = (
        int(base_seed)
        + int(target_output_size) * 1009
        + DEPENDENCY_DENSITIES.index(dependency_density) * 100_003
        + int(case_index) * 9_973
    )
    rng = random.Random(seed)
    item_count = item_count or target_item_count(target_output_size)
    records = []
    for index in range(item_count):
        bit = rng.randrange(2)
        if dependency_density == "direct":
            mode = "D"
        elif dependency_density == "chained":
            mode = "D" if index == 0 else "C"
        else:
            # Exactly half of positions after the required direct first item
            # are dependent, with the locations shuffled per case.
            mode = "D"
        records.append(f"{mode}{bit}")

    if dependency_density == "mixed" and item_count > 1:
        candidates = list(range(1, item_count))
        rng.shuffle(candidates)
        for index in candidates[: len(candidates) // 2]:
            records[index] = "C" + records[index][1]

    expected = solve_records(records)
    case_id = f"dd-{target_output_size}-{dependency_density}-{case_index:03d}"
    prompt = (
        "Return exactly one compact JSON object and no other text. "
        "The object must have the form {\"values\":[\"A\",\"B\"]}. "
        "Produce one output value for every input record, preserving order. "
        "D0 means output A. D1 means output B. C0 means output the same value "
        "as the immediately previous output. C1 means output the opposite value "
        "from the immediately previous output. The first record is always D. "
        "Do not include reasoning, Markdown, or additional keys. "
        f"Records:{compact_json(records)}"
    )
    public_case = {
        "case_id": case_id,
        "target_output_size": int(target_output_size),
        "dependency_density": dependency_density,
        "case_index": int(case_index),
        "seed": seed,
        "records": records,
        "expected": expected,
        "prompt": prompt,
    }
    public_case["case_hash"] = stable_hash(
        {key: value for key, value in public_case.items() if key != "case_hash"}
    )
    return public_case


def build_matrix(cases_per_cell, base_seed=BASE_SEED, item_counts=None):
    return [
        make_case(size, density, case_index, base_seed, (item_counts or {}).get(size))
        for size in TARGET_OUTPUT_SIZES
        for density in DEPENDENCY_DENSITIES
        for case_index in range(int(cases_per_cell))
    ]


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class TokenizerService:
    """Persistent pinned-runtime tokenizer: UTF-8 hex lines in, counts out."""

    def __init__(self, command, model_path, timeout=180):
        self.timeout = timeout
        self.stderr = tempfile.TemporaryFile()
        self.selector = selectors.DefaultSelector()
        self.process = None
        self.pending = b""
        try:
            self.process = subprocess.Popen(
                [command, model_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self.stderr, bufsize=0)
            self.selector.register(self.process.stdout, selectors.EVENT_READ)
        except Exception:
            self.close()
            raise

    def count(self, text):
        return self._request(text, b"")

    def count_prompt(self, text):
        return self._request(text, b"p:")

    def _request(self, text, prefix):
        self.process.stdin.write(prefix + text.encode("utf-8").hex().encode("ascii") + b"\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + self.timeout
        while b"\n" not in self.pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("tokenizer helper response timed out")
            if not self.selector.select(timeout=min(remaining, 1.0)):
                continue
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                self.stderr.seek(0)
                diagnostic = self.stderr.read().decode("utf-8", errors="replace")[-4000:]
                raise RuntimeError(f"tokenizer helper closed stdout: {diagnostic}")
            self.pending += chunk
        line, self.pending = self.pending.split(b"\n", 1)
        if not line.strip().isdigit():
            raise ValueError(f"invalid tokenizer count: {line!r}")
        return int(line)

    def close(self):
        if self.process is not None:
            if self.process.stdin:
                self.process.stdin.close()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            if self.process.stdout:
                self.process.stdout.close()
        self.selector.close()
        self.stderr.close()


def calibrate_item_counts(token_counters, sizes=TARGET_OUTPUT_SIZES):
    """Choose a shared output width nearest each target using both tokenizers."""
    counts = {}
    for size in sizes:
        def distance(count):
            text = compact_json({"values": ["A" if i % 2 == 0 else "B" for i in range(count)]})
            return max(abs(counter(text) - size) for counter in token_counters.values())
        counts[size] = min(range(8, size + 1), key=distance)
    return counts


def percentile(values, percent):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def parse_canonical_output(text):
    if not isinstance(text, str):
        return None
    stripped = text.strip()
    try:
        value = json.loads(stripped, object_pairs_hook=unique_object)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(value, dict) or set(value) != {"values"}:
        return None
    values = value.get("values")
    if not isinstance(values, list) or not all(item in ("A", "B") for item in values):
        return None
    # Whitespace is accepted, prose, fences, and additional JSON are not.
    return value


def evaluate_output(case, response_text):
    parsed = parse_canonical_output(response_text)
    canonical = parsed is not None
    valid = canonical and parsed == case["expected"]
    if not canonical:
        status = "noncanonical_output"
    elif len(parsed["values"]) != len(case["expected"]["values"]):
        status = "wrong_length"
    elif not valid:
        mismatch = next(
            (
                index
                for index, (actual, expected) in enumerate(
                    zip(parsed["values"], case["expected"]["values"])
                )
                if actual != expected
            ),
            None,
        )
        status = f"wrong_value_at_{mismatch}" if mismatch is not None else "wrong_values"
    else:
        status = "valid"
    return {
        "valid": bool(valid),
        "canonical": canonical,
        "task_score": 1.0 if valid else 0.0,
        "status": status,
        "parsed": parsed,
    }


def planned_order(case):
    # Stable pseudo-randomization, exactly balanced when a cell has an even
    # number of cases and differing by at most one for an odd pilot.
    condition_seed = (
        BASE_SEED
        + case["target_output_size"] * 1009
        + DEPENDENCY_DENSITIES.index(case["dependency_density"]) * 100_003
    )
    chooser = random.Random(condition_seed ^ 0xA100)
    first = "ar" if chooser.randrange(2) == 0 else "diffusion"
    if case["case_index"] % 2:
        first = "diffusion" if first == "ar" else "ar"
    second = "diffusion" if first == "ar" else "ar"
    return (first, second)


def execution_plan(cases, strategy, base_seed, phase_order_offset=0):
    """Freeze actual execution order while preserving each case's paired order."""
    plan = []
    if strategy != "phased":
        for case in cases:
            for order, model in enumerate(planned_order(case), 1):
                plan.append({"case": case, "model": model, "execution_order": order, "phase_id": None})
        return plan
    for size in TARGET_OUTPUT_SIZES:
        selected = [case for case in cases if case["target_output_size"] == size]
        rng = random.Random(base_seed + size)
        outer = ("ar", "diffusion")[(rng.randrange(2) + phase_order_offset) % 2]
        inner = "diffusion" if outer == "ar" else "ar"
        phases = (
            (outer, [case for case in selected if planned_order(case)[0] == outer]),
            (inner, selected[:]),
            (outer, [case for case in selected if planned_order(case)[0] != outer]),
        )
        for phase_index, (model, phase_cases) in enumerate(phases, 1):
            rng.shuffle(phase_cases)
            for case in phase_cases:
                plan.append({"case": case, "model": model,
                             "execution_order": planned_order(case).index(model) + 1,
                             "phase_id": f"{size}:{phase_index}:{model}"})
    return plan


def artifact_identity(path):
    candidate = Path(path)
    if not candidate.is_file():
        return str(path)
    digest = hashlib.sha256()
    with candidate.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(candidate), "size_bytes": candidate.stat().st_size, "sha256": digest.hexdigest()}


def hardware_identity():
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return completed.stdout.strip()
    except Exception as error:
        return f"unavailable:{type(error).__name__}"


def result_row(run_id, case, model_name, model_artifact, hardware, execution_order, raw_output, timing, prompt_tokens=None, output_tokens=None, load_seconds=0.0, internal_compute_seconds=None, scoring_output=None):
    evaluation = evaluate_output(case, raw_output if scoring_output is None else scoring_output)
    return {
        "run_id": run_id,
        "case_id": case["case_id"],
        "workflow": "dependency_density",
        "condition": {
            "target_output_size": case["target_output_size"],
            "dependency_density": case["dependency_density"],
            "item_count": len(case["records"]),
        },
        "model": model_name,
        "model_artifact": model_artifact,
        "hardware": hardware,
        "seed": case["seed"],
        "prompt_hash": stable_hash(case["prompt"]),
        "case_hash": case["case_hash"],
        "execution_order": int(execution_order),
        "valid": evaluation["valid"],
        "canonical": evaluation["canonical"],
        "task_score": evaluation["task_score"],
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "load_seconds": float(load_seconds),
        "warm_wall_seconds": float(timing),
        "internal_compute_seconds": internal_compute_seconds,
        "status": evaluation["status"],
        "raw_output": raw_output,
    }


def summarize(rows):
    summaries = []
    for size in TARGET_OUTPUT_SIZES:
        for density in DEPENDENCY_DENSITIES:
            for model in ("ar", "diffusion"):
                selected = [
                    row for row in rows
                    if row["model"] == model
                    and row["condition"]["target_output_size"] == size
                    and row["condition"]["dependency_density"] == density
                ]
                measured = [row for row in selected if row["warm_wall_seconds"] is not None]
                valid_times = [row["warm_wall_seconds"] for row in selected if row["valid"]]
                summaries.append(
                    {
                        "target_output_size": size,
                        "dependency_density": density,
                        "model": model,
                        "attempts": len(selected),
                        "valid": sum(bool(row["valid"]) for row in selected),
                        "valid_rate": (
                            sum(bool(row["valid"]) for row in selected) / len(selected)
                            if selected else 0.0
                        ),
                        "canonical_rate": (
                            sum(bool(row["canonical"]) for row in selected) / len(selected)
                            if selected else 0.0
                        ),
                        "median_wall_seconds_all": (
                            statistics.median(row["warm_wall_seconds"] for row in measured)
                            if measured else None
                        ),
                        "p90_wall_seconds_all": percentile([row["warm_wall_seconds"] for row in measured], 90),
                        "p90_wall_seconds_valid": percentile(valid_times, 90),
                        "median_wall_seconds_valid": (
                            statistics.median(valid_times) if valid_times else None
                        ),
                    }
                )
    return summaries


def paired_summary(rows):
    pairs = {}
    for row in rows:
        pairs.setdefault(row["case_id"], {})[row["model"]] = row
    result = []
    for size in TARGET_OUTPUT_SIZES:
        for density in DEPENDENCY_DENSITIES:
            outcomes = {"ar_only": 0, "diffusion_only": 0, "both": 0, "neither": 0}
            ratios = []
            for pair in pairs.values():
                if set(pair) != {"ar", "diffusion"}:
                    continue
                ar, diff = pair["ar"], pair["diffusion"]
                if (ar["condition"]["target_output_size"], ar["condition"]["dependency_density"]) != (size, density):
                    continue
                key = "both" if ar["valid"] and diff["valid"] else "ar_only" if ar["valid"] else "diffusion_only" if diff["valid"] else "neither"
                outcomes[key] += 1
                if key == "both" and ar["warm_wall_seconds"] > 0:
                    ratios.append(diff["warm_wall_seconds"] / ar["warm_wall_seconds"])
            result.append({"target_output_size": size, "dependency_density": density, **outcomes,
                           "median_paired_valid_latency_ratio": statistics.median(ratios) if ratios else None})
    return result


def selftest_report():
    cases = build_matrix(2)
    repeated = build_matrix(2)
    deterministic = compact_json(cases) == compact_json(repeated)
    cell_counts = {}
    for case in cases:
        key = (case["target_output_size"], case["dependency_density"])
        cell_counts[key] = cell_counts.get(key, 0) + 1

    sample = cases[0]
    expected_text = compact_json(sample["expected"])
    exact_scoring = evaluate_output(sample, expected_text)["valid"]
    canonical_enforced = all(
        not evaluate_output(sample, candidate)["canonical"]
        for candidate in (
            "```json\n" + expected_text + "\n```",
            "answer: " + expected_text,
            '{"values":[],"values":' + compact_json(sample["expected"]["values"]) + "}",
            expected_text + " trailing",
            compact_json({"values": sample["expected"]["values"], "extra": True}),
        )
    )
    orders_balanced = True
    for key in cell_counts:
        selected = [
            case for case in cases
            if (case["target_output_size"], case["dependency_density"]) == key
        ]
        firsts = [planned_order(case)[0] for case in selected]
        if abs(firsts.count("ar") - firsts.count("diffusion")) > 1:
            orders_balanced = False

    fake_timing = 0.01
    valid_row = result_row(
        "selftest", sample, "ar", "artifact", "hardware", 1,
        expected_text, fake_timing, prompt_tokens=10, output_tokens=10,
    )
    invalid_row = result_row(
        "selftest", sample, "diffusion", "artifact", "hardware", 2,
        "not json", fake_timing, prompt_tokens=10, output_tokens=2,
    )
    with tempfile.TemporaryDirectory() as directory:
        helper = Path(directory) / "tokenizer"
        helper.write_text("#!" + sys.executable + "\nimport sys\nfor line in sys.stdin:\n prompt = line.startswith('p:')\n print(len(bytes.fromhex(line[2:] if prompt else line).decode('utf-8')) + (2 if prompt else 0), flush=True)\n")
        helper.chmod(0o700)
        tokenizer = TokenizerService(str(helper), "unused")
        try:
            assert tokenizer.count("first\nsecond") == 12
            assert tokenizer.count("中") == 1
            assert tokenizer.count("") == 0
            assert tokenizer.count_prompt("中") == 3
        finally:
            tokenizer.close()
        assert tokenizer.process.poll() is not None
    calibration = calibrate_item_counts({"test": lambda text: len(text)}, (256, 1024, 2048))
    assert calibration == {256: 61, 1024: 253, 2048: 509}, calibration
    assert percentile([1, 2, 3, 4, 5], 90) == 4.6
    transcript = '\rdiffusion step: 1/48 [==  ] 2%\n' + expected_text + '\ntotal time: 123.4ms, time per step: 1ms\nthroughput: 1.0 tok/s (256 tok in 123.4ms)\n\n> '
    assert diffusion_response_text(transcript) == expected_text
    observed = '0.15.602.834 W init: embeddings required but some input tokens were not marked as outputs -> overriding\n0.16.167.310 I \rdiffusion step: 0/48 [   ] 0%0.16.305.651 I \rdiffusion step: 1/48 [=  ] 2%\n' + expected_text + '\ntotal time: 1565.95ms, time per step: 173.99ms (9 steps over 1 blocks, entropy-bound)\nthroughput: 163.5 tok/s (256 tok in 1565.95ms), in-step parallel 1471 tok/s (256-tok canvas x 9.0 steps/block)\n\n> '
    assert diffusion_response_text(observed) == expected_text
    thought_output = "<|channel>thought\nreasoning<channel|>" + expected_text
    assert diffusion_response_text(observed.replace(expected_text, thought_output)) == thought_output
    assert not evaluate_output(sample, thought_output)["canonical"]
    final_content, reasoning = split_native_response(thought_output)
    assert final_content == expected_text and reasoning == "reasoning"
    assert evaluate_output(sample, final_content)["valid"]
    for malformed in ("<|channel>thought\nreasoning" + expected_text,
                      thought_output + "<channel|>",
                      thought_output.replace("reasoning", "<|channel>thought\nreasoning")):
        assert split_native_response(malformed) == (malformed, None)
        assert not evaluate_output(sample, split_native_response(malformed)[0])["canonical"]
    assert not evaluate_output(sample, split_native_response(thought_output + " prose")[0])["canonical"]
    channel_row = result_row("selftest", sample, "diffusion", "artifact", "hardware", 2,
                             thought_output, 1.0, scoring_output=final_content)
    assert channel_row["valid"] and channel_row["raw_output"] == thought_output
    assert diffusion_response_text('explanation\n' + transcript).startswith('explanation')
    phases = execution_plan(cases, "phased", BASE_SEED)
    assert len(phases) == len(cases) * 2
    assert phases == execution_plan(cases, "phased", BASE_SEED)
    reversed_phases = execution_plan(cases, "phased", BASE_SEED, 1)
    for size in TARGET_OUTPUT_SIZES:
        first = next(item["model"] for item in phases if item["case"]["target_output_size"] == size)
        reversed_first = next(item["model"] for item in reversed_phases if item["case"]["target_output_size"] == size)
        assert first != reversed_first
    assert len({(item["case"]["case_id"], item["model"]) for item in phases}) == len(phases)
    for case in cases:
        observed = [item["model"] for item in phases if item["case"]["case_id"] == case["case_id"]]
        assert tuple(observed) == planned_order(case)
    for size in TARGET_OUTPUT_SIZES:
        selected = [item for item in phases if item["case"]["target_output_size"] == size]
        assert len({item["phase_id"] for item in selected}) <= 3
        assert 1 + sum(a["model"] != b["model"] for a, b in zip(selected, selected[1:])) <= 3
    paired = paired_summary([valid_row, invalid_row])[0]
    assert paired["ar_only"] == 1 and paired["median_paired_valid_latency_ratio"] is None
    failed_row = dict(invalid_row, warm_wall_seconds=None, status="runtime_error")
    assert summarize([failed_row])[1]["median_wall_seconds_all"] is None
    checks = {
        "balanced_conditions": len(cell_counts) == 9 and len(set(cell_counts.values())) == 1,
        "canonical_output_enforced": canonical_enforced,
        "deterministic_cases": deterministic,
        "exact_scoring": exact_scoring,
        "invalid_outputs_retained": not invalid_row["valid"] and invalid_row["raw_output"] == "not json",
        "order_is_seeded_and_balanced": orders_balanced,
        "paired_contract_equal": all(
            stable_hash(case["prompt"]) == stable_hash(case["prompt"])
            and case["expected"] == case["expected"]
            for case in cases
        ),
        "result_schema_complete": RESULT_FIELDS <= set(valid_row) and RESULT_FIELDS <= set(invalid_row),
    }
    matrix = [
        {
            "output_size": size,
            "dependency_density": density,
            "case_count": cell_counts[(size, density)],
        }
        for size in TARGET_OUTPUT_SIZES
        for density in DEPENDENCY_DENSITIES
    ]
    return {"status": "ok" if all(checks.values()) else "failed", "checks": checks, "matrix": matrix}


def split_native_response(text):
    """Decode only one well-formed native thought/final channel boundary."""
    prefix = "<|channel>thought\n"
    if (text.startswith(prefix) and text.count("<|channel>") == 1
            and text.count("<channel|>") == 1):
        reasoning, final = text[len(prefix):].split("<channel|>", 1)
        return final, reasoning
    return text, None


def diffusion_response_text(transcript):
    """Remove only observed runner transport around the complete model reply."""
    text = ANSI_PATTERN.sub("", transcript)
    text = re.sub(r"\n> $", "", text)
    text = re.sub(
        r"\ntotal time: [0-9.]+ms, time per step: [^\n]*\n"
        r"(?:throughput: [0-9.]+ tok/s [^\n]*\n)?\n*$", "", text)
    timestamp = r"(?:\d+\.\d+\.\d+\.\d+ [IW] )?"
    prefix = re.compile(
        r"\A\n*" + timestamp + r"(?:"
        r"\rdiffusion step: \d+/\d+ \[[^\]\n]*\] \d+%"
        r"|init: embeddings required but some input tokens were not marked as outputs -> overriding\n)")
    while True:
        matched = prefix.match(text)
        if matched is None:
            break
        text = text[matched.end():]
    return text.strip()


class GenerationCancelled(RuntimeError):
    """A request was cancelled; cleanup has acknowledged idle or process exit."""


class DiffusionSession:
    """One owner for a native process, pipe draining, and acknowledged recovery."""

    def __init__(self, runner_path, model_path, max_tokens, seed, gpu_layers=99,
                 timeout=300, context_size=8192, *, native_protocol=False,
                 trace_dir=None, trace_mode="summary", cancellation_grace=10):
        self.runner_path, self.model_path = runner_path, model_path
        self.max_tokens, self.seed = int(max_tokens), int(seed)
        self.gpu_layers, self.timeout = int(gpu_layers), float(timeout)
        self.context_size = int(context_size)
        self.native_protocol, self.trace_mode = native_protocol, trace_mode
        self.trace_dir = Path(trace_dir or tempfile.mkdtemp(prefix="diffusion-events-"))
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.cancellation_grace = float(cancellation_grace)
        self.last_transcript, self.last_result = "", {}
        self.process = self.selector = None
        self.load_seconds, self.turn_count = 0.0, 0
        self.state = "closed"
        self.cancel_event = threading.Event()
        self._request_lock = threading.Lock()
        self.event_path = None
        self._event_offset = 0
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")

    @property
    def ready(self):
        return self.state == "ready" and self.process is not None and self.process.poll() is None

    @property
    def ubatch_size(self):
        # DIFFUSION_UBATCH decouples the batch from the context; only safe with the incremental-prefill runner.
        return int(os.environ.get("DIFFUSION_UBATCH", self.context_size))

    def command(self):
        return [self.runner_path, "-m", self.model_path, "-ngl", str(self.gpu_layers),
                "-cnv", "-c", str(self.context_size), "-b", str(self.ubatch_size),
                "-ub", str(self.ubatch_size), "-n", str(self.max_tokens),
                "--seed", str(self.seed), "--diffusion-kv-cache", "on",
                "--diffusion-eb-max-steps", "48"]

    def events(self):
        if not self.event_path or not self.event_path.exists():
            return []
        rows = []
        with self.event_path.open() as f:
            f.seek(self._event_offset)
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    # A concurrent writer may not have completed the last line.
                    break
        return rows

    def start(self, *, preserve_cancel=False):
        if self.ready:
            return
        if self.state in ("generating", "cancelling"):
            raise RuntimeError("native process is not idle")
        self.close()
        if not preserve_cancel:
            self.cancel_event.clear()
        self.state = "starting"
        self.turn_count = 0
        self.process_generation = uuid.uuid4().hex
        self.event_path = self.trace_dir / (self.process_generation + ".jsonl")
        self._event_offset = 0
        env = os.environ.copy()
        if self.native_protocol:
            env.update(DIFFUSION_EVENT_PATH=str(self.event_path),
                       DIFFUSION_TRACE_MODE=self.trace_mode,
                       DIFFUSION_REPETITION_POLICY="off")
        started = time.perf_counter()
        try:
            self.process = subprocess.Popen(self.command(), stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, env=env)
            os.set_blocking(self.process.stdout.fileno(), False)
            self.selector = selectors.DefaultSelector()
            self.selector.register(self.process.stdout, selectors.EVENT_READ)
            self._read_until_prompt(False)
            if self.native_protocol and not any(e.get("event") == "ready" and e.get("version") == 2 for e in self.events()):
                raise RuntimeError("runner does not acknowledge native protocol v2")
            self.load_seconds = time.perf_counter() - started
            self.state = "ready"
        except BaseException:
            self._terminate()
            self.state = "failed"
            raise

    def _write(self, text):
        self.process.stdin.write((text + "\n").encode("utf-8"))
        self.process.stdin.flush()

    def _pump(self, wait=0.05):
        chunks = []
        if self.selector is None:
            return
        for key, _ in self.selector.select(wait):
            while True:
                try:
                    chunk = os.read(key.fileobj.fileno(), 65536)
                except BlockingIOError:
                    break
                if not chunk:
                    self.selector.unregister(key.fileobj)
                    break
                chunks.append(chunk)
        if chunks:
            self.last_transcript += self._decoder.decode(b"".join(chunks), final=False)

    def _read_until_prompt(self, require_generation, *, append=False, limit=None, interruptible=True):
        if not append:
            self.last_transcript = ""
            self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        deadline = time.monotonic() + (self.timeout if limit is None else limit)
        while True:
            self._pump()
            # Drain first, including when the child exited before we resumed.
            code = self.process.poll()
            if code is not None:
                self._pump(0)
                raise RuntimeError(f"diffusion runner exited with {code}")
            clean = ANSI_PATTERN.sub("", self.last_transcript)
            if clean.endswith("\n> "):
                self.last_transcript = clean
                return clean, ""
            if interruptible and self.cancel_event.is_set():
                raise GenerationCancelled("diffusion request cancelled")
            if time.monotonic() >= deadline:
                raise TimeoutError("diffusion response timed out")

    def _terminate(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
            self._pump(0)

    def cancel(self):
        if self.state not in ("generating", "starting", "cancelling"):
            return False
        self.cancel_event.set()
        if self.state == "generating":
            self.state = "cancelling"
        return True

    def _acknowledge_interruption(self):
        if self.native_protocol and self.process is not None and self.process.poll() is None:
            try:
                self.state = "cancelling"
                self.process.send_signal(signal.SIGUSR1)
                self._read_until_prompt(True, append=True, limit=self.cancellation_grace, interruptible=False)
                if any(e.get("event") == "stop" and e.get("reason") == "cancelled" for e in self.events()):
                    self.state = "ready"
                    return "native_cancelled"
            except (RuntimeError, TimeoutError, OSError):
                pass
        self._terminate()
        self.state = "failed"
        return "process_exited"

    def generate(self, prompt, request_id=None, *, cancel_event=None):
        if not self._request_lock.acquire(blocking=False):
            raise RuntimeError("a diffusion request is already active")
        request_id = request_id or uuid.uuid4().hex
        started = time.perf_counter()
        self.last_result = {"request_id": request_id, "request_state": "starting"}
        self.last_transcript = ""
        self._event_offset = self.event_path.stat().st_size if self.event_path and self.event_path.exists() else 0
        try:
            self.cancel_event = cancel_event if cancel_event is not None else threading.Event()
            if self.cancel_event.is_set():
                raise GenerationCancelled("diffusion request cancelled before start")
            self.start(preserve_cancel=True)
            if self.turn_count:
                self._write("/clear")
                self._read_until_prompt(False)
            self._event_offset = self.event_path.stat().st_size if self.event_path.exists() else 0
            self.state = "generating"
            self.last_result.update(request_state="generating", process_generation=self.process_generation,
                                    native_turn=self.turn_count + 1, trace_path=str(self.event_path))
            started = time.perf_counter()
            self._write(" ".join(prompt.split()))
            stdout, stderr = self._read_until_prompt(True)
            wall = time.perf_counter() - started
            self.turn_count += 1
            events = self.events()
            stops = [e for e in events if e.get("event") == "stop"]
            if self.native_protocol and len(stops) != 1:
                raise RuntimeError("missing or ambiguous native stop event")
            self.state = "ready"
            self.last_result.update(request_state="completed", elapsed_seconds=wall,
                                    native_events=events, native_stop_reason=stops[0]["reason"] if stops else None,
                                    exit_code=None, error=None, trace_mode=self.trace_mode)
            combined = stdout + "\n" + stderr
            compute = sum(float(x) for x in TELEMETRY_TOTAL_RE.findall(combined)) / 1000
            tokens = TELEMETRY_TOKEN_RE.findall(combined)
            return diffusion_response_text(stdout), wall, compute or None, int(tokens[-1]) if tokens else None
        except BaseException as exc:
            interrupted = isinstance(exc, (TimeoutError, GenerationCancelled))
            ack = self._acknowledge_interruption() if interrupted else None
            if not interrupted:
                self._terminate()
                self.state = "failed"
            self.last_result.update(request_state="cancelled" if isinstance(exc, GenerationCancelled) else "timed_out" if isinstance(exc, TimeoutError) else "failed",
                elapsed_seconds=time.perf_counter() - started, error={"type": type(exc).__name__, "message": str(exc)},
                exit_code=self.process.poll() if self.process else None, native_events=self.events(),
                cancellation_ack=ack, runtime_ready=self.ready)
            if ack == "native_cancelled":
                self.turn_count += 1
            raise
        finally:
            self.last_result["runner_transcript"] = self.last_transcript
            self._request_lock.release()

    def close(self):
        self._terminate()
        if self.selector is not None:
            self.selector.close()
            self.selector = None
        if self.process is not None:
            for stream in (self.process.stdin, self.process.stdout):
                if stream:
                    stream.close()
        self.process = None
        self.state = "closed"


class GPUMemorySampler:
    """Sample device-wide used memory; this is not a process allocation peak."""

    def __init__(self):
        self.stop_event = threading.Event()
        self.samples = []
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self.stop_event.is_set():
            try:
                measured = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5, check=True)
                self.samples.append((time.perf_counter(), max(float(value) for value in measured.stdout.splitlines())))
            except Exception:
                pass
            self.stop_event.wait(0.5)

    def peak_since(self, started):
        values = [value for timestamp, value in self.samples if timestamp >= started]
        return max(values) if values else None

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=6)


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(compact_json(row) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def run_benchmark(cases_per_cell, output_dir, base_seed=BASE_SEED):
    from llama_cpp import Llama

    def setting(name, default=None):
        return globals().get(name) or os.environ.get(name, default)

    paths = {name: setting(key) for name, key in (
        ("ar", "AR_MODEL_PATH"), ("diffusion", "DIFF_MODEL_PATH"), ("runner", "RUNNER_LOCAL_PATH"))}
    for name, path in paths.items():
        if not path or not Path(path).is_file():
            raise RuntimeError(f"missing staged runtime path: {name}")
    if cases_per_cell < 1:
        raise ValueError("cases_per_cell must be positive")
    strategy = setting("DEPENDENCY_BENCH_MEMORY_STRATEGY", "sequential")
    if strategy not in ("sequential", "coexist", "phased"):
        raise ValueError("memory strategy must be sequential, coexist, or phased")
    phase_order_offset = int(setting("DEPENDENCY_BENCH_PHASE_ORDER_OFFSET", "0"))
    if phase_order_offset not in (0, 1):
        raise ValueError("phase order offset must be 0 or 1")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("dependency-density-%Y%m%dT%H%M%S%fZ")
    result_path = output_dir / f"{run_id}.jsonl"
    summary_path = output_dir / f"{run_id}-summary.json"
    manifest_path = output_dir / f"{run_id}-cases.json"
    artifacts = {name: artifact_identity(path) for name, path in paths.items()}
    hardware = hardware_identity()
    runtime = {"llama_cpp_python": importlib.metadata.version("llama-cpp-python"),
               "runner_commit": setting("DIFFUSION_RUNNER_COMMIT"), "memory_strategy": strategy,
               "phase_order_offset": phase_order_offset, "base_seed": base_seed,
               "response_contract": "strict final channel; full generation timed/budgeted",
               "harness_sha256": stable_hash(Path(__file__).read_text())}
    tokenizers = {}
    counters = {}
    try:
        tokenizer_command = setting("DEPENDENCY_BENCH_TOKENIZER_COMMAND")
        for name in ("ar", "diffusion"):
            if name == "diffusion" and tokenizer_command:
                runtime["diffusion_tokenizer_helper"] = artifact_identity(tokenizer_command)
                runtime["diffusion_tokenizer_source_commit"] = runtime["runner_commit"]
                tokenizers[name] = TokenizerService(tokenizer_command, paths[name])
                counters[name] = tokenizers[name].count
            else:
                tokenizers[name] = Llama(model_path=paths[name], vocab_only=True, verbose=False)
                counters[name] = lambda text, tokenizer=tokenizers[name]: len(tokenizer.tokenize(text.encode(), add_bos=False, special=False))
        counts = calibrate_item_counts(counters)
        cases = build_matrix(cases_per_cell, base_seed, counts)
        for case in cases:
            case["expected_output_tokens"] = {name: count(compact_json(case["expected"])) for name, count in counters.items()}
            case["semantic_prompt_tokens"] = {name: count(case["prompt"]) for name, count in counters.items()}
            case["diffusion_prompt_tokens"] = tokenizers["diffusion"].count_prompt(case["prompt"]) if tokenizer_command else None
            # Round to complete 256-token canvases, shared by both runtimes.
            case["max_output_tokens"] = 256 * math.ceil((max(max(case["expected_output_tokens"].values()) + 256, 9216)) / 256)
            # Reserve 512 tokens for the chat template; the semantic count is
            # explicitly not reported as the exact runner prompt count.
            prompt_bound = max(case["semantic_prompt_tokens"]["ar"] + 512,
                               case["diffusion_prompt_tokens"] or case["semantic_prompt_tokens"]["diffusion"] + 512)
            # The pinned runner enforces an additional 2048-token context floor.
            needed = max(prompt_bound, 2048) + case["max_output_tokens"]
            case["context_size"] = 512 * math.ceil(needed / 512)
            if case["context_size"] > int(setting("DEPENDENCY_BENCH_MAX_CONTEXT", "16384")):
                raise ValueError(f"context gate failed for {case['case_id']}: {needed}")
            case["case_hash"] = stable_hash({key: value for key, value in case.items() if key != "case_hash"})
        # Keep a fixed runtime allocation and output allowance within each size.
        for size in TARGET_OUTPUT_SIZES:
            selected = [case for case in cases if case["target_output_size"] == size]
            context = max(case["context_size"] for case in selected)
            allowance = max(case["max_output_tokens"] for case in selected)
            for case in selected:
                case.update(context_size=context, max_output_tokens=allowance)
                case["case_hash"] = stable_hash({key: value for key, value in case.items() if key != "case_hash"})
        manifest_path.write_text(json.dumps(cases, indent=2), encoding="utf-8")
        manifest_hash = stable_hash(manifest_path.read_text())
        plan = execution_plan(cases, strategy, base_seed, phase_order_offset)
        plan_path = output_dir / f"{run_id}-execution-plan.json"
        plan_path.write_text(json.dumps([
            {"global_execution_ordinal": index, "case_id": item["case"]["case_id"],
             "model": item["model"], "execution_order": item["execution_order"], "phase_id": item["phase_id"]}
            for index, item in enumerate(plan, 1)], indent=2), encoding="utf-8")
        runtime["execution_plan_sha256"] = stable_hash(plan_path.read_text())
        print(f"Run: {run_id}, {len(cases)} paired cases, hardware: {hardware}", flush=True)
        print(f"Calibrated widths: {counts}; strategy: {strategy}", flush=True)
        rows, loaded = [], {}
        memory_sampler = GPUMemorySampler()
        memory_sampler.thread.start()
        warmup_prompt = 'Return exactly {"values":["A","B"]} and no other text.'

        def close_model(name):
            if name in loaded:
                loaded.pop(name)["model"].close()

        def acquire(name, case):
            if strategy in ("sequential", "phased"):
                for other in list(loaded):
                    if other != name:
                        close_model(other)
            config = (case["max_output_tokens"], case["context_size"])
            if name in loaded and loaded[name]["config"] != config:
                close_model(name)
            if name not in loaded:
                started = time.perf_counter()
                seed = base_seed + case["target_output_size"]
                if name == "ar":
                    model = Llama(model_path=paths[name], n_ctx=config[1], n_batch=512,
                                  n_gpu_layers=99, seed=seed, verbose=False)
                else:
                    model = DiffusionSession(paths["runner"], paths[name], config[0], seed,
                                             timeout=900, context_size=config[1])
                    try:
                        model.start()
                    except Exception:
                        model.close()
                        raise
                entry = {"model": model, "load_seconds": time.perf_counter() - started,
                         "config": config, "seed": seed, "measured_turns": 0}
                loaded[name] = entry
                warm_started = time.perf_counter()
                if name == "ar":
                    model.create_chat_completion(messages=[{"role": "user", "content": warmup_prompt}],
                                                 max_tokens=32, temperature=0.0)
                else:
                    model.generate(warmup_prompt)
                entry["warmup_seconds"] = time.perf_counter() - warm_started
            return loaded[name]

        try:
            for global_ordinal, planned in enumerate(plan, 1):
                case, name = planned["case"], planned["model"]
                execution_order = planned["execution_order"]
                phase_id = planned["phase_id"]
                started = time.perf_counter()
                raw, compute, canvas_tokens, actual_prompt_tokens = "", None, None, None
                error, entry, transcript, generated_tokens, reasoning = None, None, None, None, None
                try:
                    entry = acquire(name, case)
                    model = entry["model"]
                    if name == "ar":
                        model.reset()
                        model.set_seed(case["seed"])
                    started = time.perf_counter()
                    if name == "ar":
                        response = model.create_chat_completion(
                            messages=[{"role": "user", "content": case["prompt"]}],
                            max_tokens=case["max_output_tokens"], temperature=0.0)
                        wall = time.perf_counter() - started
                        raw = response["choices"][0]["message"]["content"] or ""
                        reasoning = response["choices"][0]["message"].get("reasoning_content")
                        actual_prompt_tokens = response.get("usage", {}).get("prompt_tokens")
                        generated_tokens = response.get("usage", {}).get("completion_tokens")
                    else:
                        raw, wall, compute, canvas_tokens = model.generate(case["prompt"])
                        transcript = model.last_transcript
                        actual_prompt_tokens = case["diffusion_prompt_tokens"]
                    entry["measured_turns"] += 1
                except Exception as failure:
                    wall = time.perf_counter() - started
                    error = f"{type(failure).__name__}: {failure}"
                    if entry and name == "diffusion":
                        transcript = entry["model"].last_transcript
                        raw = diffusion_response_text(transcript)
                    close_model(name)
                final_output = raw
                if name == "diffusion":
                    final_output, reasoning = split_native_response(raw)
                row = result_row(run_id, case, name, artifacts[name], hardware, execution_order,
                                 raw, wall, prompt_tokens=actual_prompt_tokens,
                                 output_tokens=counters[name](raw),
                                 load_seconds=entry["load_seconds"] if entry else 0.0,
                                 internal_compute_seconds=compute, scoring_output=final_output)
                row.update({"manifest_sha256": manifest_hash, "runtime": runtime,
                            "phase_id": phase_id, "global_execution_ordinal": global_ordinal,
                            "actual_runtime_seed": case["seed"] if name == "ar" else (entry["seed"] if entry else None),
                            "runtime_measured_turn": entry["measured_turns"] if entry else None,
                            "warmup_seconds": entry.get("warmup_seconds") if entry else None,
                            "semantic_prompt_tokens": case["semantic_prompt_tokens"][name],
                            "prompt_tokens_note": ("runtime usage" if name == "ar" else
                                "pinned native chat template tokenized with special tokens" if actual_prompt_tokens is not None else "unavailable"),
                            "expected_output_tokens": case["expected_output_tokens"][name],
                            "max_output_tokens": case["max_output_tokens"], "context_size": case["context_size"],
                            "canvas_work_tokens": canvas_tokens, "runner_transcript": transcript,
                            "runtime_completion_tokens": generated_tokens,
                            "final_output": final_output, "final_output_tokens": counters[name](final_output),
                            "reasoning_content": reasoning,
                            "native_channel_decoded": name == "diffusion" and reasoning is not None,
                            "output_tokens_method": "retokenized response text without BOS",
                            "canonical_output_units": len(case["expected"]["values"]),
                            "sampled_peak_device_memory_mib": memory_sampler.peak_since(started),
                            "memory_sample_interval_seconds": 0.5,
                            "error": error})
                if error:
                    row.update(valid=False, canonical=False, task_score=0.0, status="runtime_error",
                               warm_wall_seconds=None, failure_elapsed_seconds=wall)
                rows.append(row)
                append_jsonl(result_path, row)
                print(f"[{global_ordinal}/{len(plan)}] {case['case_id']} {name} valid={row['valid']} wall={wall:.2f}s error={error}", flush=True)
                payload = {"run_id": run_id, "hardware": hardware, "runtime": runtime,
                           "artifacts": artifacts, "cases_per_cell": cases_per_cell,
                           "matrix": summarize(rows), "paired": paired_summary(rows),
                           "rows_completed": len(rows), "rows_expected": len(cases) * 2,
                           "result_path": str(result_path), "manifest_path": str(manifest_path),
                           "execution_plan_path": str(plan_path)}
                summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        finally:
            memory_sampler.close()
            for name in list(loaded):
                close_model(name)
        return payload
    finally:
        for tokenizer in tokenizers.values():
            tokenizer.close()


def default_output_dir():
    namespace = globals()
    drive_root = namespace.get("DRIVE_ROOT") or os.environ.get("DRIVE_ROOT")
    if drive_root:
        return str(Path(drive_root) / "benchmark-results" / "dependency-density")
    return "/content/dependency-density-results" if Path("/content").is_dir() else "bench/results/dependency-density"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", nargs="?", choices=("selftest", "pilot", "run"), default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--cases-per-cell", type=int, default=None)
    parser.add_argument("--output-dir", default=None)
    args, _ = parser.parse_known_args(argv)

    mode = args.mode or globals().get("DEPENDENCY_BENCH_MODE") or os.environ.get("DEPENDENCY_BENCH_MODE", "selftest")
    if mode == "selftest":
        report = selftest_report()
        if args.json:
            print(compact_json(report))
        else:
            print(json.dumps(report, indent=2))
        return 0 if report["status"] == "ok" else 1

    cases_per_cell = args.cases_per_cell
    if cases_per_cell is None:
        cases_per_cell = globals().get("DEPENDENCY_BENCH_CASES_PER_CELL")
    if cases_per_cell is None:
        cases_per_cell = PILOT_CASES_PER_CELL if mode == "pilot" else DEFAULT_CASES_PER_CELL
    output_dir = args.output_dir or globals().get("DEPENDENCY_BENCH_OUTPUT_DIR") or default_output_dir()
    run_benchmark(int(cases_per_cell), output_dir)
    return 0


if __name__ == "__main__":
    running_in_kernel = "IPython" in sys.modules
    exit_code = main([] if running_in_kernel else None)
    if not running_in_kernel:
        raise SystemExit(exit_code)
