# --- CELL 2 (NVIDIA): CUDA RUNTIMES AND DIFFUSIONGEMMA RUNNER SETUP ---

import importlib.metadata
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys

import torch
from google.colab import drive


# ---------------------------------------------------------
# 1. Install or reuse the prebuilt CUDA llama-cpp-python wheel
# ---------------------------------------------------------

LLAMA_CPP_VERSION = "0.3.34"
LLAMA_CPP_WHEEL_INDEX = (
    "https://abetlen.github.io/llama-cpp-python/whl/cu124"
)

try:
    installed_version = importlib.metadata.version("llama-cpp-python")
except importlib.metadata.PackageNotFoundError:
    installed_version = None

if installed_version != LLAMA_CPP_VERSION:
    print("Installing the prebuilt llama-cpp-python CUDA wheel...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            f"llama-cpp-python=={LLAMA_CPP_VERSION}",
            "--extra-index-url",
            LLAMA_CPP_WHEEL_INDEX,
            "--only-binary=:all:",
            "--no-cache-dir",
        ],
        check=True,
    )
else:
    print(
        f"Using installed llama-cpp-python {installed_version}."
    )

from llama_cpp import llama_cpp

system_info = llama_cpp.llama_print_system_info().decode()
print(system_info)

if "CUDA" not in system_info.upper():
    raise RuntimeError(
        "llama-cpp-python is installed without CUDA support. "
        "Restart the Colab runtime, then rerun this cell."
    )

print("✅ llama-cpp-python CUDA support detected")


# ---------------------------------------------------------
# 2. Check Google Drive Mount
# ---------------------------------------------------------

if os.path.ismount("/content/drive"):
    DRIVE_ROOT = globals().get("DRIVE_ROOT", "/content/drive/MyDrive/diffusiongemma-demo")
    print("✅ Google Drive mounted at /content/drive")
else:
    DRIVE_ROOT = globals().get("DRIVE_ROOT", "/content/diffusiongemma-demo")
    print("ℹ️ Google Drive not mounted; using fast local NVMe storage at /content")
RUNNER_DRIVE_ROOT = os.path.join(DRIVE_ROOT, "diffusion-runner")

# Cell 5 always uses this stable local path. Cell 2 selects the
# correct architecture-specific Drive build and copies it here.
RUNNER_LOCAL_PATH = "/content/llama-diffusion-cli"
TOKENIZER_LOCAL_PATH = "/content/dependency-tokenizer"

# This is temporary Colab storage. Removing it does not touch
# the GGUF files stored in Google Drive.
SOURCE_DIR = "/content/llama.cpp-diffusion"
BUILD_DIR = os.path.join(SOURCE_DIR, "build")

os.makedirs(RUNNER_DRIVE_ROOT, exist_ok=True)


# ---------------------------------------------------------
# 3. Identify the current Colab GPU and CUDA environment
# ---------------------------------------------------------

# Pin the experimental llama.cpp implementation that was verified for this
# notebook. Change this value deliberately when upgrading the runner.
BUILD_FORMAT_VERSION = 3
DIFFUSION_PR_NUMBER = 24423
DIFFUSION_SOURCE_COMMIT = "daca8075d871483545dd85d58ce11970b304b541"

if not torch.cuda.is_available():
    raise RuntimeError(
        "No CUDA GPU is available. Enable a GPU runtime in Colab."
    )

gpu_name = torch.cuda.get_device_name(0)
major, minor = torch.cuda.get_device_capability(0)
cuda_architecture = f"{major}{minor}"
torch_cuda_version = torch.version.cuda or "unknown"

nvcc_output = subprocess.check_output(
    ["nvcc", "--version"],
    text=True,
    stderr=subprocess.STDOUT,
)
nvcc_match = re.search(r"release\s+([0-9]+(?:\.[0-9]+)*)", nvcc_output)

