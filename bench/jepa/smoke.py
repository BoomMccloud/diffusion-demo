#!/usr/bin/env python3
"""LLM-JEPA LoRA smoke test on Nemotron-Labs-Diffusion-3B.

One set of weights, trained with the losses it decodes with, plus an optional JEPA term:

  ar_loss    causal attention, next-token cross entropy on the answer
  dlm_loss   one answer block denoised under bidirectional attention over a causal KV
             prefix, the way ``model.generate`` decodes (first block token seeded clean)
  jepa_loss  1 - cos(Enc(Text), Enc(Code)) on clean, separately encoded views,
             as in galilai-group/llm-jepa ``finetune.py`` with predictors=0

``--lbd 0`` skips the JEPA passes, which makes the same script the baseline arm.
The smoke test checks that training runs on the DGX Spark, the losses fall, and answers still
parse in ``ar`` and ``diffusion`` modes. It is not a result: one seed, few steps.

Data: NL-RX-SYNTH (Locascio et al. 2016, arXiv:1608.03000) as preprocessed in
galilai-group/llm-jepa (Apache-2.0) at commit ``REFERENCE_COMMIT``. Scoring is exact
string match, as in that repo's evaluate.py for regex tasks.

Usage on the DGX Spark, inside the docker image from bench/jepa/Dockerfile:
  python bench/jepa/smoke.py --out runs/jepa-smoke --steps 50 --lbd 0.5
  python bench/jepa/smoke.py --out runs/base-smoke --steps 50 --lbd 0
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
import re
import time
import urllib.request

RUN_SCHEMA = "jepa-smoke-v1"
MODEL = "nvidia/Nemotron-Labs-Diffusion-3B"
REVISION = "0d51902da1f8869f83413ce642fab402fa5641e0"  # same pin as bench/nemotron_runner.py
REFERENCE_COMMIT = "ea0017c654ad917066ff32afc88276bea8ca5f7e"
DATA_URL = f"https://raw.githubusercontent.com/galilai-group/llm-jepa/{REFERENCE_COMMIT}/datasets/{{name}}.jsonl"
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_examples(name, cache_dir):
    path = Path(cache_dir) / f"{name}.jsonl"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(DATA_URL.format(name=name), path)
    return [json.loads(line)["messages"] for line in path.read_text().splitlines() if line.strip()]


GSM8K_ANSWER = re.compile(r"\n#### (.+)$")  # llm-jepa evaluate.py gsm8k_pattern


def score(dataset, output, reference):
    """Score as llm-jepa evaluate.py does: the #### answer for GSM8K, exact string otherwise."""
    if dataset.startswith("gsm8k"):
        found = GSM8K_ANSWER.search(output)
        return found is not None and found.group(1) == GSM8K_ANSWER.search(reference).group(1)
    return output == reference.strip()


