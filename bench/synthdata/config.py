"""Benchmark grid and fixed settings. See README.md for why each value was chosen."""
from dataclasses import dataclass, field, replace

DEPARTMENTS = ["心内科", "呼吸内科", "消化内科", "内分泌科", "肾内科", "神经内科",
               "血液科", "感染科", "普通外科", "骨科", "泌尿外科", "妇产科"]
AGE_BANDS = [(18, 44), (45, 64), (65, 90)]
SEXES = ["男", "女"]


def seed_grid():
    """69 seeds: every department, age band and sex, except male obstetrics."""
    return [{"department": d, "age_lo": lo, "age_hi": hi, "sex": s}
            for d in DEPARTMENTS for lo, hi in AGE_BANDS for s in SEXES
            if not (d == "妇产科" and s == "男")]


@dataclass(frozen=True)
class Config:
    arms: tuple = ("dllm", "qwen")
    temps: tuple = (0.6, 0.8, 1.0, 1.2)
    tasks: tuple = ("narrative", "record")
    modes: tuple = ("open", "seeded")
    replicates: int = 3
    open_n: int = 150
    seed_samples: int = 2
    seeds: tuple = field(default_factory=lambda: tuple(map(lambda s: tuple(s.items()), seed_grid())))
    max_tokens: tuple = (("narrative", 1024), ("record", 512))
    concurrency: int = 8
    judge_model: str = "gemini-3.8-flash"
    judge_concurrency: int = 8
    embed_model: str = "gemini-embedding-001"
    taus: tuple = (0.97, 0.96)
    orderings: int = 20
    vendi_n: int = 40
    # Cells left out of generation and scoring, as (task, mode, arm, temp). Each entry is a deviation
    # from the plan and is printed in summary.md.
    skip: tuple = ()

    def skipped(self, task, mode, arm, temp):
        return (task, mode, arm, temp) in self.skip

    def seed_dicts(self):
        return [dict(s) for s in self.seeds]

    def tokens(self, task):
        return dict(self.max_tokens)[task]


FULL = Config()
SMOKE = replace(FULL, temps=(0.8,), replicates=1, open_n=6, seed_samples=1,
                seeds=FULL.seeds[::12][:6], vendi_n=4)
