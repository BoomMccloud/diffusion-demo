# --- CELL 3 (NVIDIA): MODEL STORAGE, DOWNLOAD, AND LOCAL STAGING ---

import os
import shutil

import torch
from google.colab import drive
from huggingface_hub import hf_hub_download
from tqdm.auto import tqdm


# ---------------------------------------------------------
# Persistent and local storage
# ---------------------------------------------------------

if os.path.ismount("/content/drive"):
    DRIVE_ROOT = globals().get("DRIVE_ROOT", "/content/drive/MyDrive/diffusiongemma-demo")
    print("✅ Google Drive mounted at /content/drive")
else:
    DRIVE_ROOT = globals().get("DRIVE_ROOT", "/content/diffusiongemma-demo")
    print("ℹ️ Google Drive not mounted; using fast local NVMe storage at /content")
MODEL_CACHE = os.path.join(DRIVE_ROOT, "huggingface_cache")
LOCAL_MODEL_DIR = "/content/gguf_models"
LOCAL_SAFETY_MARGIN_GIB = 2

os.makedirs(MODEL_CACHE, exist_ok=True)
os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)


# ---------------------------------------------------------
# Exact model artifacts
# ---------------------------------------------------------

AR_REPO = "unsloth/gemma-4-26B-A4B-it-GGUF"
AR_GGUF = "gemma-4-26B-A4B-it-UD-Q4_K_M.gguf"

DIFF_REPO = "unsloth/diffusiongemma-26B-A4B-it-GGUF"
DIFF_GGUF = "diffusiongemma-26B-A4B-it-Q4_K_M.gguf"

MODELS_TO_STAGE = {"ar", "diffusion"}
unknown_models = MODELS_TO_STAGE - {"ar", "diffusion"}
if unknown_models or not MODELS_TO_STAGE:
    raise ValueError(
        "MODELS_TO_STAGE must contain 'ar', 'diffusion', or both. "
        f"Received: {sorted(MODELS_TO_STAGE)}"
    )

# Set to True only if you want to copy the 15-30 GiB models to local NVMe.
# Default False loads directly from Drive cache into GPU VRAM (saving 2-5+ min).
STAGE_MODELS_LOCALLY = bool(
    globals().get("STAGE_MODELS_LOCALLY", False)
)


# ---------------------------------------------------------
# Runtime and storage diagnostics
# ---------------------------------------------------------

if not torch.cuda.is_available():
    raise RuntimeError(
        "No CUDA GPU is available. Select Runtime > Change runtime type "
        "in Colab, then choose a GPU."
    )

DEVICE = "cuda"
GPU_NAME = torch.cuda.get_device_name(0)
GPU_MAJOR, GPU_MINOR = torch.cuda.get_device_capability(0)
GPU_ARCHITECTURE = f"{GPU_MAJOR}{GPU_MINOR}"
GPU_VRAM_GIB = torch.cuda.get_device_properties(0).total_memory / 1024**3
FULL_GPU_OFFLOAD = GPU_VRAM_GIB >= 32.0
DEFAULT_GPU_LAYERS = 99 if FULL_GPU_OFFLOAD else 16


def format_gib(byte_count):
    return f"{byte_count / 1024**3:.2f} GiB"


def show_storage():
    gib = 1024**3
    local_total, local_used, local_free = shutil.disk_usage("/content")
    print(
        f"Colab local: {local_free / gib:.1f} GiB free, "
        f"{local_used / gib:.1f} GiB used"
    )
    drive_path = "/content/drive/MyDrive"
    if os.path.isdir(drive_path):
        drive_total, drive_used, drive_free = shutil.disk_usage(drive_path)
        print(
            f"Google Drive: {drive_free / gib:.1f} GiB free, "
            f"{drive_used / gib:.1f} GiB used"
        )


print(f"GPU: {GPU_NAME}")
print(f"CUDA compute architecture: {GPU_ARCHITECTURE}")
print(f"GPU VRAM: {GPU_VRAM_GIB:.1f} GiB")
print(f"Full GPU offload expected: {FULL_GPU_OFFLOAD}")
print(f"Persistent cache: {MODEL_CACHE}")
print(f"Fast local directory: {LOCAL_MODEL_DIR}")
show_storage()


# ---------------------------------------------------------
# Resolve each model in the persistent Hugging Face cache
# ---------------------------------------------------------

def get_drive_model(repo_id, filename):
    print(f"\nChecking persistent cache for {filename}...")
    path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        cache_dir=MODEL_CACHE,
    )
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Expected model file was not created: {path}")
    size = os.path.getsize(path)
    if size <= 0:
        raise RuntimeError(f"Cached model file is empty: {path}")
    print(f"✅ Persistent copy ready: {format_gib(size)}")
    print(path)
    return path