def append(path, row):
    with open(path, "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def set_attention(model, bidirectional):
    """Flip every attention layer between diffusion (bidirectional) and AR (causal)."""
    for module in model.modules():
        if hasattr(module, "diffusion_lm"):
            module.diffusion_lm = bidirectional


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, help="directory for train_log.jsonl, eval.jsonl, run.json")
    p.add_argument("--dataset", default="synth", help="llm-jepa dataset name: synth, turk, gsm8k")
    p.add_argument("--data-dir", default="bench/jepa/.data")
    p.add_argument("--steps", type=int, default=50, help="optimizer steps")
    p.add_argument("--epochs", type=float, default=0,
                   help="if > 0, train this many passes over the training examples instead of --steps")
    p.add_argument("--val-cases", type=int, default=0,
                   help="if > 0, hold this many training examples out and score on them instead of the test set")
    p.add_argument("--val-seed", type=int, default=0, help="fixed seed for the validation split, shared by all arms")
    p.add_argument("--skip-eval-before", action="store_true", help="do not score the untrained model")
    p.add_argument("--eval-before-cases", type=int, default=0,
                   help="if > 0, score the untrained model on only the first N eval cases")
    p.add_argument("--grad-accum", type=int, default=4, help="examples per optimizer step (batch 1 each)")
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--lora-rank", type=int, default=16)
    p.add_argument("--lbd", type=float, default=0.5, help="JEPA loss weight; 0 is the baseline arm")
    p.add_argument("--jepa-attn", choices=["bidirectional", "causal"], default="bidirectional",
                   help="attention used to encode the two views")
    p.add_argument("--pool", choices=["last", "mean"], default="last",
                   help="last: hidden state at the view's final <|im_end|>; mean: average over the view")
    p.add_argument("--block-length", type=int, default=32, help="diffusion block, same as the runner default")
    p.add_argument("--threshold", type=float, default=0.9, help="diffusion decode confidence threshold")
    p.add_argument("--eval-cases", type=int, default=20, help="test cases scored before and after training")
    p.add_argument("--eval-modes", default="ar,diffusion")
    p.add_argument("--max-new-tokens", type=int, default=64)
    p.add_argument("--seed", type=int, default=82)
    args = p.parse_args(argv)

    import torch
    import torch.nn.functional as F
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModel, AutoTokenizer

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    train = load_examples(f"{args.dataset}_train", args.data_dir)
    test = load_examples(f"{args.dataset}_test", args.data_dir)[: args.eval_cases]
    split = "test"
    if args.val_cases > 0:
        # Validation comes out of the training data, never the test set, with a seed every arm shares.
        idx = random.Random(args.val_seed).sample(range(len(train)), len(train))
        test = [train[i] for i in idx[: args.val_cases]]
        train = [train[i] for i in idx[args.val_cases:]]
        split = "val"
    if args.epochs > 0:
        args.steps = math.ceil(args.epochs * len(train) / args.grad_accum)

    tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION, trust_remote_code=True)
    base = AutoModel.from_pretrained(MODEL, revision=REVISION, trust_remote_code=True, dtype=torch.bfloat16).cuda()
    im_end = tok.convert_tokens_to_ids("<|im_end|>")
    stop_ids = {tok.eos_token_id, im_end} - {None}

    def ids_of(text):
        return tok(text, return_tensors="pt", add_special_tokens=False).input_ids.cuda()

    def render(messages, generation_prompt):
        return tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=generation_prompt,
                                       enable_thinking=False)

    def encode_example(messages):
        prompt = render(messages[:2], True)
        full = render(messages[:3], False)
        if not full.startswith(prompt):
            raise ValueError("chat template renders the prompt differently inside the full conversation")
        return {
            "prompt": ids_of(prompt),
            "answer": ids_of(full[len(prompt):]),
            "text_view": ids_of(render(messages[:2], False)),  # system + user, as in llm-jepa
            "code_view": ids_of(render(messages[2:3], False)),  # assistant message alone
        }

    sample = encode_example(train[0])
    print("text view:", repr(tok.decode(sample["text_view"][0])))
    print("code view:", repr(tok.decode(sample["code_view"][0])))
    print("answer   :", repr(tok.decode(sample["answer"][0])))

    def embed(model, ids):
        set_attention(model, args.jepa_attn == "bidirectional")
        kwargs = {} if args.jepa_attn == "bidirectional" else {"use_causal_mask": True}
        hidden = model(ids, output_last_hidden_states_only=True, **kwargs).last_hidden_state[0]
        if args.pool == "mean":
            return hidden.mean(0)
        ends = (ids[0] == im_end).nonzero()
        return hidden[ends[-1, 0] if len(ends) else -1]

    def losses(model, ex):
        prompt, answer = ex["prompt"], ex["answer"]
        n_prompt, n_answer = prompt.shape[1], answer.shape[1]
        full = torch.cat([prompt, answer], dim=1)

        # AR pass over prompt + answer. Its KV cache is the causal prefix for the diffusion block.
        set_attention(model, False)
        ar = model(full, use_cache=True, use_causal_mask=True)
        ar_loss = F.cross_entropy(ar.logits[0, n_prompt - 1:-1].float(), full[0, n_prompt:])

        # Diffusion pass on one answer block, matching generate(): blocks start at the end of the
        # prompt, the first token is seeded by the causal pass, the rest are masked with rate t.
        n_blocks = math.ceil(n_answer / args.block_length)
        k = random.randrange(n_blocks)
        start = n_prompt + k * args.block_length
        block = full[:, start:start + args.block_length]
        cache = ar.past_key_values
        # transformers 5 only accepts a negative count of tokens to drop; older versions accept it too.
        n_drop = cache.get_seq_length() - start
        if n_drop > 0:
            cache.crop(-n_drop)
        t = random.uniform(1e-3, 1.0)
        masked = torch.rand(block.shape, device=block.device) < t
        masked[0, 0] = False
        if block.shape[1] > 1 and not masked.any():
            masked[0, random.randrange(1, block.shape[1])] = True
        if masked.any():
            set_attention(model, True)
            noisy = torch.where(masked, model.config.mask_token_id, block)
            logits = model(noisy, past_key_values=cache, use_cache=False).logits
            dlm_loss = (F.cross_entropy(logits[masked].float(), block[masked], reduction="sum") / t) / block.shape[1]
        else:
            dlm_loss = torch.zeros((), device=full.device)

        if args.lbd > 0:
            cos = F.cosine_similarity(embed(model, ex["text_view"]).float(), embed(model, ex["code_view"]).float(), dim=0)
            jepa_loss = 1.0 - cos
        else:
            jepa_loss = torch.zeros((), device=full.device)
        return ar_loss, dlm_loss, jepa_loss

    def evaluate(model, phase, cases=None):
        cases = test if cases is None else test[:cases]
        model.eval()
        set_attention(model, True)
        results = {}
        for mode in args.eval_modes.split(","):
            correct = 0
            for i, messages in enumerate(cases):
                prompt = ids_of(render(messages[:2], True))
                cap = -(-args.max_new_tokens // args.block_length) * args.block_length
                torch.cuda.synchronize()
                started = time.perf_counter()
                with torch.no_grad():
                    if mode == "ar":
                        ids, nfe = model.ar_generate(prompt, max_new_tokens=args.max_new_tokens)
                    else:
                        ids, nfe = model.generate(prompt, max_new_tokens=cap, block_length=args.block_length,
                                                  threshold=args.threshold)
                torch.cuda.synchronize()
                generated = ids[0, prompt.shape[1]:].tolist()
                stop_at = next((j for j, t in enumerate(generated) if t in stop_ids), None)
                kept = generated if stop_at is None else generated[:stop_at]
                text = tok.decode(kept, skip_special_tokens=True).strip()
                ok = score(args.dataset, text, messages[2]["content"])
                correct += ok
                append(out / "eval.jsonl", {
                    "schema": RUN_SCHEMA, "phase": phase, "split": split, "mode": mode, "case": i, "output": text,
                    "reference": messages[2]["content"], "exact": ok, "stopped": stop_at is not None,
                    "output_tokens": len(kept), "nfe": nfe, "seconds": time.perf_counter() - started,
                })
            results[mode] = correct / len(cases)
            print(f"[{phase}] {mode}: exact {correct}/{len(cases)}")
        set_attention(model, True)
        return results

    run = {
        "schema": RUN_SCHEMA, "started_at": utc_now(), "model": MODEL, "revision": REVISION,
        "gpu": torch.cuda.get_device_name(0), "data": DATA_URL.format(name=args.dataset + "_{train,test}"),
        "args": vars(args), "eval_split": split, "train_examples": len(train), "eval_examples": len(test),
    }
    run["eval_before"] = None if args.skip_eval_before else evaluate(base, "before", args.eval_before_cases or None)

    model = get_peft_model(base, LoraConfig(r=args.lora_rank, lora_alpha=2 * args.lora_rank,
                                            lora_dropout=0.0, target_modules=LORA_TARGETS))
    inner = model.get_base_model()
    inner.train()
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr)
    torch.cuda.reset_peak_memory_stats()
    order = random.sample(range(len(train)), len(train))

    for step in range(args.steps):
        started = time.perf_counter()
        totals = {"ar": 0.0, "dlm": 0.0, "jepa": 0.0}
        for j in range(args.grad_accum):
            ex = encode_example(train[order[(step * args.grad_accum + j) % len(order)]])
            ar_loss, dlm_loss, jepa_loss = losses(inner, ex)
            loss = (ar_loss + dlm_loss + args.lbd * jepa_loss) / args.grad_accum
            loss.backward()
            totals["ar"] += ar_loss.item() / args.grad_accum
            totals["dlm"] += dlm_loss.item() / args.grad_accum
            totals["jepa"] += jepa_loss.item() / args.grad_accum
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        row = {"step": step + 1, **totals, "seconds": time.perf_counter() - started,
               "peak_gb": torch.cuda.max_memory_allocated() / 2**30}
        append(out / "train_log.jsonl", row)
        print(json.dumps(row))

    run["eval_after"] = evaluate(inner, "after")
    run["peak_gb"] = torch.cuda.max_memory_allocated() / 2**30
    run["finished_at"] = utc_now()
    model.save_pretrained(out / "adapter")
    (out / "run.json").write_text(json.dumps(run, indent=2))
    print(json.dumps({k: run[k] for k in ("eval_before", "eval_after", "peak_gb")}))


if __name__ == "__main__":
    main()
