# Google Colab CLI & Terminal Benchmark Runner Findings

**Date:** 2026-09-04  
**Hardware Tested:** NVIDIA A100-SXM4 (40GB & 80GB variants on Google Colab)  
**Environment:** macOS (host client), Ubuntu 22.04 / CUDA 12.8 / Python 3.13 (Colab runtime)  
**Tooling:** `google-colab-cli` v0.6.0 via `uv tool`

---

## 1. Executive Summary

We established headless command-line orchestration with Google Colab via `google-colab-cli`, eliminating dependency on interactive web browser tabs and Gradio interfaces for model benchmarking. 

Key milestones achieved:
1. **Connected & Authenticated**: Configured public OAuth2 PKCE authentication and mapped remote Colab GPU assignments to local CLI sessions.
2. **Upstream Fixes**: Identified and resolved a client dependency issue (`jupyter_kernel_client.KernelClient` attribute mismatch in `google-colab-cli 0.6.0`).
3. **Headless Terminal Runner**: Implemented [`cell_7_terminal_runner.py`](../cells/common/cell_7_terminal_runner.py) and [`run_terminal_suite.py`](../run_terminal_suite.py) to run multi-case, multi-attempt benchmarks with live ASCII summary tables, statistical aggregation, and JSONL/Markdown export.
4. **FUSE & I/O Resilience**: Replaced hanging FUSE filesystem checks with `os.path.ismount()` and buffered compiler output to eliminate `ipykernel` websocket queue saturation.
5. **Cost Safety**: Verified complete session teardown to prevent compute unit leakage when jobs finish.

---

## 2. Colab CLI Mechanics & Operational Findings

### 2.1 Authentication Strategies
- **OAuth2 (Public PKCE)**: The default and most reliable strategy when running without Google Cloud SDK Application Default Credentials (ADC). It generates a one-time Google authorization code prompt and caches tokens at `~/.config/colab-cli/token.json`.
- **ADC Requirement**: The CLI can also use ADC (`--auth=adc`), but requires all four scopes: `openid`, `https://www.googleapis.com/auth/cloud-platform`, `https://www.googleapis.com/auth/userinfo.email`, and `https://www.googleapis.com/auth/colaboratory`.

### 2.2 Server-Side Assignment Discovery & Orphan Adoption
- Assignments created directly in the Colab web interface appear in `colab sessions` with a `[?]` prefix (orphan sessions not yet recorded in local `sessions.json`).
- Server assignments expose `runtime_proxy_info.token` and `runtime_proxy_info.url`. Registering these into `SessionState` allows the CLI to attach directly to an active browser runtime without creating duplicate VMs.

### 2.3 Upstream Bug Identified & Patched
- In `colab_cli/runtime.py:106`, the client instantiates:
  ```python
  self._kernel_client = jupyter_kernel_client.KernelClient(...)
  ```
- In `jupyter-kernel-client >= 1.0.0`, the class was renamed to `JupyterKernelClient`.
- **Fix**: Aliased `jupyter_kernel_client.KernelClient = jupyter_kernel_client.JupyterKernelClient` in the tool environment, restoring `colab exec` functionality.

### 2.4 Execution Timeout Traps
- `colab exec` enforces a default timeout of **30.0 seconds** unless overridden with `--timeout <seconds>`.
- Any command involving package installation, compilation, model downloads, or benchmark execution must pass `--timeout` (e.g. `--timeout 600` or `--timeout 1800`).
- **Prelude Hook Trap**: In `colab_cli/commands/execution.py:175`, `colab exec` runs an unparameterized prelude (`runtime.execute_code("import os; ...")`) which always uses the default 30s timeout. If a previous background task is still saturating the kernel, this prelude times out before user code executes.

### 2.5 Drive Credential Propagation Failure

On 2026-09-07, `colab drivemount` succeeded on a `us-central1` A100 runtime but failed twice on a fresh `asia-southeast1` A100 runtime. In both failed attempts, the Drive credential dry-run requests returned HTTP 200 and the user completed authorization, but the final non-dry-run request to Colab's `credentials-propagation` endpoint returned HTTP 400. DriveFS then timed out with `ValueError: mount failed`.

This signature indicates a Colab credential propagation failure rather than missed user authorization or an insufficient CLI timeout. After two HTTP 400 propagation failures:

1. Stop repeating the same CLI authorization flow.
2. Open the existing runtime with `colab url -s <session>`.
3. From the regular Colab browser interface, run:

   ```python
   from google.colab import drive
   drive.mount("/content/drive", force_remount=True)
   ```

