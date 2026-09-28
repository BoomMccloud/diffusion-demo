import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = REPO_ROOT / "bench" / "dependency_density_bench.py"


class DependencyDensityBenchmarkContractTest(unittest.TestCase):
    def test_selftest_reports_the_complete_deterministic_matrix_contract(self):
        self.assertTrue(
            BENCHMARK.is_file(),
            "missing standalone dependency-density benchmark CLI: "
            f"{BENCHMARK.relative_to(REPO_ROOT)}",
        )

        command = [sys.executable, str(BENCHMARK), "selftest", "--json"]
        first = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        second = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(first.stdout, second.stdout, "selftest output is not deterministic")

        try:
            report = json.loads(first.stdout)
        except json.JSONDecodeError as error:
            self.fail(f"selftest did not emit one JSON report: {error}")

        self.assertEqual(report.get("status"), "ok")
        self.assertEqual(
            report.get("checks"),
            {
                "balanced_conditions": True,
                "canonical_output_enforced": True,
                "deterministic_cases": True,
                "exact_scoring": True,
                "invalid_outputs_retained": True,
                "order_is_seeded_and_balanced": True,
                "paired_contract_equal": True,
                "result_schema_complete": True,
            },
        )

        matrix = report.get("matrix")
        self.assertIsInstance(matrix, list)
        self.assertEqual(len(matrix), 9)
        self.assertEqual(
            {condition.get("dependency_density") for condition in matrix},
            {"direct", "mixed", "chained"},
        )
        self.assertEqual(len({condition.get("output_size") for condition in matrix}), 3)
        case_counts = {condition.get("case_count") for condition in matrix}
        self.assertEqual(len(case_counts), 1)
        self.assertGreater(next(iter(case_counts)), 0)


class DiffusionSessionLifecycleTest(unittest.TestCase):
    """Real pipe/process boundary, using the runner's interactive wire protocol."""

    def setUp(self):
        from bench.dependency_density_bench import DiffusionSession

        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        script = Path(self.directory.name) / "native_protocol.py"
        script.write_text(textwrap.dedent('''\
            import os
            import sys
            import time

            sys.stdout.write("ready\\n> ")
            sys.stdout.flush()
            for request in sys.stdin:
                request = request.strip()
                if request == "crash":
                    os.write(1, b"<|channel>thought\\nunfinished reasoning\\n")
                    os.write(2, b"native fatal: boundary sentinel 37\\n")
                    os._exit(37)
                if request == "hang":
                    sys.stdout.write("<|channel>thought\\nstill generating\\n")
                    sys.stdout.flush()
                    time.sleep(60)
                elif request == "/clear":
                    sys.stdout.write("cleared\\n> ")
                    sys.stdout.flush()
                else:
                    sys.stdout.write('<|channel>thought\\nchecked both values<channel|>{"values":["A","B"]}\\n> ')
                    sys.stdout.flush()
        '''), encoding="utf-8")

        class ProtocolSession(DiffusionSession):
            def command(self):
                return [sys.executable, "-u", str(script)]

            def _write(self, text):
                super()._write(text)
                if text == "crash":
                    # Force the valid scheduling case where the child exits before
                    # the reader resumes. All output still comes from real pipes.
                    self.process.wait(timeout=5)

        self.session = ProtocolSession("unused", "unused", 256, 7, timeout=5)
        self.addCleanup(self.session.close)

    def assert_recovery(self):
        from bench.dependency_density_bench import split_native_response

        self.session.close()
        self.session.timeout = 5
        first = self.session.generate("valid request")
        self.assertEqual(len(first), 4, "generate must preserve its tuple API")
        final, reasoning = split_native_response(first[0])
        self.assertEqual(final, '{"values":["A","B"]}')
        self.assertEqual(reasoning, "checked both values")
        self.assertGreater(first[1], 0)
        recovered_process = self.session.process
        second = self.session.generate("another valid request")
        self.assertEqual(second[0], first[0])
        self.assertIs(self.session.process, recovered_process,
                      "successful turns should reuse the warm process")

    def test_crash_retains_terminal_output_and_recovers(self):
        with self.assertRaises(RuntimeError) as caught:
            self.session.generate("crash")
        # Subtests let recovery execute even when a diagnostic assertion fails.
        with self.subTest("terminal stderr survives exit before pipe drain"):
            self.assertIn("native fatal: boundary sentinel 37", self.session.last_transcript)
        with self.subTest("partial reasoning is retained without a final channel"):
            self.assertIn("unfinished reasoning", self.session.last_transcript)
            self.assertNotIn("<channel|>", self.session.last_transcript)
        with self.subTest("original exit metadata survives"):
            self.assertIn("37", str(caught.exception))
        self.assert_recovery()

    def test_timeout_stops_original_generation_and_recovers(self):
        self.session.start()
        original_process = self.session.process
        self.session.timeout = 0.15
        with self.assertRaises(TimeoutError):
            self.session.generate("hang")
        with self.subTest("timeout acknowledges termination before returning"):
            self.assertIsNotNone(original_process.poll(),
                                 "timed-out native generation is still alive")
        with self.subTest("partial reasoning survives timeout"):
            self.assertIn("still generating", self.session.last_transcript)
        self.assert_recovery()


if __name__ == "__main__":
    unittest.main()
