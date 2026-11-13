# LLM-JEPA smoke test image for the DGX Spark (GB10, arm64, CUDA 13).
# NGC PyTorch ships GB10 (sm_121) kernels; transformers and peft go on top.
#
# Build and run from the repo root on the Spark:
#   docker build -t jepa:0.1 -f bench/jepa/Dockerfile bench/jepa
#   docker run --rm --gpus all --ipc=host -v "$PWD":/work -w /work \
#     -v "$HOME/.cache/huggingface":/root/.cache/huggingface jepa:0.1 \
#     python bench/jepa/smoke.py --out runs/jepa-smoke --steps 50 --lbd 0.5
FROM nvcr.io/nvidia/pytorch:26.10-py3
RUN pip install --no-cache-dir "transformers>=5,<6" "peft>=0.17" accelerate
