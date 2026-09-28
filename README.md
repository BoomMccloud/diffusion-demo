# AR versus diffusion decoding on realistic workloads

This repository compares autoregressive and diffusion decoding on work people
actually send to a model: extraction from messy text, code and document edits,
short free-form answers, and agent tool-call loops.

`AGENTS.md` is the authoritative status record and defines the four workloads.
`bench/README.md` explains how to stage and run each model runtime.

## Layout

```text
diffusion-demo/
├── AGENTS.md                 # Current objective, workloads, controls
├── bench/
│   ├── gemma_runtimes.py     # Gemma AR (llama-cpp-python) and DiffusionGemma session
│   ├── diffusion_runtime.py  # Resident DiffusionGemma worker, loopback API
│   ├── nemotron_runner.py    # Nemotron ar / linear_spec / diffusion, OpenRouter AR
│   └── native/               # Pinned llama.cpp patch, build, CUDA probes
├── cells/                    # Colab model staging and prior runner setup
├── docs/                     # Findings from earlier runs
├── tests/                    # Runner and native contract tests
└── archive/                  # Superseded demos
```

## Local checks

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -t . -p 'test*.py'
```

These are offline. They check runner process handling and transcript parsing,
not model quality or accelerator behavior.
