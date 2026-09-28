from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class RepositoryLayoutTest(unittest.TestCase):
    def test_active_files_tests_and_archive_are_separated(self):
        active = (
            "bench/business_benchmark.py",
            "bench/business_fixtures.py",
            "bench/dependency_density_bench.py",
            "bench/diffusion_runtime.py",
            "cells/common/cell_3_model_setup.py",
            "cells/nvidia/cell_2_runner_setup.py",
            "docs/business_dependency_benchmark_cases.md",
            "docs/workload_hypotheses.md",
        )
        for relative in active:
            with self.subTest(active=relative):
                self.assertTrue((REPO_ROOT / relative).is_file())

        maintained_tests = (
            "tests/bench/test_business_fixtures.py",
            "tests/bench/test_dependency_density_bench.py",
            "tests/bench/test_diffusion_runtime.py",
            "tests/native/test_native_stopping.py",
            "tests/native/test_softcap_boundary.py",
        )
        for relative in maintained_tests:
            with self.subTest(test=relative):
                self.assertTrue((REPO_ROOT / relative).is_file())

        archived = (
            "archive/legacy-demo/cells/colab_bootstrap.py",
            "archive/legacy-demo/lab/cell_opt_lab.py",
            "archive/legacy-demo/run_terminal_suite.py",
            "archive/legacy-demo/bench/micro_bench.py",
            "archive/README.md",
        )
        for relative in archived:
            with self.subTest(archived=relative):
                self.assertTrue((REPO_ROOT / relative).is_file())

        for relative in ("lab", "run_terminal_suite.py", "bench/micro_bench.py"):
            with self.subTest(removed_from_active_tree=relative):
                self.assertFalse((REPO_ROOT / relative).exists())

        self.assertFalse(list(REPO_ROOT.rglob("__pycache__")))
        self.assertFalse(list((REPO_ROOT / "bench" / "results").rglob("*.tar.gz")))
        self.assertFalse(
            (REPO_ROOT / "bench/results/dependency-density/2026-09-07/evidence/dependency-tokenizer").exists()
        )
        # Artifact bundles are local-only (one exceeds GitHub's file size
        # limit), so a fresh clone has none. Check their layout only when present.
        bundles = REPO_ROOT / "archive" / "artifact-bundles"
        if bundles.exists():
            self.assertTrue(list(bundles.rglob("*.tar.gz")))
            self.assertTrue(
                (bundles / "bench/results/dependency-density/2026-09-07/evidence/dependency-tokenizer").is_file()
            )


if __name__ == "__main__":
    unittest.main()
