# LLM-JEPA on a diffusion model

Tests whether JEPA training improves Nemotron diffusion decoding compared with autoregressive decoding.

## Contents

- [jepa](code/jepa): code; stored at `bench/jepa`.
- [jepa-smoke-2026-11-12](results/jepa-smoke-2026-11-12): results; stored at `bench/results/jepa-smoke-2026-11-12`.
- [jepa-lbd-pick-2026-11-13](results/jepa-lbd-pick-2026-11-13): results; stored at `bench/results/jepa-lbd-pick-2026-11-13`.
- [jepa-main](results/jepa-main): results; stored at `bench/results/jepa-main`.
- [jepa_diffusion_findings.md](findings/jepa_diffusion_findings.md): findings; stored at `docs/jepa_diffusion_findings.md`.
- [llm_jepa_test_plan.md](findings/llm_jepa_test_plan.md): findings; stored at `docs/llm_jepa_test_plan.md`.

These links point to the original files, so existing commands and imports continue
to use their documented paths. Some result or download links refer to local,
untracked files and may be absent in another checkout. See the linked findings
or source README for methods, run status, and limitations before interpreting
results. Running model experiments may require the Spark, dependencies, and
credentials; this folder does not itself launch an experiment.
