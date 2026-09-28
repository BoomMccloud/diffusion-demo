#!/usr/bin/env python3
"""Prepare and run the frozen DiffusionGemma business benchmark screen.

``prepare`` performs all staged-artifact, dual-tokenizer, fixture, and context
checks without sending a generation request. ``run-diffusion`` consumes only an
accepted immutable registration and talks to the existing resident worker.
``self-test`` exercises the same registration, scoring, persistence, and resume
contracts without network, model files, or accelerator work.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import statistics
import time

try:
    from . import business_fixtures as fixtures
    from . import dependency_density_bench as density
    from . import diffusion_runtime as runtime
except ImportError:
    import business_fixtures as fixtures
    import dependency_density_bench as density
    import diffusion_runtime as runtime


REGISTRATION_SCHEMA = "business-diffusion-launch-v1"


class UnsafeLaunch(ValueError):
    def __init__(self, reason, detail):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def parse_canonical_answer(text):
    if not isinstance(text, str):
        return None
    try:
        value = json.loads(text.strip(), object_pairs_hook=unique_object)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(value, dict) or set(value) != {"values"}:
        return None
    values = value["values"]
    if (
        not isinstance(values, list)
        or len(values) != fixtures.DECISION_COUNT
        or not all(isinstance(item, str) for item in values)
    ):
        return None
    return value


def request_id_for(fixture):
    return f"business-{fixture['case_id']}-{fixture['fixture_hash'][:12]}"


def _unsigned_hash(value, key):
    return fixtures.stable_hash({name: item for name, item in value.items() if name != key})


def _fixture_without_counts(fixture):
    return {key: value for key, value in fixture.items() if key != "token_counts"}


def _valid_artifact_identity(identity):
    return (
        isinstance(identity, dict)
        and isinstance(identity.get("path"), str)
        and bool(identity["path"])
        and isinstance(identity.get("size_bytes"), int)
        and identity["size_bytes"] >= 0
        and isinstance(identity.get("sha256"), str)
        and len(identity["sha256"]) == 64
    )


def _valid_hardware_identity(identity):
    return (
        isinstance(identity, str)
        and bool(identity.strip())
        and not identity.strip().lower().startswith("unavailable:")
    )


def _warmup_accepted(result):
    if not isinstance(result, dict) or result.get("request_state") != "completed" or result.get("error"):
        return False
    stops = [event for event in result.get("native_events", []) if event.get("event") == "stop"]
    if len(stops) != 1 or stops[0].get("reason") != "eog":
        return False
    final_output, _ = density.split_native_response(result.get("raw_output", ""))
    try:
        parsed = json.loads(final_output.strip(), object_pairs_hook=unique_object)
    except (json.JSONDecodeError, ValueError):
        return False
    return parsed == {"values": ["READY"]}


def _execution_fixtures(manifest):
    planned = list(manifest["fixtures"])
    random.Random(manifest["base_seed"] ^ 0xA100).shuffle(planned)
    return planned


def build_registration(
    manifest,
    token_counts,
    worker,
    identities,
    tokenizer_identity,
    hardware_identity,
    supporting_harnesses,
    *,
    timeout_seconds,
    batch_seconds,
    ar_context_size,
):
    if not fixtures.verify_manifest(manifest):
        raise UnsafeLaunch("invalid_fixture_manifest", "fixture manifest failed deterministic verification")
    if worker.get("protocol_version") != 2:
        raise UnsafeLaunch("unsafe_worker", "resident worker must report protocol version 2")
    config = worker.get("configuration")
    if not isinstance(config, dict) or not config.get("native_protocol"):
        raise UnsafeLaunch("unsafe_worker", "resident worker must enable native protocol v2")
    context_size = config.get("context_size")
    max_tokens = config.get("max_tokens")
    if not all(isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in (context_size, max_tokens, ar_context_size)):
        raise UnsafeLaunch("unsafe_context", "positive integer context and output limits are required")
    if set(identities) != {"autoregressive_model", "diffusion_model", "runner", "harness"}:
        raise UnsafeLaunch("missing_identity", "all model, runner, and harness identities are required")
    if any(not _valid_artifact_identity(identities[name]) for name in identities):
        raise UnsafeLaunch("missing_identity", "model, runner, and harness identities require path, size, and SHA256")
    if not _valid_artifact_identity(tokenizer_identity):
        raise UnsafeLaunch("missing_identity", "tokenizer identity requires path, size, and SHA256")
    if not _valid_hardware_identity(hardware_identity):
        raise UnsafeLaunch("missing_identity", "a real GPU hardware identity is required")
    if (
        not isinstance(supporting_harnesses, dict)
        or set(supporting_harnesses) != {"fixture_generator", "resident_worker"}
        or any(not _valid_artifact_identity(item) for item in supporting_harnesses.values())
    ):
        raise UnsafeLaunch("missing_identity", "fixture and resident-worker harness identities are required")

    registered_fixtures = []
    for fixture in _execution_fixtures(manifest):
        counts = token_counts.get(fixture["case_id"])
        if not isinstance(counts, dict) or set(counts) != {"autoregressive", "diffusion"}:
            raise UnsafeLaunch("missing_token_counts", f"missing dual-tokenizer counts for {fixture['case_id']}")
        for model_name, measured in counts.items():
            if (
                not isinstance(measured, dict)
                or set(measured) != {"prompt", "expected_answer"}
                or not all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in measured.values())
            ):
                raise UnsafeLaunch("missing_token_counts", f"invalid {model_name} counts for {fixture['case_id']}")
        if counts["diffusion"]["expected_answer"] > max_tokens:
            raise UnsafeLaunch("unsafe_context", f"expected answer exceeds diffusion allowance for {fixture['case_id']}")
        if counts["diffusion"]["prompt"] + max_tokens > context_size:
            raise UnsafeLaunch("unsafe_context", f"prompt plus diffusion allowance exceeds context for {fixture['case_id']}")
        if counts["autoregressive"]["expected_answer"] > max_tokens:
            raise UnsafeLaunch("unsafe_context", f"expected answer exceeds shared AR allowance for {fixture['case_id']}")
        if counts["autoregressive"]["prompt"] + max_tokens > ar_context_size:
            raise UnsafeLaunch("unsafe_context", f"prompt plus shared AR allowance exceeds context for {fixture['case_id']}")
        registered = dict(fixture)
        registered["token_counts"] = counts
        registered_fixtures.append(registered)

    execution_order = [fixture["case_id"] for fixture in registered_fixtures]
    request_ids = {fixture["case_id"]: request_id_for(fixture) for fixture in registered_fixtures}
    if len(set(request_ids.values())) != len(request_ids):
        raise UnsafeLaunch("invalid_request_plan", "deterministic request IDs are not unique")
    registration = {
        "schema_version": REGISTRATION_SCHEMA,
        "fixture_schema_version": manifest["schema_version"],
        "manifest_hash": manifest["manifest_hash"],
        "fixtures": registered_fixtures,
        "execution_order": execution_order,
        "request_ids": request_ids,
        "worker": worker,
        "identities": identities,
        "tokenizer_identity": tokenizer_identity,
        "hardware_identity": hardware_identity,
        "supporting_harnesses": supporting_harnesses,
        "execution_seed": manifest["base_seed"] ^ 0xA100,
        "timeout_seconds": float(timeout_seconds),
        "batch_seconds": float(batch_seconds),
        "ar_context_size": int(ar_context_size),
    }
    registration["registration_hash"] = _unsigned_hash(registration, "registration_hash")
    return registration


def validate_registration(registration):
    if not isinstance(registration, dict):
        return False
    if registration.get("schema_version") != REGISTRATION_SCHEMA:
        return False
    if registration.get("registration_hash") != _unsigned_hash(registration, "registration_hash"):
        return False
    registered = registration.get("fixtures")
    if not isinstance(registered, list) or len(registered) != len(fixtures.PROBLEM_IDS) * fixtures.DEFAULT_CASES_PER_PROBLEM:
        return False
    bare = [_fixture_without_counts(fixture) for fixture in registered if isinstance(fixture, dict)]
    if len(bare) != len(registered) or not all(fixtures.validate_fixture(item) for item in bare):
        return False
    manifest = {
        "schema_version": registration.get("fixture_schema_version"),
        "base_seed": fixtures.BASE_SEED,
        "cases_per_problem": fixtures.DEFAULT_CASES_PER_PROBLEM,
        "problem_ids": list(fixtures.PROBLEM_IDS),
        "fixtures": sorted(
            bare,
            key=lambda item: (
                fixtures.PROBLEM_IDS.index(item["problem_id"]), item["fixture_index"]
            ),
        ),
    }
    manifest["manifest_hash"] = fixtures.stable_hash(manifest)
    if manifest["manifest_hash"] != registration.get("manifest_hash") or not fixtures.verify_manifest(manifest):
        return False
    if registration.get("execution_order") != [fixture["case_id"] for fixture in registered]:
        return False
    expected_ids = {fixture["case_id"]: request_id_for(fixture) for fixture in registered}
    if registration.get("request_ids") != expected_ids:
        return False
    worker = registration.get("worker", {})
    config = worker.get("configuration", {}) if isinstance(worker, dict) else {}
    if worker.get("protocol_version") != 2 or not config.get("native_protocol"):
        return False
    try:
        rebuilt = build_registration(
            manifest,
            {fixture["case_id"]: fixture["token_counts"] for fixture in registered},
            worker,
            registration["identities"],
            registration["tokenizer_identity"],
            registration["hardware_identity"],
            registration["supporting_harnesses"],
            timeout_seconds=registration["timeout_seconds"],
            batch_seconds=registration["batch_seconds"],
            ar_context_size=registration["ar_context_size"],
        )
    except (KeyError, TypeError, ValueError):
        return False
    return fixtures.compact_json(rebuilt) == fixtures.compact_json(registration)


def classify_business_result(fixture, raw_output, telemetry, registration, output_counter):
    final_output, reasoning = density.split_native_response(raw_output)
    if raw_output.startswith("<|channel>thought") and reasoning is None:
        reasoning, final_output = raw_output, ""
    parsed = parse_canonical_answer(final_output)
    semantic = fixtures.evaluate_answer(_fixture_without_counts(fixture), parsed or {})
    events = telemetry.get("native_events", [])
    stops = [event for event in events if event.get("event") == "stop"]
    stop_reason = stops[-1].get("reason") if stops else telemetry.get("native_stop_reason")
    error = telemetry.get("error")
    outcome = "correct" if semantic["valid"] else "invalid_final" if parsed is None else "incorrect"
    if len(stops) > 1:
        outcome = "ambiguous_native_stop"
    elif not stops and not error:
        outcome = "missing_native_stop"
    elif not final_output.strip() and not error:
        outcome = "budget_exhausted" if stop_reason == "block_budget" else "incomplete_reasoning"
    if stop_reason == "cancelled" or telemetry.get("request_state") == "cancelled":
        outcome = "cancelled"
    if error:
        error_type = error.get("type") if isinstance(error, dict) else "RuntimeError"
        if error_type == "TimeoutError" or telemetry.get("request_state") == "timed_out":
            outcome = "timed_out"
        elif error_type == "GenerationCancelled" or telemetry.get("request_state") == "cancelled":
            outcome = "cancelled"
        elif telemetry.get("exit_code") is not None:
            outcome = "native_crash"
        else:
            outcome = "runtime_error"
    valid = (
        semantic["valid"]
        and error is None
        and len(stops) == 1
        and stop_reason in {"eog", "block_budget"}
    )
    started_at = telemetry.get("started_at") or utc_now()
    completed_at = telemetry.get("completed_at") or utc_now()
    prompt_tokens = fixture["token_counts"]["diffusion"]["prompt"]
    row = {
        **telemetry,
        **semantic,
        "case_id": fixture["case_id"],
        "problem_id": fixture["problem_id"],
        "dependency_class": fixture["dependency_class"],
        "fixture_hash": fixture["fixture_hash"],
        "request_id": registration["request_ids"][fixture["case_id"]],
        "request_state": telemetry.get("request_state", "completed"),
        "outcome": outcome,
        "valid": bool(valid),
        "raw_output": raw_output,
        "reasoning_content": reasoning,
        "final_output": final_output,
        "native_stop_reason": stop_reason,
        "prompt_tokens": prompt_tokens,
        "output_tokens": int(output_counter(raw_output)) if raw_output else 0,
        "final_output_tokens": int(output_counter(final_output)) if final_output else 0,
        "started_at": started_at,
        "completed_at": completed_at,
        "elapsed_seconds": telemetry.get("elapsed_seconds", telemetry.get("wall_seconds")),
        "worker_elapsed_seconds": telemetry.get("worker_elapsed_seconds"),
        "model_identity": registration["identities"]["diffusion_model"],
        "runner_identity": registration["identities"]["runner"],
        "registration_hash": registration["registration_hash"],
        "error": error,
    }
    return row


def summarize(rows, allocation_seconds, stop_reason, *, expected_attempts=None, registration_hash=None):
    groups = {}
    for problem_id in fixtures.PROBLEM_IDS:
        selected = [row for row in rows if row.get("problem_id") == problem_id]
        valid_times = [row["elapsed_seconds"] for row in selected if row.get("valid") and row.get("elapsed_seconds") is not None]
        groups[problem_id] = {
            "attempts": len(selected),
            "valid": sum(bool(row.get("valid")) for row in selected),
            "median_valid_seconds": statistics.median(valid_times) if valid_times else None,
        }
    valid_count = sum(bool(row.get("valid")) for row in rows)
    summary = {
        "attempts": len(rows),
        "valid": valid_count,
        "success_rate": valid_count / len(rows) if rows else None,
        "allocation_seconds": allocation_seconds,
        "stop_reason": stop_reason,
        "groups": groups,
    }
    if expected_attempts is not None:
        summary.update(
            status=(
                "completed"
                if len(rows) == expected_attempts and stop_reason == "all_cases_completed"
                else "incomplete"
            ),
            expected_attempts=int(expected_attempts),
            registration_hash=registration_hash,
        )
    return summary


def _append_row(output, row, mirror_dir=None):
    density.append_jsonl(output / "results.jsonl", row)
    runtime.atomic_json(output / f"{row['case_id']}.result.json", row)
    runtime.mirror_file(output / "results.jsonl", mirror_dir)
    runtime.mirror_file(output / f"{row['case_id']}.result.json", mirror_dir)


def _load_rows(path, registration):
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    allowed = set(registration["execution_order"])
    seen = set()
    for row in rows:
        case_id = row.get("case_id")
        if case_id not in allowed or case_id in seen:
            raise UnsafeLaunch("invalid_resume", "results contain an unknown or duplicate case")
        if row.get("registration_hash") != registration["registration_hash"]:
            raise UnsafeLaunch("invalid_resume", "result registration hash does not match")
        if row.get("request_id") != registration["request_ids"][case_id]:
            raise UnsafeLaunch("invalid_resume", "result request ID does not match")
        seen.add(case_id)
    expected_prefix = registration["execution_order"][: len(rows)]
    if [row["case_id"] for row in rows] != expected_prefix:
        raise UnsafeLaunch("invalid_resume", "results are not an execution-order prefix")
    return rows


def _count_fixture_tokens(manifest, tokenizer_path, ar_model, diffusion_model):
    counts = {fixture["case_id"]: {} for fixture in manifest["fixtures"]}
    for model_name, model_path in (("autoregressive", ar_model), ("diffusion", diffusion_model)):
        tokenizer = density.TokenizerService(tokenizer_path, model_path)
        try:
            for fixture in manifest["fixtures"]:
                counts[fixture["case_id"]][model_name] = {
                    "prompt": tokenizer.count_prompt(fixture["prompt"]),
                    "expected_answer": tokenizer.count(fixtures.compact_json(fixture["reference_answer"])),
                }
        finally:
            tokenizer.close()
    return counts


def prepare(args):
    output = Path(args.output_dir)
    if (output / "registration.json").exists():
        registration = json.loads((output / "registration.json").read_text(encoding="utf-8"))
        if not validate_registration(registration):
            raise UnsafeLaunch("invalid_registration", "existing registration failed verification")
        state = runtime.rpc(args.url, "/status")
        live_worker = {"protocol_version": state.get("protocol_version"), "configuration": state.get("configuration")}
        if live_worker != registration["worker"]:
            raise UnsafeLaunch("worker_mismatch", "live worker configuration differs from registration")
        current_identities = {
            "autoregressive_model": density.artifact_identity(args.ar_model),
            "diffusion_model": density.artifact_identity(live_worker["configuration"]["model_path"]),
            "runner": density.artifact_identity(live_worker["configuration"]["runner_path"]),
            "harness": density.artifact_identity(__file__),
        }
        if current_identities != registration["identities"]:
            raise UnsafeLaunch("artifact_mismatch", "staged model, runner, or harness identity changed")
        if density.artifact_identity(args.tokenizer) != registration["tokenizer_identity"]:
            raise UnsafeLaunch("artifact_mismatch", "staged tokenizer identity changed")
        if density.hardware_identity() != registration["hardware_identity"]:
            raise UnsafeLaunch("artifact_mismatch", "hardware identity changed")
        current_supporting = {
            "fixture_generator": density.artifact_identity(fixtures.__file__),
            "resident_worker": density.artifact_identity(runtime.__file__),
        }
        if current_supporting != registration["supporting_harnesses"]:
            raise UnsafeLaunch("artifact_mismatch", "fixture or resident-worker harness changed")
        return registration
    manifest = fixtures.build_manifest()
    state = runtime.rpc(args.url, "/status")
    config = state.get("configuration", {})
    worker = {"protocol_version": state.get("protocol_version"), "configuration": config}
    if state.get("active_request"):
        raise UnsafeLaunch("worker_busy", "resident worker has an active request")
    diffusion_model = config.get("model_path")
    if not diffusion_model:
        raise UnsafeLaunch("missing_identity", "worker did not report its diffusion model path")
    token_counts = _count_fixture_tokens(manifest, args.tokenizer, args.ar_model, diffusion_model)
    identities = {
        "autoregressive_model": density.artifact_identity(args.ar_model),
        "diffusion_model": density.artifact_identity(diffusion_model),
        "runner": density.artifact_identity(config.get("runner_path", "")),
        "harness": density.artifact_identity(__file__),
    }
    registration = build_registration(
        manifest,
        token_counts,
        worker,
        identities,
        density.artifact_identity(args.tokenizer),
        density.hardware_identity(),
        {
            "fixture_generator": density.artifact_identity(fixtures.__file__),
            "resident_worker": density.artifact_identity(runtime.__file__),
        },
        timeout_seconds=args.timeout,
        batch_seconds=args.batch_seconds,
        ar_context_size=args.ar_context_size,
    )
    output.mkdir(parents=True, exist_ok=True)
    runtime.atomic_json(output / "registration.json", registration)
    runtime.mirror_file(output / "registration.json", args.mirror_dir)
    return registration


def run_diffusion(args):
    output = Path(args.output_dir)
    registration_path = output / "registration.json"
    if not registration_path.exists():
        raise UnsafeLaunch("missing_registration", "run prepare before run-diffusion")
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    if not validate_registration(registration):
        raise UnsafeLaunch("invalid_registration", "registration failed verification")
    state = runtime.rpc(args.url, "/status")
    current_worker = {"protocol_version": state.get("protocol_version"), "configuration": state.get("configuration")}
    if current_worker != registration["worker"]:
        raise UnsafeLaunch("worker_mismatch", "live worker configuration differs from registration")
    if state.get("active_request"):
        raise UnsafeLaunch("worker_busy", "resident worker has an active request")
    current_identities = {
        "autoregressive_model": density.artifact_identity(registration["identities"]["autoregressive_model"]["path"]),
        "diffusion_model": density.artifact_identity(current_worker["configuration"]["model_path"]),
        "runner": density.artifact_identity(current_worker["configuration"]["runner_path"]),
        "harness": density.artifact_identity(__file__),
    }
    if current_identities != registration["identities"]:
        raise UnsafeLaunch("artifact_mismatch", "registered model, runner, or harness identity changed")
    if density.artifact_identity(args.tokenizer) != registration["tokenizer_identity"]:
        raise UnsafeLaunch("artifact_mismatch", "registered tokenizer identity changed")
    if density.hardware_identity() != registration["hardware_identity"]:
        raise UnsafeLaunch("artifact_mismatch", "registered hardware identity changed")
    current_supporting = {
        "fixture_generator": density.artifact_identity(fixtures.__file__),
        "resident_worker": density.artifact_identity(runtime.__file__),
    }
    if current_supporting != registration["supporting_harnesses"]:
        raise UnsafeLaunch("artifact_mismatch", "registered fixture or worker harness changed")

    rows = _load_rows(output / "results.jsonl", registration)
    completed = {row["case_id"] for row in rows}
    fixture_by_id = {fixture["case_id"]: fixture for fixture in registration["fixtures"]}
    tokenizer_path = args.tokenizer
    diffusion_model = registration["worker"]["configuration"]["model_path"]
    tokenizer = density.TokenizerService(tokenizer_path, diffusion_model)
    sampler = density.GPUMemorySampler()
    sampler.thread.start()
    started = time.monotonic()
    deadline = started + registration["batch_seconds"]
    stop_reason = "all_cases_completed"
    try:
        warmup_path = output / "warmup.json"
        if not warmup_path.exists():
            if not runtime.admit_case(deadline - time.monotonic(), registration["timeout_seconds"]):
                raise UnsafeLaunch("insufficient_budget", "not enough time remains for warmup")
            warmup_id = "business-warmup-" + registration["registration_hash"][:16]
            runtime.rpc(args.url, "/generate", {
                "request_id": warmup_id,
                "prompt": 'Return exactly {"values":["READY"]} and no other text.',
                "timeout_seconds": registration["timeout_seconds"],
            })
            warmup = runtime.wait_result(args.url, warmup_id, registration["timeout_seconds"] + 60)
            runtime.atomic_json(warmup_path, warmup)
            runtime.mirror_file(warmup_path, args.mirror_dir)
        else:
            warmup = json.loads(warmup_path.read_text(encoding="utf-8"))
        if not _warmup_accepted(warmup):
            stop_reason = "warmup_failed"
            raise UnsafeLaunch(
                "warmup_failed",
                "warmup must complete with one native EOG and the exact READY response; inspect warmup.json",
            )

        for case_id in registration["execution_order"]:
            if case_id in completed:
                continue
            if not runtime.admit_case(deadline - time.monotonic(), registration["timeout_seconds"]):
                stop_reason = "insufficient_full_case_budget"
                break
            fixture = fixture_by_id[case_id]
            request_id = registration["request_ids"][case_id]
            request_started = utc_now()
            measured = time.perf_counter()
            runtime.rpc(args.url, "/generate", {
                "request_id": request_id,
                "prompt": fixture["prompt"],
                "timeout_seconds": registration["timeout_seconds"],
            })
            result = runtime.wait_result(args.url, request_id, registration["timeout_seconds"] + 30)
            result = dict(result, started_at=request_started, completed_at=utc_now())
            row = classify_business_result(fixture, result.get("raw_output", ""), result, registration, tokenizer.count)
            row["sampled_peak_device_memory_mib"] = sampler.peak_since(measured)
            _append_row(output, row, args.mirror_dir)
            rows.append(row)
            current_summary = summarize(
                rows,
                time.monotonic() - started,
                "running",
                expected_attempts=len(registration["execution_order"]),
                registration_hash=registration["registration_hash"],
            )
            runtime.atomic_json(output / "summary.json", current_summary)
            runtime.mirror_file(output / "summary.json", args.mirror_dir)
            print(json.dumps({key: row.get(key) for key in ("case_id", "valid", "outcome", "elapsed_seconds", "error")}), flush=True)
            if row.get("error") or row["outcome"] in {"missing_native_stop", "ambiguous_native_stop"}:
                stop_reason = "runtime_gate_failed"
                break
    finally:
        sampler.close()
        tokenizer.close()
        final_summary = summarize(
            rows,
            time.monotonic() - started,
            stop_reason,
            expected_attempts=len(registration["execution_order"]),
            registration_hash=registration["registration_hash"],
        )
        runtime.atomic_json(output / "summary.json", final_summary)
        runtime.mirror_file(output / "summary.json", args.mirror_dir)
    return final_summary


def _synthetic_counts(manifest):
    result = {}
    for fixture in manifest["fixtures"]:
        prompt = max(1, len(fixture["prompt"].encode("utf-8")) // 4)
        answer = max(1, len(fixtures.compact_json(fixture["reference_answer"]).encode("utf-8")) // 4)
        result[fixture["case_id"]] = {
            "autoregressive": {"prompt": prompt + 1, "expected_answer": answer + 1},
            "diffusion": {"prompt": prompt, "expected_answer": answer},
        }
    return result


def _synthetic_telemetry(index):
    base = {
        "request_state": "completed",
        "native_events": [{"event": "stop", "reason": "eog"}],
        "native_stop_reason": "eog",
        "elapsed_seconds": 1.0 + index / 100,
        "worker_elapsed_seconds": 1.1 + index / 100,
        "error": None,
        "exit_code": None,
    }
    if index == 2:
        base.update(request_state="timed_out", native_events=[], native_stop_reason=None,
                    error={"type": "TimeoutError", "message": "synthetic deadline"})
    elif index == 3:
        base.update(request_state="cancelled", native_events=[{"event": "stop", "reason": "cancelled"}],
                    native_stop_reason="cancelled", error={"type": "GenerationCancelled", "message": "synthetic cancel"})
    elif index == 4:
        base.update(request_state="failed", native_events=[], native_stop_reason=None, exit_code=37,
                    error={"type": "RuntimeError", "message": "synthetic native exit"})
    return base


def self_test(args):
    output = Path(args.output_dir)
    generation_rpc_calls = 0
    registration_path = output / "registration.json"
    results_path = output / "results.jsonl"
    if registration_path.exists() or results_path.exists():
        if not registration_path.exists() or not results_path.exists():
            raise UnsafeLaunch("invalid_resume", "self-test resume artifacts are incomplete")
        registration = json.loads(registration_path.read_text(encoding="utf-8"))
        if not validate_registration(registration):
            raise UnsafeLaunch("invalid_resume", "self-test registration is invalid")
        rows = _load_rows(results_path, registration)
        if len(rows) != 36:
            raise UnsafeLaunch("invalid_resume", "self-test result set is incomplete")
        new_attempts, resumed_attempts = 0, len(rows)
    else:
        manifest = fixtures.build_manifest()
        worker = {
            "protocol_version": 2,
            "configuration": {
                "native_protocol": True,
                "context_size": int(args.context_size),
                "max_tokens": int(args.max_tokens),
                "runner_path": "/synthetic/llama-diffusion-cli",
                "model_path": "/synthetic/diffusiongemma.gguf",
                "seed": fixtures.BASE_SEED,
                "trace_mode": "summary",
                "prefill_chunk": 2048,
                "incremental_prefill": True,
                "repetition_policy": "off",
            },
        }
        identities = {
            "autoregressive_model": {"path": "/synthetic/gemma.gguf", "size_bytes": 1, "sha256": "a" * 64},
            "diffusion_model": {"path": "/synthetic/diffusiongemma.gguf", "size_bytes": 1, "sha256": "d" * 64},
            "runner": {"path": "/synthetic/llama-diffusion-cli", "size_bytes": 1, "sha256": "b" * 64},
            "harness": density.artifact_identity(__file__),
        }
        tokenizer_identity = {"path": "/synthetic/dependency-tokenizer", "size_bytes": 1, "sha256": "c" * 64}
        hardware_identity = "synthetic A100"
        supporting_harnesses = {
            "fixture_generator": density.artifact_identity(fixtures.__file__),
            "resident_worker": density.artifact_identity(runtime.__file__),
        }
        try:
            registration = build_registration(
                manifest,
                _synthetic_counts(manifest),
                worker,
                identities,
                tokenizer_identity,
                hardware_identity,
                supporting_harnesses,
                timeout_seconds=120,
                batch_seconds=7200,
                ar_context_size=int(args.context_size),
            )
        except UnsafeLaunch as error:
            report = {
                "status": "refused",
                "reason": error.reason,
                "detail": error.detail,
                "generation_rpc_calls": generation_rpc_calls,
            }
            if args.json:
                print(fixtures.compact_json(report))
            else:
                print(f"refused: {error.reason}: {error.detail}")
            return 1
        output.mkdir(parents=True, exist_ok=True)
        runtime.atomic_json(registration_path, registration)
        rows = []
        duplicate_index = 5
        for index, fixture in enumerate(registration["fixtures"]):
            if index == 0:
                raw = "<|channel>thought\nsynthetic reasoning<channel|>" + fixtures.compact_json(fixture["reference_answer"])
            elif index == 1:
                raw = "not json"
            elif index in (2, 3, 4):
                raw = "<|channel>thought\nsynthetic incomplete"
            elif index == duplicate_index:
                values = fixtures.compact_json(fixture["reference_answer"]["values"])
                raw = '{"values":[],"values":' + values + "}"
            else:
                raw = fixtures.compact_json(fixture["reference_answer"])
            telemetry = dict(_synthetic_telemetry(index), started_at=f"synthetic-{index:02d}-start", completed_at=f"synthetic-{index:02d}-end")
            row = classify_business_result(fixture, raw, telemetry, registration, lambda text: len(text.encode("utf-8")))
            _append_row(output, row)
            rows.append(row)
        new_attempts, resumed_attempts = len(rows), 0

    outcomes = {row["outcome"] for row in rows}
    required = {
        "case_id", "fixture_hash", "request_id", "request_state", "outcome",
        "valid", "exact_match", "per_decision_correct", "first_error",
        "constraint_violations", "raw_output", "reasoning_content", "final_output",
        "native_stop_reason", "prompt_tokens", "output_tokens", "started_at",
        "completed_at", "elapsed_seconds", "worker_elapsed_seconds",
        "model_identity", "runner_identity", "registration_hash",
    }
    checks = {
        "registration_valid": validate_registration(registration),
        "manifest_bound": all(fixtures.validate_fixture(_fixture_without_counts(item)) for item in registration["fixtures"]),
        "dual_tokenizer_counts": all(set(item["token_counts"]) == {"autoregressive", "diffusion"} for item in registration["fixtures"]),
        "deterministic_request_ids": len(set(registration["request_ids"].values())) == 36,
        "terminal_rows_complete": all(not (required - set(row)) for row in rows),
        "terminal_outcomes_retained": {"invalid_final", "timed_out", "cancelled", "native_crash"} <= outcomes,
        "valid_reasoning_retained": any(row["valid"] and row["reasoning_content"] for row in rows),
        "duplicate_keys_rejected": parse_canonical_answer('{"values":[],"values":[]}') is None and rows[5]["outcome"] == "invalid_final",
        "no_generation_rpc": generation_rpc_calls == 0,
        "resume_contract": len(rows) == len(registration["execution_order"]) == 36,
        "runtime_provenance_bound": bool(registration.get("hardware_identity"))
        and set(registration.get("supporting_harnesses", {}))
        == {"fixture_generator", "resident_worker"},
    }
    report = {
        "status": "launch_ready" if all(checks.values()) else "failed",
        "fixture_count": len(registration["fixtures"]),
        "decision_count": fixtures.DECISION_COUNT,
        "new_attempts": new_attempts,
        "resumed_attempts": resumed_attempts,
        "generation_rpc_calls": generation_rpc_calls,
        "checks": checks,
    }
    if args.json:
        print(fixtures.compact_json(report))
    else:
        print(f"{report['status']}: {report['fixture_count']} fixtures")
    return 0 if report["status"] == "launch_ready" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    self_parser = subparsers.add_parser("self-test")
    self_parser.add_argument("--output-dir", required=True)
    self_parser.add_argument("--url", default="http://127.0.0.1:8765")
    self_parser.add_argument("--context-size", type=int, default=16_384)
    self_parser.add_argument("--max-tokens", type=int, default=4_096)
    self_parser.add_argument("--json", action="store_true")

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--url", default="http://127.0.0.1:8765")
    prepare_parser.add_argument("--output-dir", required=True)
    prepare_parser.add_argument("--mirror-dir")
    prepare_parser.add_argument("--tokenizer", required=True)
    prepare_parser.add_argument("--ar-model", required=True)
    prepare_parser.add_argument("--ar-context-size", type=int, default=11_264)
    prepare_parser.add_argument("--timeout", type=float, default=300)
    prepare_parser.add_argument("--batch-seconds", type=float, default=14_400)

    run_parser = subparsers.add_parser("run-diffusion")
    run_parser.add_argument("--url", default="http://127.0.0.1:8765")
    run_parser.add_argument("--output-dir", required=True)
    run_parser.add_argument("--mirror-dir")
    run_parser.add_argument("--tokenizer", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "self-test":
            return self_test(args)
        if args.command == "prepare":
            registration = prepare(args)
            print(fixtures.compact_json({
                "status": "launch_ready",
                "fixture_count": len(registration["fixtures"]),
                "registration_hash": registration["registration_hash"],
                "generation_rpc_calls": 0,
            }))
            return 0
        report = run_diffusion(args)
        print(fixtures.compact_json(report))
        return 0 if report["status"] == "completed" else 3
    except UnsafeLaunch as error:
        print(fixtures.compact_json({"status": "refused", "reason": error.reason, "detail": error.detail}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
