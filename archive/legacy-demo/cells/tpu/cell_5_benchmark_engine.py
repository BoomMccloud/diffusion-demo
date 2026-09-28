# --- CELL 5 (TPU): PUZZLE-AGNOSTIC WARM BENCHMARK ENGINE FOR TPU ---

import gc
import json
import os
import re
import time
from datetime import datetime, timezone

import numpy as np
import torch

# ---------------------------------------------------------
# PyTorch-XLA & Transformers setup
# ---------------------------------------------------------

try:
    import torch_xla.core.xla_model as xm
    DEVICE = xm.xla_device()
    IS_TPU = True
    print(f"✅ Using TPU device: {DEVICE}")
except Exception:
    DEVICE = torch.device("cpu")
    IS_TPU = False
    print("⚠️ torch_xla not found. Falling back to CPU.")

from transformers import AutoModelForCausalLM, AutoProcessor, AutoTokenizer

try:
    from transformers import DiffusionGemmaForBlockDiffusion
    HAS_DIFFUSION_CLASS = True
except ImportError:
    DiffusionGemmaForBlockDiffusion = AutoModelForCausalLM
    HAS_DIFFUSION_CLASS = False


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

AR_MODEL_ID = globals().get("AR_MODEL_ID", "google/gemma-4-26B-A4B-it")
DIFF_MODEL_ID = globals().get("DIFF_MODEL_ID", "google/diffusiongemma-26B-A4B-it")

AR_MODEL_PATH = globals().get("AR_MODEL_PATH", AR_MODEL_ID)
DIFF_MODEL_PATH = globals().get("DIFF_MODEL_PATH", DIFF_MODEL_ID)

if "BENCHMARK_SPEC" not in globals():
    try:
        try:
            import cell_4_schedule_puzzle as _cell4
        except ImportError:
            from cells.common import cell_4_schedule_puzzle as _cell4
        BENCHMARK_SPEC = _cell4.BENCHMARK_SPEC
    except Exception:
        raise RuntimeError("BENCHMARK_SPEC is missing. Run Cell 4 before Cell 5.")

SPEC = BENCHMARK_SPEC
PUZZLE_CASES = SPEC["cases"]
PUZZLE_CASE_BY_ID = SPEC["case_by_id"]
BUILD_PROMPT = SPEC["build_prompt"]
PARSE_OUTPUT = SPEC["parse_output"]
EVALUATE_OUTPUT = SPEC["evaluate_output"]
RENDER_OUTPUT = SPEC["render"]
PUZZLE_NAME = SPEC["name"]
PUZZLE_SLUG = SPEC["slug"]

BENCHMARK_MAX_TOKENS = int(
    globals().get(
        "PUZZLE_OUTPUT_TOKENS",
        SPEC.get("default_output_tokens", 512),
    )
)
BENCHMARK_TEMPERATURE = float(globals().get("BENCHMARK_TEMPERATURE", 0.8))
BENCHMARK_TIMEOUT_SECONDS = int(
    globals().get("BENCHMARK_TIMEOUT_SECONDS", 3 * 60)
)
BENCHMARK_BASE_SEED = int(globals().get("BENCHMARK_BASE_SEED", 20260814))

DRIVE_ROOT = globals().get(
    "DRIVE_ROOT", "/content/drive/MyDrive/diffusiongemma-demo"
)
RESULTS_DIR = os.path.join(DRIVE_ROOT, "benchmark-results", PUZZLE_SLUG)
os.makedirs(RESULTS_DIR, exist_ok=True)

WARM_RUNTIMES = bool(globals().get("WARM_RUNTIMES", True))


# ---------------------------------------------------------
# Result construction and metrics
# ---------------------------------------------------------

def clean_text(value):
    if not isinstance(value, str):
        return ""
    text = re.sub(r"\x1B\[[0-9;]*[A-Za-z]", "", value)
    return text.replace("\r", "")


def extract_thought_and_final(text):
    if not isinstance(text, str):
        return "", ""
    thought_match = re.search(r"<\|channel\>thought\n?(.*?)<channel\|>", text, re.DOTALL)
    thought = thought_match.group(1).strip() if thought_match else ""
    final = re.sub(r"<\|channel\>thought\n?.*?<channel\|>", "", text, flags=re.DOTALL).strip()
    return thought, final