AR_DRIVE_PATH = (
    get_drive_model(AR_REPO, AR_GGUF)
    if "ar" in MODELS_TO_STAGE
    else None
)
DIFF_DRIVE_PATH = (
    get_drive_model(DIFF_REPO, DIFF_GGUF)
    if "diffusion" in MODELS_TO_STAGE
    else None
)

if STAGE_MODELS_LOCALLY:
    model_sources = []
    if AR_DRIVE_PATH:
        model_sources.append(
            (AR_DRIVE_PATH, os.path.join(LOCAL_MODEL_DIR, AR_GGUF))
        )
    if DIFF_DRIVE_PATH:
        model_sources.append(
            (DIFF_DRIVE_PATH, os.path.join(LOCAL_MODEL_DIR, DIFF_GGUF))
        )

    # ---------------------------------------------------------
    # Capacity check before either large local copy starts
    # ---------------------------------------------------------

    required_bytes = 0
    reclaimable_bytes = 0
    for source_path, target_path in model_sources:
        partial_path = target_path + ".part"
        if os.path.isfile(partial_path):
            print(f"Removing stale partial copy: {partial_path}")
            os.remove(partial_path)

        source_size = os.path.getsize(source_path)
        if os.path.isfile(target_path):
            target_size = os.path.getsize(target_path)
            if target_size == source_size:
                continue
            reclaimable_bytes += target_size
        required_bytes += source_size

    local_free_bytes = shutil.disk_usage("/content").free
    safety_bytes = LOCAL_SAFETY_MARGIN_GIB * 1024**3
    effective_free_bytes = local_free_bytes + reclaimable_bytes
    if effective_free_bytes < required_bytes + safety_bytes:
        raise RuntimeError(
            "Not enough local Colab storage to stage the requested models.\n"
            f"Copies required: {format_gib(required_bytes)}\n"
            f"Effective free space: {format_gib(effective_free_bytes)}\n"
            f"Safety margin: {LOCAL_SAFETY_MARGIN_GIB} GiB\n"
            "Delete unneeded files under /content and rerun Cell 3. Persistent "
            "Drive copies will be reused."
        )

    # ---------------------------------------------------------
    # Copy once per Colab runtime to fast local disk
    # ---------------------------------------------------------

    def stage_model_locally(source_path, filename):
        target_path = os.path.join(LOCAL_MODEL_DIR, filename)
        partial_path = target_path + ".part"
        source_size = os.path.getsize(source_path)

        if (
            os.path.isfile(target_path)
            and os.path.getsize(target_path) == source_size
        ):
            print(f"\n✅ Local copy already ready: {target_path}")
            return target_path

        for stale_path in (partial_path, target_path):
            if os.path.isfile(stale_path):
                os.remove(stale_path)

        print(f"\nCopying {filename} from Drive to local Colab storage...")
        chunk_size = 16 * 1024**2
        with (
            open(source_path, "rb") as source_file,
            open(partial_path, "wb") as target_file,
            tqdm(
                total=source_size,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=filename,
            ) as progress,
        ):
            while True:
                chunk = source_file.read(chunk_size)
                if not chunk:
                    break
                target_file.write(chunk)
                progress.update(len(chunk))
            target_file.flush()
            os.fsync(target_file.fileno())

        copied_size = os.path.getsize(partial_path)
        if copied_size != source_size:
            os.remove(partial_path)
            raise RuntimeError(
                f"Incomplete local copy for {filename}: expected {source_size} "
                f"bytes, copied {copied_size} bytes."
            )
        os.replace(partial_path, target_path)
        print(f"✅ Local copy ready: {format_gib(copied_size)}")
        print(target_path)
        return target_path

    AR_MODEL_PATH = (
        stage_model_locally(AR_DRIVE_PATH, AR_GGUF)
        if AR_DRIVE_PATH else None
    )
    DIFF_MODEL_PATH = (
        stage_model_locally(DIFF_DRIVE_PATH, DIFF_GGUF)
        if DIFF_DRIVE_PATH else None
    )
else:
    print("\n⚡ STAGE_MODELS_LOCALLY is False: using Drive cache directly (skipping multi-minute copy).")
    AR_MODEL_PATH = AR_DRIVE_PATH
    DIFF_MODEL_PATH = DIFF_DRIVE_PATH

for label, path in {
    "AR model": AR_MODEL_PATH,
    "Diffusion model": DIFF_MODEL_PATH,
}.items():
    if path is not None and not os.path.isfile(path):
        raise FileNotFoundError(f"{label} was not staged correctly: {path}")

show_storage()
print("\n✅ Cell 3 (NVIDIA): Model configuration complete")
print(f"AR_MODEL_PATH = {AR_MODEL_PATH}")
print(f"DIFF_MODEL_PATH = {DIFF_MODEL_PATH}")
