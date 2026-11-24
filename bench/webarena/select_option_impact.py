"""Find tasks whose select_option calls carried a list encoded as a string.

Run inside the agent container: python select_option_impact.py /results/<study> /analysis/tasks.jsonl
"""

import glob
import gzip
import pickle
import re
import sys
from multiprocessing import Pool

import pandas as pd

study, tasks_path = sys.argv[1], sys.argv[2]
r = pd.read_csv(sorted(glob.glob(f"{study}/result_df_trial_*.csv"))[-1])
r["task"] = r["env.task_name"].str.split(".").str[1].astype(int)
BAD = re.compile(r"select_option\(.*options=['\"]\[")


def scan(exp_dir):
    n_select = n_bad = 0
    for f in glob.glob(f"{exp_dir}/step_*.pkl.gz"):
        try:
            a = pickle.load(gzip.open(f)).action or ""
        except Exception:
            continue
        if a.startswith("select_option"):
            n_select += 1
            n_bad += bool(BAD.search(a))
    return n_select, n_bad


with Pool(24) as p:
    counts = p.map(scan, r.exp_dir)
r["n_select"], r["n_bad_select"] = zip(*counts)
t = pd.read_json(tasks_path, lines=True).merge(r[["task", "n_select", "n_bad_select"]], on="task")
hit = t[t.n_bad_select > 0]
print("tasks with any select_option:", int((t.n_select > 0).sum()))
print("tasks with a string-encoded list:", len(hit), "| passed:", int(hit.ok.sum()), "| failed:", int((~hit.ok).sum()))
print("failed and hit, by site:", hit[~hit.ok].sites.value_counts().to_dict())
print("failed and hit, capped:", int(hit[~hit.ok].capped.sum()))
print("pass rate, tasks with select_option but never malformed:",
      round(t[(t.n_select > 0) & (t.n_bad_select == 0)].ok.mean(), 3))