def make_result(
    model_name,
    case,
    attempt,
    raw_output,
    load_seconds=0.0,
    response_seconds=0.0,
    compute_seconds=0.0,
    output_tokens=None,
    error=None,
):
    output_text = clean_text(raw_output)
    thought, final_text = extract_thought_and_final(output_text)
    eval_input = final_text if final_text else output_text

    parsed = PARSE_OUTPUT(eval_input) if not error else None
    evaluation = (
        EVALUATE_OUTPUT(case, parsed)
        if parsed is not None
        else {
            "valid": False,
            "status": f"Error: {error}" if error else "Could not parse output",
            "metrics": {},
            "display_value": None,
        }
    )

    quality_key = SPEC.get("primary_quality_metric")
    optimal_key = SPEC.get("optimal_quality_metric")
    metrics = evaluation.get("metrics", {})

    image = RENDER_OUTPUT(
        case,
        evaluation,
        title=f"{model_name} · {case['case_id']}",
    )

    return {
        "model": model_name,
        "case_id": case["case_id"],
        "attempt": attempt,
        "valid": bool(evaluation.get("valid", False)),
        "status": evaluation.get("status", "Unknown"),
        "load_seconds": load_seconds,
        "response_seconds": response_seconds,
        "compute_seconds": compute_seconds,
        "output_tokens": output_tokens,
        "thought": thought,
        "metrics": metrics,
        "quality_value": metrics.get(quality_key) if quality_key else None,
        "optimal_quality_value": (
            metrics.get(optimal_key) if optimal_key else None
        ),
        "raw_output": output_text,
        "parsed_output": parsed,
        "display_value": evaluation.get("display_value"),
        "image": image,
    }


def serializable_result(result):
    return {
        key: value
        for key, value in result.items()
        if key != "image" and not isinstance(value, np.ndarray)
    }


# ---------------------------------------------------------
# TPU Model Management & Warm Runtimes
# ---------------------------------------------------------

_TPU_AR_MODEL = None
_TPU_AR_PROCESSOR = None
_TPU_DIFF_MODEL = None
_TPU_DIFF_PROCESSOR = None


