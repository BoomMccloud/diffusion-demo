# AR versus diffusion decoding on realistic workloads

This repository compares autoregressive and diffusion decoding on work people
actually send to a model: extraction from messy text, code and document edits,
short free-form answers, and agent tool-call loops.

`AGENTS.md` is the authoritative status record and defines the four workloads.
`bench/README.md` explains how to run the model runtimes in Docker on the DGX Spark.
`experiments/workbuddy/` contains the Clover WorkBuddy evidence and comparison plan.

For Spark model, build and benchmark locations, see the [Spark workspace guide](docs/spark-workspace.md).

## Layout

```text
diffusion-demo/
├── AGENTS.md                 # Current objective, workloads, controls
├── bench/
│   ├── gemma_runtimes.py     # Gemma AR (llama-cpp-python) and DiffusionGemma session
│   ├── diffusion_runtime.py  # Resident DiffusionGemma worker, loopback API
│   ├── nemotron_runner.py    # Nemotron ar / linear_spec / diffusion, OpenRouter AR
│   └── native/               # Pinned llama.cpp patch, build, CUDA probes
├── docs/                     # Findings from earlier runs
├── experiments/              # Start here for an index of experiments
│   └── workbuddy/            # Clover WorkBuddy evidence and planned comparisons
├── downloads/                # Downloaded benchmark data and supporting files
├── models/                   # Local model-related files
├── packages/                 # CLI package handoff snapshot
├── go-live/                  # Model launch materials
├── tests/                    # Runner and native contract tests
└── archive/                  # Superseded demos
```

The [experiment index](experiments/README.md) explains each project and links
its code, findings, and results from one folder. Older files remain at their
original paths so existing commands keep working; experiment folders link to
them. Some downloaded data and run artifacts exist only locally or on the DGX
Spark. `docs/` also includes marketing material. The standalone Clover CLI is
maintained in the separate repository named in `AGENTS.md`.

## Local checks

Use a Python environment with NumPy and the OpenAI Python SDK.

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -t . -p 'test*.py'
```

These are offline. They check runner process handling and transcript parsing,
not model quality or accelerator behavior.
