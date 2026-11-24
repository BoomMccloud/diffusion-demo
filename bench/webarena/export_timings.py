"""Export one WebArena task run's timeline to JSON for make_webarena_race.py.

Runs in the webarena-agent container, since the step pickles need AgentLab.
For each step it writes wall-clock times for the model call (agent_start and
agent_stop) and the browser action (env_start, action_exec_start and stop,
env_stop), plus the model calls logged by run_webarena.py in that window.

Usage (inside the container):
    python /bench/export_timings.py /results/<study>/<task_dir> /results/llm_calls out.json
"""
import json
import sys
from pathlib import Path

from browsergym.experiments.loop import ExpResult


def main():
    exp_dir, calls_dir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    res = ExpResult(exp_dir)
    steps = []
    for i, st in enumerate(res.steps_info):
        p = st.profiling
        steps.append({
            "step": i,
            "action": st.action,
            "agent_start": p.agent_start or None,
            "agent_stop": p.agent_stop or None,
            "env_start": p.env_start or None,
            "action_exec_start": p.action_exec_start or None,
            "action_exec_stop": p.action_exec_stop or None,
            "env_stop": p.env_stop or None,
            "reward": st.reward,
            "terminated": st.terminated,
            "truncated": st.truncated,
        })
    # Step 0 is the reset: its action_exec_start is when the recorded page opened.
    video_t0 = steps[0]["action_exec_start"]
    t_end = max(v for s in steps for k, v in s.items() if k.endswith(("_start", "_stop")) and v)
    calls = []
    for f in sorted(calls_dir.glob("*.jsonl")):
        for line in f.open():
            row = json.loads(line)
            if video_t0 - 5 <= row["time"] <= t_end + 5:
                row["file"] = f.name
                calls.append(row)
    calls.sort(key=lambda r: r["time"])
    videos = sorted(str(p.relative_to(exp_dir)) for p in (exp_dir / "task_video").glob("*.webm"))
    summary = res.summary_info
    json.dump({
        "exp_dir": str(exp_dir),
        # exp_args.pkl needs run_webarena's classes to unpickle; the folder name has the task.
        "task": exp_dir.name.split("_on_")[-1].rsplit("_", 1)[0],
        "goal": (res.steps_info[0].obs or {}).get("goal"),
        "video_t0": video_t0,
        "t_end": t_end,
        "videos": videos,
        "summary": {k: summary.get(k) for k in (
            "n_steps", "cum_reward", "err_msg", "terminated", "truncated",
            "stats.cum_agent_elapsed", "stats.cum_step_elapsed", "stats.cum_input_tokens",
            "stats.cum_output_tokens")},
        "steps": steps,
        "llm_calls": calls,
    }, out.open("w"), indent=1, default=str)
    print(f"{out}: {len(steps)} steps, {len(calls)} calls, videos {videos}")


if __name__ == "__main__":
    main()
