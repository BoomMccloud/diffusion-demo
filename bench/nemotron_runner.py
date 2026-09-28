#!/usr/bin/env python3
"""Run Nemotron-Labs-Diffusion on one GPU in its three decoding modes, or an AR endpoint.

The same weights expose three generators through the model's remote code:
  ar           ``model.ar_generate``: one token per forward pass
  linear_spec  ``model.linear_spec_generate``: diffusion drafts a block, AR verifies it
  diffusion    ``model.generate``: parallel block diffusion, confidence ``--threshold``

Input is JSONL, one case per line: ``{"case_id", "prompt", "max_new_tokens"?}``.
Output is JSONL rows with raw output, stop reason, token counts, forward passes
(``nfe``) and wall time. Rows resume by (case_id, arm). Scoring belongs to the workload.

Subcommands:
  nemotron    Colab GPU, needs torch and transformers
  openrouter  local, reads OPENROUTER_API_KEY from the environment or .env.local
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request


RUN_SCHEMA = "nemotron-runner-v1"
DEFAULT_MAX_NEW_TOKENS = 2048
DEFAULT_REVISION = "0d51902da1f8869f83413ce642fab402fa5641e0"  # Nemotron-Labs-Diffusion-3B used by the 2026-09-28 runs
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def prompt_hash(prompt):
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def load_cases(path):
    cases = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    ids = [case["case_id"] for case in cases]
    if len(set(ids)) != len(ids):
        raise SystemExit("case_id values must be unique")
    return cases


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


def pending(cases, out, arm):
    done = {(row["case_id"], row["arm"]) for row in load_rows(out)}
    return [case for case in cases if (case["case_id"], arm) not in done]


def strip_thinking(text):
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return text.strip()


def thinking_text(text):
    return text.split("</think>")[0].replace("<think>", "").strip() if "</think>" in text else None


def cmd_nemotron(args):
    import torch
    from transformers import AutoModel, AutoTokenizer

    cases = load_cases(args.cases)
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

    def cap_for(case):
        # Diffusion decodes whole blocks, so round a per-case cap up to the block length.
        wanted = case.get("max_new_tokens") or args.max_new_tokens
        return -(-wanted // args.block_length) * args.block_length

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
        todo = pending(cases, args.out, arm)
        run(mode, encode("Reply with the single word READY."), 64)  # warmup, not recorded
        for case in todo:
            ids = encode(case["prompt"])
            started_at = utc_now()
            torch.cuda.synchronize()
            start = time.perf_counter()
            error = None
            try:
                out, nfe = run(mode, ids, cap_for(case))
            except Exception as exc:  # retain the failure as a row
                out, nfe, error = None, None, {"type": type(exc).__name__, "message": str(exc)}
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - start
            generated = out[0, ids.shape[1]:].tolist() if out is not None else []
            stop_at = next((i for i, tok in enumerate(generated) if tok in stop_ids), None)
            kept = generated if stop_at is None else generated[:stop_at]
            raw = tokenizer.decode(kept, skip_special_tokens=False)
            row = {
                "schema": RUN_SCHEMA,
                "arm": arm,
                "mode": mode,
                "model": args.model,
                "model_revision": revision,
                "gpu": gpu,
                "torch_version": torch.__version__,
                "transformers_version": transformers.__version__,
                "thinking": args.thinking,
                "case_id": case["case_id"],
                "prompt_hash": prompt_hash(case["prompt"]),
                "prompt_tokens": int(ids.shape[1]),
                "output_tokens": len(kept),
                "stop_reason": "error" if error else ("eos" if stop_at is not None else "max_new_tokens"),
                "nfe": int(nfe) if nfe is not None else None,
                "max_new_tokens": cap_for(case),
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
    cases = load_cases(args.cases)
    api_key = read_api_key(args.env_file)
    arm = f"openrouter-{args.model.split('/')[-1]}"
    for case in pending(cases, args.out, arm):
        body = {
            "model": args.model,
            "messages": [{"role": "user", "content": case["prompt"]}],
            "temperature": 0,
            "max_tokens": case.get("max_new_tokens") or args.max_new_tokens,
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
            "schema": RUN_SCHEMA,
            "arm": arm,
            "mode": "ar-endpoint",
            "model": args.model,
            "served_model": (response or {}).get("model"),
            "provider": (response or {}).get("provider"),
            "generation_id": (response or {}).get("id"),
            "thinking": False,
            "case_id": case["case_id"],
            "prompt_hash": prompt_hash(case["prompt"]),
            "prompt_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "stop_reason": "error" if error else choice.get("finish_reason"),
            "max_new_tokens": case.get("max_new_tokens") or args.max_new_tokens,
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("nemotron")
    p.add_argument("--cases", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--model", default="nvidia/Nemotron-Labs-Diffusion-3B")
    p.add_argument("--revision", default=DEFAULT_REVISION)
    p.add_argument("--thinking", action="store_true", help="render the chat template with enable_thinking=True")
    p.add_argument("--arm-prefix", default="nemotron-3b")
    p.add_argument("--modes", default="ar,linear_spec,diffusion")
    p.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS, help="cap for cases without max_new_tokens")
    p.add_argument("--block-length", type=int, default=32)
    p.add_argument("--threshold", type=float, default=0.9)
    p.set_defaults(func=cmd_nemotron)

    p = sub.add_parser("openrouter")
    p.add_argument("--cases", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--env-file", default=str(Path(__file__).resolve().parents[1] / ".env.local"))
    p.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    p.add_argument("--reasoning-off", action="store_true")
    p.add_argument("--timeout", type=float, default=300)
    p.set_defaults(func=cmd_openrouter)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
