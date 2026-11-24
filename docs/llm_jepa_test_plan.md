# LLM-JEPA on a diffusion LM: test plan

2026-11-12

## Question

Does LLM-JEPA fine-tuning help diffusion decoding more than it helps AR decoding? Nothing has been run yet, and as far as we know no one has published LLM-JEPA results on a diffusion model.

Hypothesis: on the same weights, the JEPA arm's accuracy gain over the baseline arm is larger in `diffusion` mode than in `ar` mode. If JEPA helps both modes equally, the hypothesis is false.

We test on Nemotron-Labs-Diffusion-3B because one set of weights decodes in both modes, so a gain can be attributed to the decoding method. Clover (35B-A3B) comes later, and only if this result holds.

## Arms

Every arm is a LoRA fine-tune of the same pretrained model on the same examples. Base weights stay frozen and nothing is trained from scratch. The arms differ only in the loss.

| Arm | Loss | Purpose |
| --- | --- | --- |
| Baseline | AR + diffusion | Reference (`--lbd 0`) |
| JEPA, bidirectional | AR + diffusion + lbd × (1 − cos) | Main test |
| JEPA, causal | Same, views encoded with causal attention | Checks the encoding isn't biased toward diffusion |
| Baseline, same FLOPs | AR + diffusion, more steps | Checks the gain isn't extra compute |

- **AR loss:** next-token cross entropy on the answer, causal attention.
- **Diffusion loss:** one answer block masked and denoised with bidirectional attention, as `generate` decodes.
- **JEPA loss:** the model encodes the prompt and the answer in separate passes and takes one hidden-state vector from each. The loss is 1 − cosine similarity between them. This follows [galilai-group/llm-jepa](https://github.com/galilai-group/llm-jepa) with zero predictor tokens.

At inference all arms decode the same way. The JEPA term only changes the trained adapter weights.

## Decision rule

The hypothesis is supported only if the interaction below is at least 2 points and its 95% CI excludes zero on at least 2 of 3 tasks. Fix this before any run.

```
interaction = (JEPA − base) in diffusion mode − (JEPA − base) in AR mode
```

- Accuracy per task, on the same test cases for every arm and mode.
- CI by bootstrapping over test cases, paired by case, with seeds kept as blocks.
- If the interaction appears with bidirectional encoding but not causal, report it as a weaker claim. If the same-FLOPs baseline matches the JEPA arm, the gain is compute, not JEPA.
- A gain in both modes with no interaction means JEPA helps, but not specifically diffusion.

## Steps

Each step gates the next. Report results before moving on.

1. **Smoke test.** Run `bench/jepa/smoke.py` for 50 steps with `--lbd 0.5` and `--lbd 0`. Pass: fits in memory, JEPA loss falls, `ar` and `diffusion` outputs still stop and parse. Record seconds per step to size step 3.
2. **Pick lbd.** Try 0.5 and 2.0, as the reference repo does, on NL-RX-SYNTH with one seed. Choose on a validation split carved from the training data, never the test set, then freeze it.
3. **Main runs.** 3 arms (baseline, JEPA bidirectional, JEPA causal) × 3 seeds × 3 tasks = 27 runs. Score each in `ar` and `diffusion` mode on the full test sets, plus the untrained model.
4. **Compute control.** One same-FLOPs baseline on NL-RX-SYNTH, 3 seeds.
5. **Mechanism check.** If diffusion gains more, measure whether adjacent-token duplication dropped. That was diffusion's main failure in earlier screens.
6. **Clover.** Only if the rule passes: check whether Clover's BF16 checkpoint has a diffusion training forward. If so, repeat steps 3 and 4 on it.

## Setup

| Item | Choice |
| --- | --- |
| Hardware | DGX Spark (GB10, 121 GB unified memory, arm64, CUDA 13) |
| Software | NVIDIA PyTorch container under podman; transformers ≥ 5, peft. No bitsandbytes, since QLoRA isn't needed at 121 GB. |
| Model | [nvidia/Nemotron-Labs-Diffusion-3B](https://huggingface.co/nvidia/Nemotron-Labs-Diffusion-3B), revision `0d51902`, bf16 |
| Training | LoRA rank 16 on all attention and MLP projections, lr 1e-4, batch 1 with gradient accumulation |
| Tasks | NL-RX-SYNTH, NL-RX-TURK, GSM8K from [llm-jepa](https://github.com/galilai-group/llm-jepa) at `ea0017c` (Apache-2.0); Spider optional later |
| Scoring | Exact match, as in the reference repo's evaluate.py |
| Code | `bench/jepa/smoke.py` (smoke test written, not yet run on a GPU) |

Record per eval row: raw output, reference, exact match, stop reason, output tokens, forward passes, wall time, arm, seed, mode, model revision and GPU. Train in batch 1, because bidirectional mode takes no attention mask and padding would leak into the output.

## Risks and open questions

- **Less headroom for diffusion.** The masked-diffusion loss already learns representations by denoising, so JEPA may help AR more.
- **Wrong granularity.** JEPA aligns one vector per sequence, but diffusion's known failure is local duplication inside a block.
- **Spark throughput.** It has the memory, not the compute. Step time from the smoke test decides whether 27 runs fit the schedule.
- **PyTorch on GB10.** Stock wheels may not support sm_121. Confirm the container before step 1.
- **`linear_spec` mode.** It turns attached LoRA adapters off during verification. Merge the adapter before scoring it, or leave the mode out, since its output matches AR by design.

- [ ] Is 2 points the right minimum effect for these tasks?
- [ ] Do we include Spider, which needs its SQLite databases?
- [ ] Does Clover's BF16 checkpoint have a diffusion training forward?
