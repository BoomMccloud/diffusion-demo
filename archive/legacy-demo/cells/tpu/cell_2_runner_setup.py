# --- CELL 2 (TPU): TPU RUNTIME, TORCH-XLA, AND TRANSFORMERS SETUP ---

import importlib.metadata
import os
import subprocess
import sys

from google.colab import drive

# ---------------------------------------------------------
# 1. Mount Google Drive
# ---------------------------------------------------------

drive.mount("/content/drive")

DRIVE_ROOT = globals().get(
    "DRIVE_ROOT",
    "/content/drive/MyDrive/diffusiongemma-demo",
)
os.makedirs(DRIVE_ROOT, exist_ok=True)


# ---------------------------------------------------------
# 2. Install and verify PyTorch-XLA & Transformers dependencies
# ---------------------------------------------------------

REQUIRED_PACKAGES = [
    "transformers>=4.49.0",
    "accelerate>=1.0.0",
    "huggingface_hub[cli]",
    "sentencepiece",
    "protobuf",
]

print("Verifying and installing required packages for TPU inference...")
subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-U",
        *REQUIRED_PACKAGES,
    ],
    check=True,
)


# ---------------------------------------------------------
# 3. Detect and initialize the TPU device
# ---------------------------------------------------------

try:
    import torch
    import torch_xla
    import torch_xla.core.xla_model as xm

    tpu_device = xm.xla_device()
    tpu_type = xm.xla_device_hw(tpu_device)
    print(f"✅ Connected to TPU device: {tpu_device} (Hardware: {tpu_type})")
except Exception as exc:
    print(f"⚠️ torch_xla initialization warning: {exc}")
    print("If running on Colab TPU, ensure 'TPU v5e' or 'TPU v6e' is selected in Runtime > Change runtime type.")
    tpu_device = None

print("✅ Cell 2 (TPU): TPU runtime environment is ready")