if nvcc_match is None:
    raise RuntimeError(f"Could not determine the nvcc version:\n{nvcc_output}")

nvcc_version = nvcc_match.group(1)

# Keep separate binaries for each GPU compute architecture and CUDA
# version. Examples: sm_75_cuda_12_8, sm_80_cuda_12_8.
nvcc_version_key = re.sub(r"[^0-9A-Za-z]+", "_", nvcc_version).strip("_")
source_key = DIFFUSION_SOURCE_COMMIT[:12]
RUNNER_CACHE_KEY = (
    f"v{BUILD_FORMAT_VERSION}_sm_{cuda_architecture}_nvcc_"
    f"{nvcc_version_key}_src_{source_key}"
)

RUNNER_DRIVE_DIR = os.path.join(
    RUNNER_DRIVE_ROOT,
    RUNNER_CACHE_KEY,
)
RUNNER_DRIVE_PATH = os.path.join(
    RUNNER_DRIVE_DIR,
    "llama-diffusion-cli",
)
RUNNER_METADATA_PATH = os.path.join(
    RUNNER_DRIVE_DIR,
    "build-info.json",
)
TOKENIZER_DRIVE_PATH = os.path.join(RUNNER_DRIVE_DIR, "dependency-tokenizer")

os.makedirs(RUNNER_DRIVE_DIR, exist_ok=True)

print(f"GPU: {gpu_name}")
print(f"CUDA compute architecture: {cuda_architecture}")
print(f"PyTorch CUDA version: {torch_cuda_version}")
print(f"nvcc CUDA toolkit version: {nvcc_version}")
print(f"Runner cache key: {RUNNER_CACHE_KEY}")
print(f"Runner Drive directory: {RUNNER_DRIVE_DIR}")


# ---------------------------------------------------------
# 4. Check for a compatible runner saved in Google Drive
# ---------------------------------------------------------

def sha256_file(path):
    digest = hashlib.sha256()

    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024**2), b""):
            digest.update(chunk)

    return digest.hexdigest()


def metadata_matches_current_environment(metadata):
    return (
        metadata.get("build_format_version") == BUILD_FORMAT_VERSION
        and metadata.get("pull_request") == DIFFUSION_PR_NUMBER
        and metadata.get("source_commit") == DIFFUSION_SOURCE_COMMIT
        and metadata.get("cuda_architecture") == cuda_architecture
        and metadata.get("nvcc_version") == nvcc_version
        and metadata.get("runner_cache_key") == RUNNER_CACHE_KEY
    )


def saved_runner_is_compatible():
    if not os.path.isfile(RUNNER_DRIVE_PATH) or not os.path.isfile(TOKENIZER_DRIVE_PATH):
        return False

    if not os.path.isfile(RUNNER_METADATA_PATH):
        return False

    try:
        with open(RUNNER_METADATA_PATH, "r") as file:
            metadata = json.load(file)

        if not metadata_matches_current_environment(metadata):
            return False

        expected_checksum = metadata.get("sha256")
        tokenizer_checksum = metadata.get("tokenizer_sha256")
        return (
            bool(expected_checksum)
            and bool(tokenizer_checksum)
            and sha256_file(RUNNER_DRIVE_PATH) == expected_checksum
            and sha256_file(TOKENIZER_DRIVE_PATH) == tokenizer_checksum
        )
    except (OSError, ValueError, TypeError):
        return False


