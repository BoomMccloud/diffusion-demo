#!/usr/bin/env python3
"""Apply the benchmark patch to exactly the pinned llama.cpp checkout.

Reads pristine pinned blobs, so rerunning never stacks instrumentation. Existing
modified versions are retained once as .pre-benchmark-v2 files. Build separately
with cmake --build build --target llama-diffusion-cli -j8.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
PIN = 'daca8075d871483545dd85d58ce11970b304b541'
HERE = Path(__file__).resolve().parent


def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError(f'Pinned source mismatch: expected {count} occurrences of {old[:100]!r}, got {text.count(old)}')
    return text.replace(old, new)


def cli_patch(s):
    s = '#include "benchmark_trace.h"\n' + s
    s = replace(s, '    auto print_progress_bar =', '    if (benchmark_trace::cancelled) return false;\n    if (benchmark_trace::enabled() && !benchmark_trace::diagnostic()) return true;\n\n    auto print_progress_bar =')
    s = replace(s, '    auto trim_canvas =', '    benchmark_trace::init();\n    auto trim_canvas =')
    # With the prefix-KV cache and incremental prefill, only prefill chunks and the 256-token canvas pass
    # through one ubatch, so keep the requested ubatch instead of growing it (and its logits buffer) to n_ctx.
    s = replace(s, '        params.n_ubatch = std::max(params.n_ubatch, needed);', '        if (!(benchmark_trace::incremental_prefill() && params.diffusion.eb_kv_cache == 1)) {\n            params.n_ubatch = std::max(params.n_ubatch, needed);\n        }')
    # The canvas is written at [prefix, prefix + canvas_length), which can exceed a decoupled ubatch.
    s = replace(s, '    std::vector<llama_token> output_tokens(params.n_ubatch);', '    std::vector<llama_token> output_tokens(std::max(params.n_ubatch, params.n_ctx));')
    s = replace(s, '        const int32_t max_ub   = std::min((int32_t) params.n_ubatch, (int32_t) llama_n_ctx(ctx));', '        const int32_t max_ub   = (benchmark_trace::incremental_prefill() && params.diffusion.eb_kv_cache == 1)\n                                     ? (int32_t) llama_n_ctx(ctx)\n                                     : std::min((int32_t) params.n_ubatch, (int32_t) llama_n_ctx(ctx));')
    s = replace(s, '        for (size_t i = 0; i + 1 < cut; i++) {', '        if (benchmark_trace::enabled()) return cut;  // Repeated values are legitimate output.\n        for (size_t i = 0; i + 1 < cut; i++) {')
    s = replace(s, '        const int n_input = (int) prefix.size();', '        benchmark_trace::begin();\n        const int n_input = (int) prefix.size();')
    s = replace(s, '            LOG_ERR("error: input too long', '            benchmark_trace::reason = "input_limit";\n            LOG_ERR("error: input too long')
    s = replace(s, '            if (max_length > max_ub) {', '            if (benchmark_trace::cancelled) break;\n            if (max_length > max_ub) {\n                benchmark_trace::reason = "context_limit";')
    s = replace(s, '            int32_t n_generated = 0;\n            if (use_eb)', '            benchmark_trace::block = b;\n            benchmark_trace::event("block_start", ",\\"prefix_tokens\\":" + std::to_string(prefix_len) + ",\\"max_length\\":" + std::to_string(max_length));\n            const double block_start = benchmark_trace::now();\n            int32_t n_generated = 0;\n            if (use_eb)')
    s = replace(s, '            if (n_generated <= prefix_len) {', '            benchmark_trace::event("block_end", ",\\"duration_seconds\\":" + std::to_string(benchmark_trace::now() - block_start));\n            if (benchmark_trace::cancelled) break;\n            if (n_generated <= prefix_len) {\n                benchmark_trace::reason = "generation_error";')
    s = replace(s, '            response.insert(response.end(), canvas, canvas + cut);', '''            response.insert(response.end(), canvas, canvas + cut);
            benchmark_trace::event("commit", ",\\"tokens\\":" + std::to_string(cut) + ",\\"committed_tokens\\":" + std::to_string(response.size()));
            const std::string committed = common_detokenize(vocab, response, false);
            if (!thought_seen && committed.find("<|channel>thought") != std::string::npos) {
                thought_seen = true; benchmark_trace::event("channel", ",\\"channel\\":\\"thought\\",\\"observed_at_commit\\":true");
            }
            if (!final_seen && committed.find("<channel|>") != std::string::npos) {
                final_seen = true; benchmark_trace::event("channel", ",\\"channel\\":\\"final\\",\\"observed_at_commit\\":true");
            }
            if (benchmark_trace::diagnostic()) {
                std::string ids = ",\\"token_ids\\":[";
                for (size_t i = 0; i < cut; ++i) { if (i) ids += ","; ids += std::to_string(canvas[i]); }
                benchmark_trace::event("canvas", ids + "]");
            }''')
    s = replace(s, '        std::vector<llama_token> response;', '        std::vector<llama_token> response;\n        bool thought_seen = false, final_seen = false;')
    s = replace(s, '                break;  // end token or repetition loop: answer complete', '                benchmark_trace::reason = "eog";\n                break;  // Native EOG when benchmark repetition trimming is disabled.')
    s = replace(s, '        const int64_t turn_us =', '        benchmark_trace::stop();\n        const int64_t turn_us =')
    s = replace(s, '                printf("\\n> ");', '                benchmark_trace::event("ready");\n                printf("\\n> ");')
    return s


def diffusion_patch(s):
    s = '#include "benchmark_trace.h"\n' + s
    s = replace(s, 'const int32_t U = std::max(1, (int32_t) llama_n_ubatch(ctx));', 'const int32_t U = benchmark_trace::prefill_chunk(std::max(1, (int32_t) llama_n_ubatch(ctx)));\n        const int32_t reuse = benchmark_trace::prefill_reuse(input_tokens, n_input);\n        // Size the store for the whole context once so it never reallocates (and loses) the reused prefix.\n        const int32_t store_P = benchmark_trace::incremental_prefill() ? std::max(n_input, (int32_t) llama_n_ctx(ctx)) : n_input;')
    s = replace(s, '        bool prefill_ok = true;', '        benchmark_trace::event("prefill_start", ",\\"prefix_tokens\\":" + std::to_string(n_input) + ",\\"reused_tokens\\":" + std::to_string(reuse) + ",\\"chunk_limit\\":" + std::to_string(U));\n        const double prefill_start = benchmark_trace::now();\n        bool prefill_ok = true;')
    s = replace(s, '        for (int32_t s = 0; s < n_input && prefill_ok; s += U) {', '        for (int32_t s = reuse; s < n_input && prefill_ok; s += U) {')
    s = replace(s, 'llama_diffusion_set_phase(model, /*PKV_PREFILL=*/1, n_input, /*off=*/s);', 'llama_diffusion_set_phase(model, /*PKV_PREFILL=*/1, store_P, /*off=*/s);')
    s = replace(s, '                prefill_ok = false;\n            }\n        }', '                prefill_ok = false;\n            } else {\n                benchmark_trace::prefill_done(input_tokens, s + u);\n            }\n        }')
    s = replace(s, '            const int32_t u = std::min(U, n_input - s);', '            if (benchmark_trace::cancelled) { prefill_ok = false; break; }\n            const int32_t u = std::min(U, n_input - s);')
    s = replace(s, '        if (!prefill_ok) {', '        benchmark_trace::event("prefill_end", ",\\"duration_seconds\\":" + std::to_string(benchmark_trace::now() - prefill_start));\n        if (!prefill_ok) {')
    s = replace(s, '    for (int32_t cur_step = S; cur_step >= 1 && !finished; --cur_step) {', '    const double denoise_start = benchmark_trace::now();\n    benchmark_trace::event("denoise_start");\n    for (int32_t cur_step = S; cur_step >= 1 && !finished && !benchmark_trace::cancelled; --cur_step) {')
    s = replace(s, '    if (params.kv_cache) {\n        llama_diffusion_set_phase(model, /*PKV_UNIFIED=*/0, 0, 0);  // restore default', '    benchmark_trace::event("denoise_end", ",\\"duration_seconds\\":" + std::to_string(benchmark_trace::now() - denoise_start));\n    if (params.kv_cache) {\n        llama_diffusion_set_phase(model, /*PKV_UNIFIED=*/0, 0, 0);  // restore default')
    return s


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('checkout', type=Path)
    args = p.parse_args()
    root = args.checkout.resolve()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if head != PIN:
        raise ValueError(f'Expected {PIN}, got {head}')
    manifest = {'upstream_commit': PIN, 'protocol': 2, 'sources': {}}
    for relative, patch in [('examples/diffusion/diffusion-cli.cpp', cli_patch), ('examples/diffusion/diffusion.cpp', diffusion_patch)]:
        source = subprocess.check_output(['git', 'show', f'{PIN}:{relative}'], cwd=root, text=True)
        path = root / relative
        backup = path.with_suffix(path.suffix + '.pre-benchmark-v2')
        if not backup.exists(): backup.write_bytes(path.read_bytes())
        result = patch(source)
        if path.read_text() != result: path.write_text(result)
        manifest['sources'][relative] = hashlib.sha256(result.encode()).hexdigest()
    header = root / 'examples/diffusion/benchmark_trace.h'
    if not header.exists() or header.read_bytes() != (HERE/'benchmark_trace.h').read_bytes():
        header.write_bytes((HERE/'benchmark_trace.h').read_bytes())
    manifest['sources']['examples/diffusion/benchmark_trace.h'] = hashlib.sha256(header.read_bytes()).hexdigest()
    softcap = root/'ggml/src/ggml-cuda/softcap.cu'
    pristine = subprocess.check_output(['git', 'show', f'{PIN}:ggml/src/ggml-cuda/softcap.cu'], cwd=root, text=True)
    repaired = replace(pristine, 'const int k', 'const int64_t k', 2)
    repaired = replace(repaired, 'const int i = blockDim.x*blockIdx.x + threadIdx.x;', 'const int64_t i = int64_t(blockDim.x)*blockIdx.x + threadIdx.x;')
    repaired = replace(repaired, 'const int num_blocks =', 'const int64_t num_blocks =')
    backup = softcap.with_suffix('.cu.pre-benchmark-v2')
    if not backup.exists(): backup.write_bytes(softcap.read_bytes())
    if softcap.read_text() != repaired: softcap.write_text(repaired)
    manifest['sources']['ggml/src/ggml-cuda/softcap.cu'] = hashlib.sha256(softcap.read_bytes()).hexdigest()
    (root/'benchmark-v2-build.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest))

if __name__ == '__main__': main()