4. If browser-driven mounting also fails, create a fresh runtime, prefer `us-central1` when selectable, and mount Drive before downloading or compiling artifacts.
5. Keep the successfully mounted runtime for the complete benchmark batch so the Drive mount, downloaded model, compiled runner, and loaded GPU state can be reused.

The observed region correlation is diagnostic evidence, not proof that every `asia-southeast1` runtime will fail. The decisive signal is the final credential propagation response: HTTP 200 preceded the successful mount, while HTTP 400 preceded both failed mounts.

---

## 3. Runtime & Build Optimizations

### 3.1 Non-Blocking Google Drive Mount Detection
- **Issue**: Standard Colab scripts frequently call `os.path.isdir("/content/drive/MyDrive")`. When Google Drive is not mounted or pending user authorization, traversing `/content/drive` blocks indefinitely at the FUSE filesystem layer.
- **Resolution**: Updated [`cells/nvidia/cell_2_runner_setup.py`](../cells/nvidia/cell_2_runner_setup.py) and [`cells/common/cell_3_model_setup.py`](../cells/common/cell_3_model_setup.py) to check:
  ```python
  if os.path.ismount("/content/drive"):
      DRIVE_ROOT = "/content/drive/MyDrive/diffusiongemma-demo"
  else:
      DRIVE_ROOT = "/content/diffusiongemma-demo"  # Fast local NVMe fallback
  ```
  This guarantees immediate, non-blocking execution in headless environments.

### 3.2 NVCC & CMake Parallelism
- The upstream runner setup hardcoded `--parallel 2` for standard free Colab runtimes.
- On an A100 GPU instance (with 8–12 vCPUs), this throttled compilation needlessly.
- **Resolution**: Updated to `parallel_jobs = str(max(2, min(8, os.cpu_count() or 4)))`, accelerating compilation time by ~4x.

### 3.3 Websocket Queue Flood Prevention
- Streaming every compiler line over the Jupyter kernel via `print(line, end="", flush=True)` overwhelmed `ipykernel.iostream`'s message loop during high-throughput parallel builds, resulting in `KeyboardInterrupt` / dropped connections.
- **Resolution**: Redirected full compiler output to `/content/build.log` and implemented milestone-based progress logging (emitting percentage updates like `🔨 [XX%]`), keeping websocket traffic minimal and stable.

---

## 4. Terminal Benchmark Architecture

To replace the interactive Gradio web interface, we designed a dedicated CLI benchmark suite:

```
diffusion-demo/
├── run_terminal_suite.py           # Top-level CLI entrypoint
├── cells/
│   ├── colab_bootstrap.py         # Bootstrap pipeline with terminal mode default
│   └── common/
│       ├── cell_7_terminal_runner.py  # Multi-run terminal harness & table renderer
│       └── cell_7_web_ui.py           # Gradio UI with automatic headless delegation
```

### 4.1 Features of `cell_7_terminal_runner.py`
1. **Configurable Test Runs**: Evaluates multiple test cases across repeated trials:
   - `BENCHMARK_CASE_COUNT` (default: 5)
   - `BENCHMARK_ATTEMPTS` (default: 3)
2. **Formatted ASCII Summary Table**: The following illustrates output formatting. No linked raw measurements substantiate these numbers; do not use it as evidence of a successful model run.
   ```text
   ============================================================================
   📊 BENCHMARK RESULTS SUMMARY
   ============================================================================
   +----------------+----------+--------------+--------------+----------------+-------+-------+
   | Model          | Attempts | Success Rate | Optimal Rate | Median Latency |   Min |   Max |
   +----------------+----------+--------------+--------------+----------------+-------+-------+
   | DiffusionGemma |        3 |       100.0% |        66.7% |          0.88s | 0.85s | 0.92s |
   | Gemma 4 AR     |        3 |        66.7% |        33.3% |          1.90s | 1.75s | 2.10s |
   +----------------+----------+--------------+--------------+----------------+-------+-------+

   ⚡ Latency Comparison: DiffusionGemma is 2.16x faster in median response.
   ```
3. **Artifact Persistence**: Outputs structured `.jsonl` data and a companion `_summary.md` report directly to `RESULTS_DIR`.

---

## 5. Lifecycle & Shutdown Verification

- Idle Colab sessions consume compute units continuously until stopped.
- Verified that `colab sessions` queries `https://colab.research.google.com/tun/m/assignments` and confirmed:
  ```text
  [colab] No active sessions found on server.
  ```
- All local session states in `~/.config/colab-cli/sessions.json` have been cleared.