def migrate_previous_keyed_runner():
    """Reuse a compatible format-v2 build without recompiling it."""
    if saved_runner_is_compatible():
        return True

    old_cuda_key = re.sub(
        r"[^0-9A-Za-z]+",
        "_",
        torch_cuda_version,
    ).strip("_")
    old_cache_key = f"sm_{cuda_architecture}_cuda_{old_cuda_key}"
    old_directory = os.path.join(RUNNER_DRIVE_ROOT, old_cache_key)
    old_runner = os.path.join(old_directory, "llama-diffusion-cli")
    old_metadata_path = os.path.join(old_directory, "build-info.json")

    if not os.path.isfile(old_runner) or not os.path.isfile(old_metadata_path):
        return False

    try:
        with open(old_metadata_path, "r") as file:
            old_metadata = json.load(file)

        compatible = (
            old_metadata.get("build_format_version") == 2
            and old_metadata.get("pull_request") == DIFFUSION_PR_NUMBER
            and old_metadata.get("source_commit") == DIFFUSION_SOURCE_COMMIT
            and old_metadata.get("cuda_architecture") == cuda_architecture
            and old_metadata.get("pytorch_cuda_version")
            == torch_cuda_version
        )

        if not compatible:
            return False

        print(f"Migrating compatible cached runner from {old_cache_key}...")
        runner_part_path = RUNNER_DRIVE_PATH + ".part"
        metadata_part_path = RUNNER_METADATA_PATH + ".part"
        shutil.copy2(old_runner, runner_part_path)
        os.chmod(runner_part_path, 0o755)

        migrated_metadata = {
            "build_format_version": BUILD_FORMAT_VERSION,
            "pull_request": DIFFUSION_PR_NUMBER,
            "source_commit": DIFFUSION_SOURCE_COMMIT,
            "gpu_name": gpu_name,
            "cuda_architecture": cuda_architecture,
            "pytorch_cuda_version": torch_cuda_version,
            "nvcc_version": nvcc_version,
            "runner_cache_key": RUNNER_CACHE_KEY,
            "sha256": sha256_file(runner_part_path),
        }

        with open(metadata_part_path, "w") as file:
            json.dump(migrated_metadata, file, indent=2)

        os.replace(runner_part_path, RUNNER_DRIVE_PATH)
        os.replace(metadata_part_path, RUNNER_METADATA_PATH)
        print("✅ Previous A100 runner migrated without recompilation")
        return True

    except (OSError, ValueError, TypeError) as error:
        print(f"Previous runner migration skipped: {error}")
        return False


# ---------------------------------------------------------
# 5. Build only when a compatible saved runner is unavailable
# ---------------------------------------------------------

migrate_previous_keyed_runner()

if saved_runner_is_compatible():
    print("✅ Compatible DiffusionGemma runner found in Drive")

