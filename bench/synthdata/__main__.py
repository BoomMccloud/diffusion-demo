"""python -m bench.synthdata {generate,judge,score,all,audit} --run NAME [--smoke]"""
import argparse, asyncio, dataclasses, datetime, json, subprocess
from pathlib import Path

from . import arms, audit, generate, judge, metrics
from .config import FULL, SMOKE

RESULTS = Path(__file__).resolve().parents[1] / "results"


def main():
    p = argparse.ArgumentParser(prog="python -m bench.synthdata")
    p.add_argument("stage", choices=["generate", "judge", "score", "all", "audit"])
    p.add_argument("--run", required=True, help="run name; output goes to bench/results/synthdata-<run>/")
    p.add_argument("--smoke", action="store_true", help="tiny grid to check the pipeline end to end")
    p.add_argument("--score-labels", action="store_true", help="audit: score the labelled CSVs")
    p.add_argument("--tasks", nargs="+", choices=["narrative", "record"], help="judge/score only these formats")
    p.add_argument("--modes", nargs="+", choices=["open", "seeded"], help="judge/score only these prompting modes")
    p.add_argument("--tag", default="", help="score: suffix for metrics/summary files, e.g. early")
    p.add_argument("--judge-concurrency", type=int, help="judge: concurrent requests (default from config)")
    p.add_argument("--skip", nargs="+", default=[], metavar="TASK:MODE:ARM:TEMP",
                   help="cells to leave out of generation and scoring; recorded in the manifest")
    a = p.parse_args()
    cfg = SMOKE if a.smoke else FULL
    if a.tasks or a.modes:
        cfg = dataclasses.replace(cfg, tasks=tuple(a.tasks or cfg.tasks), modes=tuple(a.modes or cfg.modes))
    if a.judge_concurrency:
        cfg = dataclasses.replace(cfg, judge_concurrency=a.judge_concurrency)
    if a.skip:
        skip = tuple((t, m, arm, float(tp)) for t, m, arm, tp in (s.split(":") for s in a.skip))
        cfg = dataclasses.replace(cfg, skip=skip)
    run_dir = RESULTS / f"synthdata-{a.run}"
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = run_dir / "manifest.json"
    if a.stage in ("generate", "all") and not manifest.exists():
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        manifest.write_text(json.dumps({
            "started": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "git_commit": commit, "smoke": a.smoke, "config": dataclasses.asdict(cfg),
            "arms": arms.fingerprint()}, ensure_ascii=False, indent=1, default=list))

    if cfg.skip and manifest.exists():
        m = json.loads(manifest.read_text())
        dev = m.setdefault("deviations", [])
        entry = {"skip": [list(s) for s in cfg.skip]}
        if entry not in [{"skip": d.get("skip")} for d in dev]:
            dev.append({**entry, "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")})
            manifest.write_text(json.dumps(m, ensure_ascii=False, indent=1, default=list))

    gen, jud = run_dir / "generations.jsonl", run_dir / "judgments.jsonl"
    if a.stage in ("generate", "all"):
        asyncio.run(generate.run(cfg, gen))
    if a.stage in ("judge", "all"):
        asyncio.run(judge.run(cfg, gen, jud))
    if a.stage in ("score", "all"):
        metrics.score(cfg, run_dir, a.tag)
    if a.stage == "audit":
        audit.score(run_dir) if a.score_labels else audit.export(cfg, run_dir)


if __name__ == "__main__":
    main()
