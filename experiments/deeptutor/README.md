# DeepTutor with Clover

The original macOS smoke used DeepTutor 1.7.3 and two Clover servers on the
DGX Spark. The [Clover runtime notes](../clover-gguf/dllm-inhouse/README.md)
cover the server builds and model artifacts. This directory contains the
reusable local adapter and prompt-cache probe.

## Repeat the prompt-cache comparison

With the 128K servers running, forward the Spark's loopback ports 18082
(self-speculative) and 18083 (autoregressive) to local ports 18182 and
18183. Use your own Spark login.

```sh
ssh -N -o ExitOnForwardFailure=yes \
  -L 18182:127.0.0.1:18082 -L 18183:127.0.0.1:18083 USER@SPARK_HOST
```

From the repository root, in another shell:

```sh
python3 experiments/deeptutor/verify_prompt_cache.py
python3 experiments/deeptutor/verify_prompt_cache.py --source-in-user
```

Each command emits JSONL for initial requests, exact replays, a changed
question, and a cache-disabled control. Compare the server's cached token
counts by mode and prompt layout. Prior results are summarized in the root
[AGENTS.md](../../AGENTS.md).

## Repeat the text-only chat

Install DeepTutor 1.7.3 separately. With `aiohttp` available, run
`python3 experiments/deeptutor/self-trial/text_only.py`. Configure the
DeepTutor OpenAI-compatible route to use `http://127.0.0.1:18185/v1` and
model `clover`. The adapter forwards to the self-speculative server on
local port 18182, forces greedy decoding, and omits thinking and native
tools. The alternative `greedy.py` on port 18184 was used for a separate
trial. The original smoke used loopback services and had no embeddings
configured.
