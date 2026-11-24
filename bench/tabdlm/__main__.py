"""python -m bench.tabdlm {generate,judge,score,all} --run NAME

Few-shot structured-data consistency on TabDLM's ProfileBio and Amazon data. See README.md.
"""
import argparse, asyncio, dataclasses, datetime, json, subprocess
from dataclasses import dataclass
from pathlib import Path

from bench.synthdata import arms
from . import data, run, metrics, tasks

RESULTS = Path(__file__).resolve().parents[1] / "results"


@dataclass(frozen=True)
class Config:
    arms: tuple = ("dllm", "qwen")
    # Each model at its best temperature in the 2026-10-20 synthdata run.
    temps: tuple = (("dllm", 0.6), ("qwen", 1.0))
    datasets: tuple = tasks.DATASETS
    settings: tuple = tasks.SETTINGS
    n: int = 20
    max_tokens: tuple = ((("amazon", "gen1"), 1024), (("amazon", "gen10"), 8192), (("amazon", "extract"), 256),
                         (("bio", "gen1"), 768), (("bio", "gen10"), 6144), (("bio", "extract"), 256))
    concurrency: int = 8
    judge_model: str = "gemini-3.8-flash"
    judge_concurrency: int = 8


def main():
    p = argparse.ArgumentParser(prog="python -m bench.tabdlm")
    p.add_argument("stage", choices=["generate", "judge", "score", "all"])
    p.add_argument("--run", required=True, help="output goes to bench/results/tabdlm-<run>/")
    p.add_argument("--n", type=int, help="requests per cell and arm (default 20)")
    a = p.parse_args()
    cfg = Config() if not a.n else dataclasses.replace(Config(), n=a.n)
    run_dir = RESULTS / f"tabdlm-{a.run}"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = run_dir / "manifest.json"
    if a.stage in ("generate", "all") and not manifest.exists():
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        manifest.write_text(json.dumps({
            "started": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "git_commit": commit, "config": dataclasses.asdict(cfg), "arms": arms.fingerprint(),
            "data": data.sources()}, ensure_ascii=False, indent=1, default=list))
    gen, jud = run_dir / "generations.jsonl", run_dir / "judgments.jsonl"
    if a.stage in ("generate", "all"):
        asyncio.run(run.generate(cfg, gen))
    if a.stage in ("judge", "all"):
        asyncio.run(run.judge(cfg, gen, jud))
    if a.stage in ("score", "all"):
        metrics.score(cfg, run_dir)


if __name__ == "__main__":
    main()
