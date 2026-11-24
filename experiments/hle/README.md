# Humanity’s Last Exam

Runs and diagnoses model responses to HLE questions.

## Run

Follow the [API setup](../../docs/api-experiments.md) with
`DIFFUSION_BASE_URL` and `GEMINI_API_KEY`. This runner uses the historical
diffusion model ID on a route that accepts requests without a bearer key.
Accept the dataset terms for `cais/hle` using your own Hugging Face account.
From the repository root, stage the dataset and judge prompt:

```sh
python -m pip install pyarrow pydantic huggingface_hub
hf auth login
hf download cais/hle data/test-00000-of-00001.parquet --repo-type dataset --local-dir downloads/hle
cp downloads/hle/data/test-00000-of-00001.parquet downloads/hle/test.parquet
git clone https://github.com/centerforaisafety/hle.git downloads/hle/repo
git -C downloads/hle/repo checkout --detach 22ed3074b1e7b134bcbc09028d0ba320839b0655
```

Record the dataset checksum for your run. The original dataset revision is
unrecorded. Start with two text-only questions, then repeat the saved
300-question sampling settings in a separate file:

```sh
run="$(mktemp -d)"
python -m bench.hle.run_hle --n 2 --seed 0 --workers 1 --out "$run/smoke.jsonl"
python -m bench.hle.run_hle --n 300 --seed 0 --max-tokens 131072 --out "$run/hle300.jsonl"
```

Check the smoke's judged rows and final error and truncation counts. The
reported score uses a Gemini judge and a text-only subset. Compare it under
those settings. Reuse an output path to resume and pass `--redo-errors` to
retry request errors.

## Contents

- [hle](code/hle): code; stored at `bench/hle`.
- [hle](results/hle): results; stored at `downloads/hle`.
- [tau2_hle_qwen36_findings.md](findings/tau2_hle_qwen36_findings.md): findings; stored at `docs/tau2_hle_qwen36_findings.md`.

These links point to the original files, so existing commands and imports continue
to use their documented paths. Some result or download links refer to local,
untracked files and may be absent in another checkout. See the linked findings
or source README for methods, run status, and limitations before interpreting
results. Running model experiments may require the Spark, dependencies, and
credentials; this folder does not itself launch an experiment.
