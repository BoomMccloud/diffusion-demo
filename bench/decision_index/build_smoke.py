"""Build a small Decision Index 0.3 smoke sample from pinned public sources.

Rows reproduce the prompts of apolinario/decision-index @f5a6e4f
(suite/build/normalize_direct.py and adapters_added.py) for seven
benchmarks that need no heavy rebuild. Run with:

    uv run --with pyarrow python bench/decision_index/build_smoke.py --per 40
"""

import argparse
import csv
import io
import json
import random
import urllib.request
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
CACHE = HERE / "sources"
HF = "https://huggingface.co/datasets/{repo}/resolve/{rev}/{path}"
GH = "https://raw.githubusercontent.com/{repo}/{rev}/{path}"

SOURCES = {
    "banking77_test": GH.format(repo="PolyAI-LDN/task-specific-datasets", rev="master", path="banking_data/test.csv"),
    "banking77_categories": GH.format(repo="PolyAI-LDN/task-specific-datasets", rev="master", path="banking_data/categories.json"),
    "clinc150": GH.format(repo="clinc/oos-eval", rev="master", path="data/data_full.json"),
    **{f"anli_{r}": HF.format(repo="facebook/anli", rev="8e4813d", path=f"plain_text/test_{r}-00000-of-00001.parquet") for r in ("r1", "r2", "r3")},
    "winogrande": HF.format(repo="allenai/winogrande", rev="01e7417", path="winogrande_xl/validation-00000-of-00001.parquet"),
    "hellaswag": HF.format(repo="Rowan/hellaswag", rev="218ec52", path="data/validation-00000-of-00001.parquet"),
    "mmlu_pro": HF.format(repo="TIGER-Lab/MMLU-Pro", rev="b189ec765aa7ed75c8acfea42df31fdae71f97be", path="data/test-00000-of-00001.parquet"),
    "when2call": HF.format(repo="nvidia/When2Call", rev="0582f7749df63a96fdc3070932e83e72396ace53", path="test/when2call_test_mcq.jsonl"),
}


def fetch(name):
    p = CACHE / (name + "." + SOURCES[name].rsplit(".", 1)[-1])
    if not p.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(SOURCES[name], timeout=300) as r:
            p.write_bytes(r.read())
    return p


def letters(n):
    return [chr(65 + i) if n <= 26 else f"option_{i}" for i in range(n)]


def choice_row(benchmark, source_id, state, instructions, options, gold, key="q1"):
    # Base-suite rows use question key q1; the 0.2 added benchmarks use q.
    keys = letters(len(options))
    return {"id": f"{benchmark}:{source_id}", "benchmark": benchmark, "state": state,
            "questions": {key: {"type": "choice", "instructions": instructions, "criteria": dict(zip(keys, options))}},
            "expected": {key: keys[gold]}}


def banking77():
    data = list(csv.DictReader(io.StringIO(fetch("banking77_test").read_text(encoding="utf-8"))))
    labels = json.loads(fetch("banking77_categories").read_text())
    for i, r in enumerate(data):
        yield choice_row("BANKING77", i, {}, "Classify the banking intent of this user request:\n" + r["text"], labels, labels.index(r["category"]))


def clinc150():
    obj = json.loads(fetch("clinc150").read_text())
    labels = sorted({pair[1] for pair in obj["train"]} | {"oos"})
    desc = ["out of scope: none of the listed intents" if x == "oos" else x.replace("_", " ") for x in labels]
    for split in ("test", "oos_test"):
        for i, (text, label) in enumerate(obj[split]):
            yield choice_row("CLINC150+OOS", f"{split}:{i}", {}, "Classify the intent of this user request, or choose out of scope if none applies:\n" + text, desc, labels.index(label))


def anli():
    names = ["entailment", "neutral", "contradiction"]
    for rnd in ("r1", "r2", "r3"):
        for r in pq.read_table(fetch(f"anli_{rnd}")).to_pylist():
            yield choice_row("ANLI", r["uid"], {}, "Classify the relationship between the premise and hypothesis.\nPremise: " + r["premise"] + "\nHypothesis: " + r["hypothesis"], names, int(r["label"]))


def winogrande():
    for i, r in enumerate(pq.read_table(fetch("winogrande")).to_pylist()):
        yield choice_row("WinoGrande", i, {}, "Which option correctly fills the blank?\n" + r["sentence"], [r["option1"], r["option2"]], int(r["answer"]) - 1)


def hellaswag():
    clean = lambda s: " ".join(str(s).split())
    for i, r in enumerate(pq.read_table(fetch("hellaswag")).to_pylist()):
        yield choice_row("HellaSwag", f"{i}:{r['ind']}", {}, "Which continuation is most plausible?\n" + clean(r["ctx"]), [clean(x) for x in r["endings"]], int(r["label"]))


def mmlu_pro():
    for r in pq.read_table(fetch("mmlu_pro")).to_pylist():
        keys = letters(len(r["options"]))
        yield choice_row("MMLU-Pro", r["question_id"], r["question"], "Which option is the correct answer?", list(r["options"]), keys.index(r["answer"]), key="q")


def when2call():
    order = ["direct", "tool_call", "request_for_info", "cannot_answer"]
    for line in fetch("when2call").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        state = {"tools": [json.loads(t) for t in r["tools"]], "question": r["question"]}
        yield choice_row("When2Call", r["uuid"], state, "Which response should the assistant give to the user's question, given the available tools?", [r["answers"][k] for k in order], order.index(r["correct_answer"]), key="q")


BUILDERS = [banking77, clinc150, anli, winogrande, hellaswag, mmlu_pro, when2call]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20261016)
    ap.add_argument("--out", default=str(HERE / "smoke-rows.jsonl"))
    a = ap.parse_args()
    rows = []
    for build in BUILDERS:
        all_rows = list(build())
        rows += random.Random(f"{a.seed}:{build.__name__}").sample(all_rows, min(a.per, len(all_rows)))
        print(f"{build.__name__}: {len(all_rows)} rows, sampled {min(a.per, len(all_rows))}")
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"wrote {len(rows)} rows to {a.out}")


if __name__ == "__main__":
    main()