def acquire_ar_tpu_runtime():
    global _TPU_AR_MODEL, _TPU_AR_PROCESSOR
    if _TPU_AR_MODEL is not None and _TPU_AR_PROCESSOR is not None:
        return _TPU_AR_MODEL, _TPU_AR_PROCESSOR, 0.0

    started = time.perf_counter()
    print(f"Loading AR model ({AR_MODEL_PATH}) on TPU...")
    processor = AutoProcessor.from_pretrained(AR_MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(
        AR_MODEL_PATH,
        torch_dtype=torch.bfloat16,
    ).to(DEVICE)
    model.eval()
    if IS_TPU:
        xm.mark_step()
    load_time = time.perf_counter() - started

    if WARM_RUNTIMES:
        _TPU_AR_MODEL = model
        _TPU_AR_PROCESSOR = processor

    return model, processor, load_time


def acquire_diff_tpu_runtime():
    global _TPU_DIFF_MODEL, _TPU_DIFF_PROCESSOR
    if _TPU_DIFF_MODEL is not None and _TPU_DIFF_PROCESSOR is not None:
        return _TPU_DIFF_MODEL, _TPU_DIFF_PROCESSOR, 0.0

    started = time.perf_counter()
    print(f"Loading DiffusionGemma model ({DIFF_MODEL_PATH}) on TPU...")
    processor = AutoProcessor.from_pretrained(DIFF_MODEL_PATH)
    model = DiffusionGemmaForBlockDiffusion.from_pretrained(
        DIFF_MODEL_PATH,
        torch_dtype=torch.bfloat16,
    ).to(DEVICE)
    model.eval()
    if IS_TPU:
        xm.mark_step()
    load_time = time.perf_counter() - started

    if WARM_RUNTIMES:
        _TPU_DIFF_MODEL = model
        _TPU_DIFF_PROCESSOR = processor

    return model, processor, load_time


def release_runtimes():
    global _TPU_AR_MODEL, _TPU_AR_PROCESSOR, _TPU_DIFF_MODEL, _TPU_DIFF_PROCESSOR
    _TPU_AR_MODEL = None
    _TPU_AR_PROCESSOR = None
    _TPU_DIFF_MODEL = None
    _TPU_DIFF_PROCESSOR = None
    gc.collect()


# ---------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------

def run_ar_case_tpu(case, attempt):
    model, processor, load_sec = acquire_ar_tpu_runtime()
    prompt = BUILD_PROMPT(case)
    messages = [
        {
            "role": "system",
            "content": (
                "Return only the requested JSON. Do not output analysis, "
                "reasoning, Markdown, or explanations."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    started = time.perf_counter()
    try:
        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(DEVICE)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=BENCHMARK_MAX_TOKENS,
                temperature=BENCHMARK_TEMPERATURE,
                do_sample=BENCHMARK_TEMPERATURE > 0,
            )
            if IS_TPU:
                xm.mark_step()

        elapsed = time.perf_counter() - started
        generated_ids = outputs[0][inputs["input_ids"].shape[1] :]
        output_text = processor.decode(generated_ids, skip_special_tokens=False)

        return make_result(
            "Gemma 4 AR",
            case,
            attempt,
            output_text,
            load_sec,
            elapsed,
            elapsed,
            len(generated_ids),
        )
    except Exception as error:
        elapsed = time.perf_counter() - started
        return make_result(
            "Gemma 4 AR",
            case,
            attempt,
            "",
            load_sec,
            elapsed,
            0.0,
            error=error,
        )


def run_diff_case_tpu(case, attempt):
    model, processor, load_sec = acquire_diff_tpu_runtime()
    prompt = BUILD_PROMPT(case)
    messages = [{"role": "user", "content": prompt}]

    started = time.perf_counter()
    try:
        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(DEVICE)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=BENCHMARK_MAX_TOKENS,
            )
            if IS_TPU:
                xm.mark_step()

        elapsed = time.perf_counter() - started
        generated_ids = outputs[0][inputs["input_ids"].shape[1] :]
        output_text = processor.decode(generated_ids, skip_special_tokens=False)

        return make_result(
            "DiffusionGemma",
            case,
            attempt,
            output_text,
            load_sec,
            elapsed,
            elapsed,
            len(generated_ids),
        )
    except Exception as error:
        elapsed = time.perf_counter() - started
        return make_result(
            "DiffusionGemma",
            case,
            attempt,
            "",
            load_sec,
            elapsed,
            0.0,
            error=error,
        )


# ---------------------------------------------------------
# Single Demo & Benchmark Suite
# ---------------------------------------------------------

def run_single_demo(case_id, attempt=1):
    case = PUZZLE_CASE_BY_ID[case_id]

    ar_result = run_ar_case_tpu(case, attempt)
    diff_result = run_diff_case_tpu(case, attempt)

    summary = (
        f"### {case_id} Results (TPU)\n\n"
        f"- **AR Model**: {'✅ Valid' if ar_result['valid'] else '❌ Invalid'} "
        f"({ar_result['response_seconds']:.2f}s, {ar_result['output_tokens']} tokens)\n"
        f"- **DiffusionGemma**: {'✅ Valid' if diff_result['valid'] else '❌ Invalid'} "
        f"({diff_result['response_seconds']:.2f}s, {diff_result['output_tokens']} tokens)\n"
    )
    return ar_result, diff_result, summary


def run_benchmark_suite(case_count=10, attempts=1):
    cases_to_run = PUZZLE_CASES[:case_count]
    all_results = []

    for case in cases_to_run:
        for attempt in range(1, attempts + 1):
            all_results.append(run_ar_case_tpu(case, attempt))
            all_results.append(run_diff_case_tpu(case, attempt))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    result_filename = f"suite_tpu_{PUZZLE_SLUG}_{timestamp}.json"
    result_path = os.path.join(RESULTS_DIR, result_filename)

    serializable = [serializable_result(r) for r in all_results]
    with open(result_path, "w") as f:
        json.dump(serializable, f, indent=2)

    # Compute summary rows
    rows = []
    for model_name in ("Gemma 4 AR", "DiffusionGemma"):
        model_results = [r for r in all_results if r["model"] == model_name]
        total = len(model_results)
        valid_count = sum(1 for r in model_results if r["valid"])
        avg_resp = np.mean([r["response_seconds"] for r in model_results]) if model_results else 0.0
        avg_tok = np.mean([r["output_tokens"] or 0 for r in model_results]) if model_results else 0.0

        rows.append({
            "model": model_name,
            "attempts": total,
            "success_rate": valid_count / total if total else 0.0,
            "optimal_rate": 0.0,
            "avg_latency": f"{avg_resp:.2f}s",
            "avg_tokens": f"{avg_tok:.1f}",
        })

    summary_text = (
        f"### TPU Benchmark Suite Finished ({case_count} cases, {attempts} attempts)\n\n"
        f"Results saved to: `{result_path}`"
    )

    return all_results, summary_text, rows, result_path


print("✅ Cell 5 (TPU): Warm benchmark engine for TPU is ready")
