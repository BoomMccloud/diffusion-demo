"""Run the public WorkBuddy Office benchmark against the configured API."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from bench.api_preflight import route


DATASET = "datasets/wb-bench-office-v1.0/tasks"
SMOKE_TASK = "ticket-weekly-L3-010"
CODEBUDDY_VERSION = "2.109.3"
HARNESS = f"codebuddy-code/{CODEBUDDY_VERSION}"
HARNESS_IMAGE = f"workbuddy-bench/harness/codebuddy-code:{CODEBUDDY_VERSION}"


def scored_tasks(results):
    scored = set()
    for path in results.glob("*/*/result.json"):
        trial = json.loads(path.read_text())
        rewards = (trial.get("verifier_result") or {}).get("rewards")
        output_tokens = (trial.get("agent_result") or {}).get("n_output_tokens")
        if not trial.get("exception_info") and rewards and (output_tokens or rewards.get("reward", 0) > 0):
            scored.add(trial["task_name"].rsplit("/", 1)[-1])
    return scored


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path, help="path to the pinned Tencent WorkBuddy checkout")
    parser.add_argument("--run", required=True, help="unique name for the upstream job and results")
    tasks = parser.add_mutually_exclusive_group()
    tasks.add_argument("--task", action="append", help="Office task slug. Defaults to the weekly-ticket smoke.")
    tasks.add_argument("--all", action="store_true", help="run all 50 Office tasks")
    parser.add_argument("--dry-run", action="store_true", help="resolve the job without model calls or Docker")
    parser.add_argument("--context-window", type=int, default=110_000, help="CodeBuddy compaction threshold")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.run):
        parser.error("--run must use lowercase letters, digits, and hyphens.")
    if args.context_window <= 8192:
        parser.error("--context-window must leave room above the 8,192-token output cap.")
    try:
        base_url, _, model = route()
    except ValueError as exc:
        parser.error(str(exc))

    root = args.checkout.resolve()
    launcher = root / "scripts/run.sh"
    harness_config = root / f"configs/harnesses/codebuddy-code/versions/{CODEBUDDY_VERSION}.yaml"
    if not launcher.is_file() or not harness_config.is_file():
        parser.error("Set up the pinned WorkBuddy checkout and CodeBuddy configuration first.")
    dataset = root / DATASET
    if not dataset.is_dir():
        parser.error("Fetch the upstream Office dataset with scripts/dataset/fetch-dataset.sh office.")
    names = args.task or [SMOKE_TASK]
    if not args.all:
        for name in names:
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", name) or not (dataset / name / "task.toml").is_file():
                parser.error(f"Office task is missing: {name}")

    slug = f"hosted-office-{args.run}"
    job_path = root / f"configs/jobs/{slug}.yaml"
    model_path = root / f"configs/models/{slug}.yaml"
    job = {
        "model": slug,
        "harness": HARNESS,
        "dataset": DATASET,
        "harness_backend": "local",
        "model_connection": "local_proxy",
        "extra_allowed_hosts": ["host.docker.internal"],
        "n_attempts": 1,
        "context_window": args.context_window,
        "harness_params_override": {"CBC_MAX_TURNS": 48},
        "orchestrator_override": {"n_concurrent_trials": 1},
        "llm_judge_override": {"enabled": False},
        "task_selection": {"mode": "all"} if args.all else {"mode": "name", "names": names},
    }
    model_config = {"model": {
        "name": model, "protocols": ["openai"], "backend_url_env": "BENCH_API_BASE_URL",
        "backend_key_env": "BENCH_API_KEY", "max_concurrent": 1,
        "params": {"temperature": 0.0, "max_output_tokens": 8192, "thinking_enabled": True},
    }}
    for path, config in ((model_path, model_config), (job_path, job)):
        serialized = json.dumps(config, indent=2) + "\n"
        if path.exists() and path.read_text() != serialized:
            parser.error(f"{path.name} has different settings. Pick a fresh run name.")
        path.write_text(serialized)

    bash = shutil.which("bash")
    if not bash or subprocess.run([bash, "-c", "(( BASH_VERSINFO[0] >= 4 ))"]).returncode:
        parser.error("Put Bash 4 or newer on PATH before running WorkBuddy.")
    run = ["uv", "run", "--locked", bash]
    env = {
        **os.environ, "BENCH_API_BASE_URL": base_url, "AUTO_BUILD_HARNESS_MOUNT": "0",
        "SHARDS": "1", "SHARD_CONCURRENCY": "1",
    }
    command = [*run, str(launcher), "--job", slug]
    if args.dry_run:
        command.append("--dry-run")
    else:
        docker = shutil.which("docker")
        if not docker:
            parser.error("Install Docker Engine and Docker Compose before the live run.")
        ready = subprocess.run([docker, "info"], stdout=subprocess.DEVNULL)
        compose = subprocess.run(
            [docker, "compose", "version", "--short"],
            text=True, stdout=subprocess.PIPE,
        )
        if ready.returncode or compose.returncode:
            parser.error("Start Docker and verify that its Compose plugin is available.")
        compose_version = re.match(r"v?(\d+)\.(\d+)", compose.stdout.strip())
        if not compose_version or tuple(map(int, compose_version.groups())) < (2, 35):
            parser.error("WorkBuddy needs Docker Compose 2.35 or newer.")
        api = subprocess.run(
            [docker, "version", "--format", "{{.Server.APIVersion}}"],
            text=True, stdout=subprocess.PIPE,
        )
        version = re.fullmatch(r"(\d+)\.(\d+)", api.stdout.strip())
        if api.returncode or not version or tuple(map(int, version.groups())) < (1, 48):
            parser.error("WorkBuddy needs Docker server API 1.48 or newer for the CodeBuddy image mount.")
        image = subprocess.run(
            [docker, "image", "inspect", HARNESS_IMAGE],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if image.returncode:
            # WorkBuddy's nested build script uses /bin/bash, which is Bash 3 on macOS.
            build = root / "scripts/harness/build-harness-mounts.sh"
            result = subprocess.run([*run, str(build), "--harness", HARNESS], cwd=root, env=env)
            if result.returncode:
                return result.returncode
    result = subprocess.run(command, cwd=root, env=env)
    if result.returncode or args.dry_run:
        return result.returncode
    expected = {p.name for p in dataset.iterdir() if (p / "task.toml").is_file()} if args.all else set(names)
    missing = expected - scored_tasks(root / "results" / slug)
    if missing:
        print("Missing scored model rollouts for " + ", ".join(sorted(missing)), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