else:
    print("No compatible saved runner was found.")
    print("Preparing a shallow DiffusionGemma source checkout...")

    # Only this temporary source/build directory is removed.
    # MODEL_CACHE and /content/gguf_models are not touched.
    if os.path.isdir(SOURCE_DIR):
        shutil.rmtree(SOURCE_DIR)

    os.makedirs(SOURCE_DIR, exist_ok=True)

    subprocess.run(
        ["git", "init", SOURCE_DIR],
        check=True,
    )

    subprocess.run(
        [
            "git",
            "-C",
            SOURCE_DIR,
            "remote",
            "add",
            "origin",
            "https://github.com/ggml-org/llama.cpp.git",
        ],
        check=True,
    )

    subprocess.run(
        [
            "git",
            "-C",
            SOURCE_DIR,
            "fetch",
            "--depth=1",
            "--progress",
            "origin",
            DIFFUSION_SOURCE_COMMIT,
        ],
        check=True,
    )

    subprocess.run(
        [
            "git",
            "-C",
            SOURCE_DIR,
            "checkout",
            "--detach",
            "FETCH_HEAD",
        ],
        check=True,
    )

    source_commit = subprocess.check_output(
        [
            "git",
            "-C",
            SOURCE_DIR,
            "rev-parse",
            "HEAD",
        ],
        text=True,
    ).strip()

    if source_commit != DIFFUSION_SOURCE_COMMIT:
        raise RuntimeError(
            f"Expected source {DIFFUSION_SOURCE_COMMIT}, got {source_commit}."
        )

    print(f"Source commit: {source_commit}")
    print("Configuring the CUDA build...")

    subprocess.run(
        [
            "cmake",
            "-S",
            SOURCE_DIR,
            "-B",
            BUILD_DIR,
            "-DGGML_CUDA=ON",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DLLAMA_CURL=OFF",
            f"-DCMAKE_CUDA_ARCHITECTURES={cuda_architecture}",
            "-DCMAKE_BUILD_TYPE=Release",
        ],
        check=True,
    )

    parallel_jobs = str(max(2, min(8, os.cpu_count() or 4)))
    print(f"Compiling llama-diffusion-cli with {parallel_jobs} parallel jobs. This may take a while...")

    build_command = [
        "cmake",
        "--build",
        BUILD_DIR,
        "--config",
        "Release",
        "--target",
        "llama-diffusion-cli",
        "--parallel",
        parallel_jobs,
    ]

    # Stream combined stdout and stderr line by line so Colab
    # displays CMake, compiler, and linker progress immediately.
    log_path = "/content/build.log"
    print(f"Build output logged to {log_path}...")
    with open(log_path, "w", encoding="utf-8") as log_file:
        build_process = subprocess.Popen(
            build_command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

        last_pct_str = ""
        while build_process.poll() is None:
            time.sleep(3)
            try:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()[-25:]
                    for l in reversed(lines):
                        m = re.search(r"\[\s*(\d+)%\]", l)
                        if m:
                            current_pct_str = m.group(0)
                            if current_pct_str != last_pct_str:
                                last_pct_str = current_pct_str
                                print(f"🔨 {l.strip()}", flush=True)
                            break
            except Exception:
                pass

    build_return_code = build_process.wait()

    if build_return_code != 0:
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                tail = "".join(f.readlines()[-40:])
            print("Build failed. Last 40 lines of log:\n", tail)
        except Exception:
            pass
        raise subprocess.CalledProcessError(
            build_return_code,
            build_command,
        )

    compiled_path = os.path.join(
        BUILD_DIR,
        "bin",
        "llama-diffusion-cli",
    )

    if not os.path.isfile(compiled_path):
        raise FileNotFoundError(
            f"Compiled runner was not found at {compiled_path}"
        )

    tokenizer_source = "/content/dependency-tokenizer.cpp"
    with open(tokenizer_source, "w", encoding="utf-8") as file:
        file.write(r'''#include "llama.h"
#include "chat.h"
#include "common.h"
#include <iostream>
#include <string>
static void quiet(enum ggml_log_level, const char *, void *) {}
int main(int argc,char **argv) {
 if(argc!=2) return 2; llama_log_set(quiet,nullptr); llama_backend_init();
 auto params=llama_model_default_params(); params.vocab_only=true;
 auto *model=llama_model_load_from_file(argv[1],params); if(!model) return 3;
 auto *vocab=llama_model_get_vocab(model); auto templates=common_chat_templates_init(model, "");
 std::string line; while(std::getline(std::cin,line)) {
  bool prompt=line.rfind("p:",0)==0; if(prompt) line=line.substr(2); if(line.size()%2) return 4;
  std::string s; for(size_t i=0;i<line.size();i+=2) s.push_back(static_cast<char>(std::stoi(line.substr(i,2),nullptr,16)));
  if(prompt) { common_chat_msg msg; msg.role="user"; msg.content=s; common_chat_templates_inputs inputs; inputs.messages={msg}; inputs.add_generation_prompt=true; s=common_chat_templates_apply(templates.get(),inputs).prompt; }
  int n=llama_tokenize(vocab,s.data(),s.size(),nullptr,0,prompt,prompt); std::cout << (n<0?-n:n) << std::endl;
 }
 llama_model_free(model); llama_backend_free(); return 0;
}''')

    link_dir = os.path.join(BUILD_DIR, "examples", "diffusion")
    link_args = shlex.split(open(os.path.join(link_dir, "CMakeFiles", "llama-diffusion-cli.dir", "link.txt")).read())
    object_name = "CMakeFiles/llama-diffusion-cli.dir/diffusion-cli.cpp.o"
    link_args[link_args.index(object_name)] = tokenizer_source
    link_args[link_args.index("-o") + 1] = TOKENIZER_LOCAL_PATH
    link_args[1:1] = [
        "-I" + os.path.join(SOURCE_DIR, "include"),
        "-I" + os.path.join(SOURCE_DIR, "common"),
        "-I" + os.path.join(SOURCE_DIR, "vendor"),
        "-I" + os.path.join(SOURCE_DIR, "ggml", "include"),
    ]
    subprocess.run(link_args, cwd=link_dir, check=True)
    os.chmod(TOKENIZER_LOCAL_PATH, 0o755)

    print("Saving the compiled runner to Google Drive...")
    runner_part_path = RUNNER_DRIVE_PATH + ".part"
    tokenizer_part_path = TOKENIZER_DRIVE_PATH + ".part"
    metadata_part_path = RUNNER_METADATA_PATH + ".part"

    shutil.copy2(compiled_path, runner_part_path)
    os.chmod(runner_part_path, 0o755)
    runner_checksum = sha256_file(runner_part_path)
    shutil.copy2(TOKENIZER_LOCAL_PATH, tokenizer_part_path)
    os.chmod(tokenizer_part_path, 0o755)
    tokenizer_checksum = sha256_file(tokenizer_part_path)

    metadata = {
        "build_format_version": BUILD_FORMAT_VERSION,
        "pull_request": DIFFUSION_PR_NUMBER,
        "source_commit": source_commit,
        "gpu_name": gpu_name,
        "cuda_architecture": cuda_architecture,
        "pytorch_cuda_version": torch_cuda_version,
        "nvcc_version": nvcc_version,
        "runner_cache_key": RUNNER_CACHE_KEY,
        "sha256": runner_checksum,
        "tokenizer_sha256": tokenizer_checksum,
    }

    with open(metadata_part_path, "w") as file:
        json.dump(metadata, file, indent=2)

    os.replace(runner_part_path, RUNNER_DRIVE_PATH)
    os.replace(tokenizer_part_path, TOKENIZER_DRIVE_PATH)
    os.replace(metadata_part_path, RUNNER_METADATA_PATH)

    print("✅ Compiled runner saved to Google Drive")


# ---------------------------------------------------------
# 6. Copy the saved runner to fast local Colab storage
# ---------------------------------------------------------

shutil.copy2(RUNNER_DRIVE_PATH, RUNNER_LOCAL_PATH)
os.chmod(RUNNER_LOCAL_PATH, 0o755)
shutil.copy2(TOKENIZER_DRIVE_PATH, TOKENIZER_LOCAL_PATH)
os.chmod(TOKENIZER_LOCAL_PATH, 0o755)

if not os.path.isfile(RUNNER_LOCAL_PATH):
    raise FileNotFoundError(
        "Failed to copy the DiffusionGemma runner locally."
    )

print(f"✅ Local runner ready: {RUNNER_LOCAL_PATH}")
print(f"✅ Local tokenizer ready: {TOKENIZER_LOCAL_PATH}")
print(f"Loaded cached build: {RUNNER_CACHE_KEY}")


# ---------------------------------------------------------
# 7. Verify that the saved executable starts
# ---------------------------------------------------------

verification = subprocess.run(
    [RUNNER_LOCAL_PATH, "--version"],
    capture_output=True,
    text=True,
    timeout=60,
)

version_output = (
    verification.stdout.strip()
    or verification.stderr.strip()
)

print(version_output[:2000])

if verification.returncode != 0:
    raise RuntimeError(
        "The DiffusionGemma runner was copied, but its startup "
        f"verification failed with code {verification.returncode}."
    )

print("✅ Cell 2 (NVIDIA): CUDA runtimes and DiffusionGemma runner ready")
