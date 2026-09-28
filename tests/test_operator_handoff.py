from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
HANDOFF = REPO_ROOT / "docs" / "operator_handoff.md"


class OperatorHandoffContractTest(unittest.TestCase):
    def test_one_handoff_entry_point_carries_the_current_operator_state(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        bench_readme = (REPO_ROOT / "bench" / "README.md").read_text(encoding="utf-8")

        self.assertIn("[Operator handoff](docs/operator_handoff.md)", readme)
        self.assertIn("[operator handoff](docs/operator_handoff.md)", agents.lower())
        self.assertIn("[operator handoff](../docs/operator_handoff.md)", bench_readme.lower())
        self.assertTrue(HANDOFF.is_file(), "missing the human-facing operator handoff")

        handoff = HANDOFF.read_text(encoding="utf-8")
        for heading in (
            "## Verified state",
            "## Evidence still missing",
            "## Before allocating an A100",
            "## A100 setup order",
            "## Prepare gate",
            "## Diffusion run",
            "## Resume, inspect, and stop",
            "## Where development resumes",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, handoff)

        required_facts = (
            "No real business-screen result exists yet.",
            "v4_sm_80_nvcc_12_8_src_daca8075d871_harness_v2",
            "cells/nvidia/cell_2_runner_setup.py",
            "format-v3",
            '"status":"launch_ready"',
            '"generation_rpc_calls":0',
            "run-diffusion",
            '"stop_reason":"all_cases_completed"',
            "matching Gemma autoregressive business phase is not implemented",
        )
        for fact in required_facts:
            with self.subTest(fact=fact):
                self.assertIn(fact, handoff)

        for relative in (
            "AGENTS.md",
            "bench/README.md",
            "bench/business_benchmark.py",
            "bench/diffusion_runtime.py",
            "cells/common/cell_3_model_setup.py",
            "cells/nvidia/cell_2_runner_setup.py",
            "docs/workload_hypotheses.md",
        ):
            with self.subTest(path=relative):
                self.assertTrue((REPO_ROOT / relative).is_file())
                self.assertIn(f"`{relative}`", handoff)


if __name__ == "__main__":
    unittest.main()
