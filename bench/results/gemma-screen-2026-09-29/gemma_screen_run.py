#!/usr/bin/env python3
"""Run planning or homework cases through Gemma 4 AR or DiffusionGemma on one A100.

Rows match ``bench/nemotron_runner.py`` so the planning and homework scorers work
unchanged. Both arms get the same prompt with whitespace collapsed to single
spaces, because the diffusion CLI reads one line per turn.

  ar         Gemma 4 26B A4B GGUF through llama-cpp-python, in this process
  diffusion  a running ``bench/diffusion_runtime.py serve`` worker at --url
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))  # bench/ is copied beside this script on Colab
import gemma_runtimes as g
import diffusion_runtime as runtime

SCHEMA = "gemma-screen-v1"


def read_jsonl(path):
    path = Path(path)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def append(path, row):
    with open(path, "a") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("arm", choices=("ar", "diffusion"))
    p.add_argument("--cases", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-tokens", type=int, required=True)
    p.add_argument("--context", type=int, required=True)
    p.add_argument("--timeout", type=float, default=900)
    p.add_argument("--seed", type=int, default=20260909)
    p.add_argument("--ar-model")
    p.add_argument("--url", default="http://127.0.0.1:8765")
    p.add_argument("--think", action="store_true",
                   help="AR only: render the GGUF chat template with enable_thinking=True. Without it the template "
                        "pre-fills an empty thought channel, so a <|think|> system message alone does not enable thinking.")
    args = p.parse_args()

    arm = f"gemma4-26b-a4b-{args.arm}" + ("-think" if args.think else "")
    done = {row["case_id"] for row in read_jsonl(args.out) if row["arm"] == arm}
    cases = [case for case in read_jsonl(args.cases) if case["case_id"] not in done]
    hardware = g.hardware_identity()
    model = g.load_ar(args.ar_model, args.context, args.seed) if args.arm == "ar" else None
    if args.think:
        from jinja2.sandbox import ImmutableSandboxedEnvironment
        template = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True).from_string(
            model.metadata["tokenizer.chat_template"])
        end_ids = {model.token_eos(), *model.tokenize(b"<turn|>", add_bos=False, special=True)}
    # Path and size only; hashing the 16 GB GGUF from Drive costs minutes. The repo and filename pin it.
    identity = {"path": args.ar_model, "size_bytes": os.path.getsize(args.ar_model)} if args.arm == "ar" else runtime.rpc(args.url, "/status")

    for case in cases:
        prompt = " ".join(case["prompt"].split())
        started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        error = reasoning = None
        raw, output_tokens, stop, elapsed, extra = "", None, None, None, {}
        try:
            if args.arm == "ar":
                model.reset()
                model.set_seed(args.seed)
                start = time.perf_counter()
                if args.think:
                    # BOS comes from tokenize, so the template's bos_token is empty.
                    text = template.render(messages=[{"role": "user", "content": prompt}], add_generation_prompt=True,
                                           enable_thinking=True, bos_token="")
                    ids = model.tokenize(text.encode(), add_bos=True, special=True)
                    out = []
                    for token in model.generate(ids, top_k=1, top_p=1.0, min_p=0.0, temp=0.0, repeat_penalty=1.0):
                        if token in end_ids:
                            stop = "eos"
                            break
                        out.append(token)
                        if len(out) >= args.max_tokens:
                            stop = "max_new_tokens"
                            break
                    elapsed = time.perf_counter() - start
                    raw = model.detokenize(out, special=True).decode(errors="replace")
                    output_tokens = len(out)
                    extra = {"prompt_tokens": len(ids), "rendered_prompt_tail": text[-80:]}
                else:
                    response = model.create_chat_completion(
                        messages=[{"role": "user", "content": prompt}], max_tokens=args.max_tokens, temperature=0.0)
                    elapsed = time.perf_counter() - start
                    choice = response["choices"][0]
                    raw = choice["message"]["content"] or ""
                    reasoning = choice["message"].get("reasoning_content")
                    output_tokens = response.get("usage", {}).get("completion_tokens")
                    stop = {"stop": "eos", "length": "max_new_tokens"}.get(choice.get("finish_reason"), choice.get("finish_reason"))
                    extra = {"prompt_tokens": response.get("usage", {}).get("prompt_tokens")}
            else:
                rid = f"{case['case_id']}-{uuid.uuid4().hex[:8]}"
                runtime.rpc(args.url, "/generate", {"request_id": rid, "prompt": prompt, "timeout_seconds": args.timeout})
                result = runtime.wait_result(args.url, rid, args.timeout + 60)
                raw = result.get("raw_output") or ""
                elapsed = result.get("wall_seconds") or result.get("worker_elapsed_seconds")
                native = result.get("native_stop_reason")
                stop = {"eog": "eos", "block_budget": "max_new_tokens"}.get(native, native)
                output_tokens = result.get("canvas_work_tokens")
                error = result.get("error")
                extra = {"request_id": rid, "native_stop_reason": native,
                         "internal_compute_seconds": result.get("internal_compute_seconds")}
        except Exception as exc:  # keep the failure as a row
            error = {"type": type(exc).__name__, "message": str(exc)}
        final, native_reasoning = g.split_native_response(raw)
        if raw.startswith("<|channel>thought") and native_reasoning is None:
            final, native_reasoning = "", raw  # reasoning never closed
        row = {
            "schema": SCHEMA, "arm": arm, "mode": args.arm, "case_id": case["case_id"],
            "hardware": hardware, "identity": identity, "seed": args.seed,
            "max_new_tokens": args.max_tokens, "context": args.context, "prompt_whitespace_collapsed": True,
            "started_at": started_at, "elapsed_seconds": round(elapsed, 3) if elapsed else None,
            "output_tokens": output_tokens, "nfe": None, "stop_reason": "error" if error else stop,
            "raw_output": raw, "reasoning": reasoning or native_reasoning, "final_output": final.strip(),
            "error": error, **extra,
        }
        append(args.out, row)
        print(json.dumps({k: row[k] for k in ("arm", "case_id", "stop_reason", "output_tokens", "elapsed_seconds")}), flush=True)


if __name__ == "__main__":
    main()
