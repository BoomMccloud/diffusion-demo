# Clover local model and Spark comparison

Tests whether local Clover GGUF weights load and compares local decoding with Qwen on the DGX Spark.

## Contents

- [dllm-inhouse/README.md](dllm-inhouse/README.md): Spark workspace guide for
  the native Clover build, converted weights, running APIs and repetition tests.

- [clover_gguf](code/clover_gguf): code; stored at `bench/clover_gguf`.
- [clover-gguf-2026-11-12](results/clover-gguf-2026-11-12): results; stored at `bench/results/clover-gguf-2026-11-12`.
- [clover-vs-qwen36-spark-2026-11-12](results/clover-vs-qwen36-spark-2026-11-12): results; stored at `bench/results/clover-vs-qwen36-spark-2026-11-12`.
- [clover_gguf_llamacpp_findings.md](findings/clover_gguf_llamacpp_findings.md): findings; stored at `docs/clover_gguf_llamacpp_findings.md`.
- [clover_vs_qwen36_spark_findings.md](findings/clover_vs_qwen36_spark_findings.md): findings; stored at `docs/clover_vs_qwen36_spark_findings.md`.

These links point to the original files, so existing commands and imports continue
to use their documented paths. Some result or download links refer to local,
untracked files and may be absent in another checkout. See the linked findings
or source README for methods, run status, and limitations before interpreting
results. Running model experiments may require the Spark, dependencies, and
credentials; this folder does not itself launch an experiment.
