import unittest
from bench import diffusion_runtime as runtime
from bench.dependency_density_bench import make_case


class BusinessPolicyContractTest(unittest.TestCase):
    @staticmethod
    def _business_module():
        import importlib.util
        import os
        from pathlib import Path

        module_path = os.environ.get("DIFFUSION_BUSINESS_BENCHMARK_UNDER_TEST")
        if not module_path:
            from bench import business_benchmark
            return business_benchmark
        spec = importlib.util.spec_from_file_location("bench.business_benchmark_under_test", Path(module_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_hardware_identity_requires_an_available_gpu(self):
        business = self._business_module()
        self.assertTrue(business._valid_hardware_identity("NVIDIA A100-SXM4-80GB, 81920 MiB"))
        for unavailable in (
            "unavailable:nvidia-smi missing",
            "Unavailable: command failed",
            "  unavailable:no GPU  ",
        ):
            with self.subTest(identity=unavailable):
                self.assertFalse(business._valid_hardware_identity(unavailable))

    def test_warmup_acceptance_requires_exact_completed_native_result(self):
        business = self._business_module()
        accepted = {
            "request_state": "completed",
            "raw_output": '{"values":["READY"]}',
            "native_events": [{"event": "stop", "reason": "eog"}],
        }
        self.assertTrue(business._warmup_accepted(accepted))
        rejected = {
            "state": {**accepted, "request_state": "failed"},
            "error": {**accepted, "error": {"type": "RuntimeError"}},
            "output": {**accepted, "raw_output": '{"values":["NOT_READY"]}'},
            "missing_stop": {**accepted, "native_events": []},
            "duplicate_stop": {**accepted, "native_events": accepted["native_events"] * 2},
            "wrong_stop": {**accepted, "native_events": [{"event": "stop", "reason": "block_budget"}]},
        }
        for variant, result in rejected.items():
            with self.subTest(variant=variant):
                self.assertFalse(business._warmup_accepted(result))

    def test_summary_classifies_complete_budget_and_runtime_stops(self):
        business = self._business_module()
        registration_hash = "b" * 64
        completed_rows = [
            {"problem_id": business.fixtures.PROBLEM_IDS[0], "valid": True, "elapsed_seconds": 0.1}
            for _ in range(36)
        ]
        cases = (
            (completed_rows, "all_cases_completed", "completed", 36),
            ([], "insufficient_full_case_budget", "incomplete", 0),
            (completed_rows[:1], "runtime_gate_failed", "incomplete", 1),
        )
        for rows, stop_reason, status, attempts in cases:
            with self.subTest(stop_reason=stop_reason):
                summary = business.summarize(
                    rows,
                    1.0,
                    stop_reason,
                    expected_attempts=36,
                    registration_hash=registration_hash,
                )
                self.assertEqual(summary.get("status"), status)
                self.assertEqual(summary["attempts"], attempts)
                self.assertEqual(summary.get("expected_attempts"), 36)
                self.assertEqual(summary["stop_reason"], stop_reason)
                self.assertEqual(summary.get("registration_hash"), registration_hash)


class BusinessLaunchContractTest(unittest.TestCase):
    def _registration(self):
        from bench import business_benchmark as business

        manifest = business.fixtures.build_manifest()
        counts = {
            fixture["case_id"]: {
                "autoregressive": {"prompt": 1, "expected_answer": 1},
                "diffusion": {"prompt": 1, "expected_answer": 1},
            }
            for fixture in manifest["fixtures"]
        }
        identity = {"path": "/synthetic/artifact", "size_bytes": 1, "sha256": "a" * 64}
        worker = {
            "protocol_version": 2,
            "configuration": {
                "native_protocol": True,
                "context_size": 100,
                "max_tokens": 10,
                "model_path": "/synthetic/model",
                "runner_path": "/synthetic/runner",
            },
        }
        registration = business.build_registration(
            manifest,
            counts,
            worker,
            {name: identity for name in ("autoregressive_model", "diffusion_model", "runner", "harness")},
            identity,
            "Synthetic A100",
            {"fixture_generator": identity, "resident_worker": identity},
            timeout_seconds=1,
            batch_seconds=100,
            ar_context_size=100,
        )
        return registration, identity

    def _run_cli(self, output, registration, *, warmup=None, result=None, admit=True):
        import contextlib
        import io
        import json
        from pathlib import Path
        from unittest import mock
        from bench import business_benchmark as business

        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        runtime.atomic_json(output / "registration.json", registration)
        if warmup is not None:
            runtime.atomic_json(output / "warmup.json", warmup)

        generated = []

        def rpc(_url, path, payload=None):
            if path == "/status":
                return {**registration["worker"], "active_request": None}
            if path == "/generate":
                generated.append(payload["request_id"])
                return {"request_state": "accepted"}
            raise AssertionError(path)

        class Tokenizer:
            def __init__(self, *_args):
                pass

            def count(self, _text):
                return 1

            def close(self):
                pass

        class Sampler:
            class Thread:
                def start(self):
                    pass

            thread = Thread()

            def peak_since(self, _started):
                return 0

            def close(self):
                pass

        stdout = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(business.runtime, "rpc", side_effect=rpc))
            stack.enter_context(mock.patch.object(business.runtime, "wait_result", return_value=result))
            stack.enter_context(mock.patch.object(business.runtime, "admit_case", side_effect=admit if isinstance(admit, list) else None, return_value=admit if not isinstance(admit, list) else mock.DEFAULT))
            stack.enter_context(mock.patch.object(business.density, "artifact_identity", return_value=registration["tokenizer_identity"]))
            stack.enter_context(mock.patch.object(business.density, "hardware_identity", return_value=registration["hardware_identity"]))
            stack.enter_context(mock.patch.object(business.density, "TokenizerService", Tokenizer))
            stack.enter_context(mock.patch.object(business.density, "GPUMemorySampler", Sampler))
            with contextlib.redirect_stdout(stdout):
                code = business.main([
                    "run-diffusion", "--url", "http://synthetic", "--output-dir", str(output),
                    "--tokenizer", registration["tokenizer_identity"]["path"],
                ])
        return code, generated, [json.loads(line) for line in stdout.getvalue().splitlines()]

    def test_public_prepare_refuses_unavailable_gpu_before_registration(self):
        import contextlib
        import io
        import json
        import tempfile
        from pathlib import Path
        from unittest import mock
        from bench import business_benchmark as business

        registration, identity = self._registration()
        status = {**registration["worker"], "active_request": None}
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "prepare"
            stdout = io.StringIO()
            with mock.patch.object(business.runtime, "rpc", return_value=status) as rpc_call, \
                    mock.patch.object(business, "_count_fixture_tokens", return_value={
                        fixture["case_id"]: fixture["token_counts"] for fixture in registration["fixtures"]
                    }), \
                    mock.patch.object(business.density, "artifact_identity", return_value=identity), \
                    mock.patch.object(business.density, "hardware_identity", return_value="unavailable:nvidia-smi missing"), \
                    contextlib.redirect_stdout(stdout):
                code = business.main([
                    "prepare", "--url", "http://synthetic", "--output-dir", str(output),
                    "--tokenizer", identity["path"], "--ar-model", identity["path"],
                ])
            report = json.loads(stdout.getvalue())
            self.assertNotEqual(code, 0)
            self.assertEqual(report["status"], "refused")
            self.assertFalse((output / "registration.json").exists())
            self.assertEqual([call.args[1] for call in rpc_call.call_args_list], ["/status"])

    def test_public_run_requires_completed_native_warmup_before_cases(self):
        import json
        import tempfile
        from pathlib import Path

        registration, _ = self._registration()
        invalid_warmup = {
            "request_state": "completed",
            "raw_output": "not READY",
            "native_events": [{"event": "stop", "reason": "eog"}],
        }
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            code, generated, reports = self._run_cli(
                output, registration, result=invalid_warmup, admit=[True, False]
            )
            self.assertNotEqual(code, 0)
            self.assertEqual(generated, ["business-warmup-" + registration["registration_hash"][:16]])
            self.assertEqual(reports[-1]["status"], "refused")
            self.assertEqual(reports[-1]["reason"], "warmup_failed")
            self.assertEqual(json.loads((output / "warmup.json").read_text()), invalid_warmup)
            self.assertFalse((output / "results.jsonl").exists())

    def test_public_run_reports_budget_stop_as_durable_incomplete_failure(self):
        import json
        import tempfile
        from pathlib import Path

        registration, _ = self._registration()
        warmup = {
            "request_state": "completed",
            "raw_output": '{"values":["READY"]}',
            "native_events": [{"event": "stop", "reason": "eog"}],
        }
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            code, generated, _ = self._run_cli(output, registration, warmup=warmup, admit=False)
            summary = json.loads((output / "summary.json").read_text())
            self.assertNotEqual(code, 0)
            self.assertEqual(generated, [])
            self.assertEqual(summary["status"], "incomplete")
            self.assertEqual(summary["attempts"], 0)
            self.assertEqual(summary["expected_attempts"], 36)
            self.assertEqual(summary["stop_reason"], "insufficient_full_case_budget")
            self.assertEqual(summary["registration_hash"], registration["registration_hash"])

    def test_public_run_reports_runtime_stop_after_durable_terminal_row(self):
        import json
        import tempfile
        from pathlib import Path

        registration, _ = self._registration()
        warmup = {
            "request_state": "completed",
            "raw_output": '{"values":["READY"]}',
            "native_events": [{"event": "stop", "reason": "eog"}],
        }
        failed = {
            "request_state": "failed",
            "raw_output": "",
            "native_events": [],
            "error": {"type": "RuntimeError", "message": "synthetic failure"},
            "elapsed_seconds": 0.1,
        }
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            code, generated, _ = self._run_cli(output, registration, warmup=warmup, result=failed)
            rows = [json.loads(line) for line in (output / "results.jsonl").read_text().splitlines()]
            summary = json.loads((output / "summary.json").read_text())
            self.assertNotEqual(code, 0)
            self.assertEqual(generated, [registration["request_ids"][registration["execution_order"][0]]])
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["request_state"], "failed")
            self.assertEqual(summary["status"], "incomplete")
            self.assertEqual(summary["attempts"], 1)
            self.assertEqual(summary["expected_attempts"], 36)
            self.assertEqual(summary["stop_reason"], "runtime_gate_failed")
            self.assertEqual(summary["registration_hash"], registration["registration_hash"])

    def test_public_run_reports_complete_resume_without_repeating_cases(self):
        import json
        import tempfile
        from pathlib import Path

        registration, _ = self._registration()
        warmup = {
            "request_state": "completed",
            "raw_output": '{"values":["READY"]}',
            "native_events": [{"event": "stop", "reason": "eog"}],
        }
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            rows = [
                {
                    "case_id": case_id,
                    "request_id": registration["request_ids"][case_id],
                    "registration_hash": registration["registration_hash"],
                    "request_state": "completed",
                    "problem_id": case_id.rsplit("-", 1)[0],
                    "valid": True,
                    "elapsed_seconds": 0.1,
                }
                for case_id in registration["execution_order"]
            ]
            (output / "results.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
            before = (output / "results.jsonl").read_bytes()
            first, generated, _ = self._run_cli(output, registration, warmup=warmup)
            second, generated_again, _ = self._run_cli(output, registration, warmup=warmup)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual((first, second), (0, 0))
            self.assertEqual(generated + generated_again, [])
            self.assertEqual((output / "results.jsonl").read_bytes(), before)
            self.assertEqual(summary.get("status"), "completed")
            self.assertEqual(summary["attempts"], summary.get("expected_attempts"))
            self.assertEqual(summary["stop_reason"], "all_cases_completed")
            self.assertEqual(summary["registration_hash"], registration["registration_hash"])

    def test_controller_script_reaches_self_test_from_an_unrelated_directory(self):
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        repository = Path(__file__).resolve().parents[2]
        controller = repository / "bench" / "business_benchmark.py"
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "output"
            completed = subprocess.run(
                [sys.executable, str(controller), "self-test", "--json", "--output-dir", str(output)],
                cwd=folder,
                text=True,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["status"], "launch_ready")

    def test_self_test_proves_launch_ready_registration_scoring_and_resume(self):
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        def invoke(output, *extra):
            command = [
                sys.executable,
                "-m",
                "bench.business_benchmark",
                "self-test",
                "--json",
                "--output-dir",
                str(output),
                "--url",
                "http://127.0.0.1:1",
                *extra,
            ]
            return subprocess.run(command, text=True, capture_output=True, timeout=30)

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "launch"
            first = invoke(output)
            self.assertEqual(first.returncode, 0, first.stderr)
            report = json.loads(first.stdout)
            self.assertEqual(report["status"], "launch_ready")
            self.assertEqual(report["fixture_count"], 36)
            self.assertEqual(report["decision_count"], 48)
            self.assertEqual(report["new_attempts"], 36)
            self.assertEqual(report["resumed_attempts"], 0)
            self.assertEqual(report["generation_rpc_calls"], 0)
            self.assertTrue(all(report["checks"].values()), report["checks"])

            registration_path = output / "registration.json"
            results_path = output / "results.jsonl"
            registration_bytes = registration_path.read_bytes()
            results_bytes = results_path.read_bytes()
            registration = json.loads(registration_bytes)
            fixtures = registration["fixtures"]
            self.assertEqual(len(fixtures), 36)
            self.assertEqual(
                registration["execution_order"],
                [fixture["case_id"] for fixture in fixtures],
            )
            self.assertEqual(len(set(registration["request_ids"].values())), 36)
            self.assertEqual(set(registration["request_ids"]), set(registration["execution_order"]))
            self.assertRegex(registration["registration_hash"], r"^[0-9a-f]{64}$")
            self.assertRegex(registration["manifest_hash"], r"^[0-9a-f]{64}$")
            self.assertEqual(registration["worker"]["protocol_version"], 2)
            self.assertTrue(registration["worker"]["configuration"]["native_protocol"])
            self.assertEqual(
                set(registration["identities"]),
                {"autoregressive_model", "diffusion_model", "runner", "harness"},
            )
            for fixture in fixtures:
                self.assertEqual(set(fixture["token_counts"]), {"autoregressive", "diffusion"})
                for counts in fixture["token_counts"].values():
                    self.assertGreater(counts["prompt"], 0)
                    self.assertGreater(counts["expected_answer"], 0)

            rows = [json.loads(line) for line in results_bytes.splitlines()]
            self.assertEqual(len(rows), 36)
            self.assertEqual([row["case_id"] for row in rows], registration["execution_order"])
            required = {
                "case_id", "fixture_hash", "request_id", "request_state", "outcome",
                "valid", "exact_match", "per_decision_correct", "first_error",
                "constraint_violations", "raw_output", "reasoning_content",
                "final_output", "native_stop_reason", "prompt_tokens",
                "output_tokens", "started_at", "completed_at", "elapsed_seconds",
                "worker_elapsed_seconds", "model_identity", "runner_identity",
                "registration_hash",
            }
            for row in rows:
                self.assertFalse(required - set(row), (row.get("case_id"), required - set(row)))
                self.assertEqual(row["request_id"], registration["request_ids"][row["case_id"]])
                self.assertEqual(row["registration_hash"], registration["registration_hash"])
            self.assertTrue(any(row["valid"] and row["reasoning_content"] for row in rows))
            self.assertTrue(any(row["outcome"] == "invalid_final" for row in rows))
            self.assertTrue(any(row["outcome"] == "timed_out" for row in rows))
            self.assertTrue(any(row["outcome"] == "cancelled" for row in rows))
            self.assertTrue(any(row["outcome"] == "native_crash" for row in rows))
            self.assertTrue(report["checks"]["duplicate_keys_rejected"])

            second = invoke(output)
            self.assertEqual(second.returncode, 0, second.stderr)
            resumed = json.loads(second.stdout)
            self.assertEqual(resumed["status"], "launch_ready")
            self.assertEqual(resumed["new_attempts"], 0)
            self.assertEqual(resumed["resumed_attempts"], 36)
            self.assertEqual(resumed["generation_rpc_calls"], 0)
            self.assertEqual(registration_path.read_bytes(), registration_bytes)
            self.assertEqual(results_path.read_bytes(), results_bytes)

            unsafe = root / "unsafe"
            refused = invoke(unsafe, "--context-size", "1", "--max-tokens", "1")
            self.assertNotEqual(refused.returncode, 0)
            refusal = json.loads(refused.stdout)
            self.assertEqual(refusal["status"], "refused")
            self.assertEqual(refusal["reason"], "unsafe_context")
            self.assertEqual(refusal["generation_rpc_calls"], 0)
            self.assertFalse((unsafe / "registration.json").exists())
            self.assertFalse((unsafe / "results.jsonl").exists())


class ResultContractTest(unittest.TestCase):
    def test_completed_artifact_is_atomically_mirrored(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "local" / "case.result.json"
            source.parent.mkdir()
            source.write_text('{"valid":true}')
            runtime.mirror_file(source, root / "drive")
            self.assertEqual((root / "drive" / source.name).read_text(), source.read_text())
            self.assertFalse((root / "drive" / (source.name + ".tmp")).exists())

    def test_admission_reserves_the_full_generation_limit(self):
        self.assertFalse(runtime.admit_case(40, 120))
        self.assertFalse(runtime.admit_case(124, 120))
        self.assertTrue(runtime.admit_case(125, 120))

    def test_reasoning_and_original_timeout_are_not_converted_to_correctness(self):
        case = make_case(256, "direct", 0, item_count=8)
        error = {"type": "TimeoutError", "message": "original deadline"}
        row = runtime.classify_result(case, '<|channel>thought\n{"values":["A"]}',
                                      {"error": error, "native_events": []})
        self.assertFalse(row["valid"])
        self.assertEqual(row["outcome"], "timed_out")
        self.assertEqual(row["error"], error)
        self.assertEqual(row["final_output"], "")
        self.assertIsNone(row["native_stop_reason"])

    def test_duplicate_native_stops_cannot_be_reported_as_correct(self):
        from bench.dependency_density_bench import compact_json
        case = make_case(256, "direct", 0, item_count=8)
        row = runtime.classify_result(case, compact_json(case["expected"]),
            {"native_events": [{"event": "stop", "reason": "eog"}]*2})
        self.assertFalse(row["valid"])
        self.assertEqual(row["outcome"], "ambiguous_native_stop")

    def test_failed_request_time_counts_toward_cost_per_correct_answer(self):
        rows = [{"valid": True, "elapsed_seconds": 10}, {"valid": False, "elapsed_seconds": 90}]
        result = runtime.summarize_run(rows, 120)
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["request_seconds_per_correct"], 100)
        self.assertEqual(result["allocation_seconds_per_correct"], 120)
        self.assertIsNone(runtime.summarize_run([rows[1]], 90)["allocation_seconds_per_correct"])


class DurableWorkerTests(unittest.TestCase):
    def test_restart_does_not_repeat_an_existing_request(self):
        import tempfile
        from pathlib import Path
        from bench.diffusion_runtime import Worker, atomic_json
        with tempfile.TemporaryDirectory() as folder:
            request = {"request_id": "saved", "prompt": "same", "timeout_seconds": 120}
            atomic_json(Path(folder)/"saved.request.json", request)
            atomic_json(Path(folder)/"saved.result.json", {"request_id": "saved", "request_state": "completed"})
            worker = Worker(None, folder)
            self.assertEqual(worker.submit(request)["request_state"], "completed")
            with self.assertRaises(RuntimeError):
                worker.submit(dict(request, prompt="different"))

    def test_interrupted_worker_request_is_not_silently_replayed(self):
        import tempfile
        from pathlib import Path
        from bench.diffusion_runtime import Worker, atomic_json
        with tempfile.TemporaryDirectory() as folder:
            request = {"request_id": "saved", "prompt": "same", "timeout_seconds": 120}
            atomic_json(Path(folder)/"saved.request.json", request)
            worker = Worker(None, folder)
            result = worker.submit(request)
            self.assertEqual(result["request_state"], "failed")
            self.assertEqual(result["error"]["type"], "WorkerInterrupted")

class NativeCancellationTests(unittest.TestCase):
    def test_acknowledged_cancel_reuses_process_and_persists_identity(self):
        import tempfile, textwrap, sys, time
        from pathlib import Path
        from bench.dependency_density_bench import DiffusionSession
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder)/"native.py"
            script.write_text(textwrap.dedent('''
                import os,sys,json,signal,time
                cancelled=False
                def signal_cancel(*_):
                    global cancelled
                    cancelled=True
                signal.signal(signal.SIGUSR1,signal_cancel)
                def event(name,**fields):
                    with open(os.environ['DIFFUSION_EVENT_PATH'],'a') as f:
                        f.write(json.dumps(dict(event=name,version=2,**fields))+'\\n')
                def ready():
                    event('ready');print('\\n> ',end='',flush=True)
                ready()
                for line in sys.stdin:
                    if line.strip()=='/clear':ready();continue
                    if line.strip()=='hang':
                        print('<|channel>thought\\nworking',flush=True)
                        while not cancelled:time.sleep(.005)
                        event('stop',reason='cancelled');cancelled=False
                    else:
                        print('{"values":["A","B"]}',flush=True)
                        event('stop',reason='eog')
                    ready()
            '''))
            class Session(DiffusionSession):
                def command(self):return [sys.executable, '-u',str(script)]
            session=Session('unused','unused',9216,1,native_protocol=True,trace_dir=Path(folder)/'trace')
            worker=runtime.Worker(session,Path(folder)/'results')
            self.addCleanup(worker.close)
            session.start();pid=session.process.pid
            request=dict(request_id='cancel-me',prompt='hang',timeout_seconds=5)
            worker.submit(request)
            deadline=time.monotonic()+5
            while session.state!='generating' and time.monotonic()<deadline:time.sleep(.01)
            self.assertFalse(worker.status()['ready'])
            with self.assertRaises(RuntimeError):worker.submit(dict(request,request_id='busy'))
            worker.cancel('cancel-me');worker.thread.join(5)
            row=worker.result('cancel-me')
            self.assertEqual(row['request_state'],'cancelled')
            self.assertEqual(row['cancellation_ack'],'native_cancelled')
            self.assertTrue(worker.status()['ready'])
            self.assertEqual(session.process.pid,pid)
            self.assertEqual(worker.submit(request),row)
            worker.submit(dict(request,request_id='next',prompt='okay'));worker.thread.join(5)
            self.assertEqual(worker.result('next')['raw_output'],'{"values":["A","B"]}')
            self.assertEqual(session.process.pid,pid)
            session.process.kill();session.process.wait()
            self.assertFalse(worker.status()['ready'])
            self.assertFalse(worker.status()['loaded'])

class Utf8PipeBoundaryTest(unittest.TestCase):
    def test_multibyte_character_split_across_reads_is_preserved(self):
        import sys, tempfile, textwrap
        from pathlib import Path
        from bench.dependency_density_bench import DiffusionSession
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "split.py"
            script.write_text(textwrap.dedent('''
                import sys, time
                print("ready\\n> ", end="", flush=True)
                for line in sys.stdin:
                    sys.stdout.buffer.write(b"\\xe4"); sys.stdout.buffer.flush()
                    time.sleep(.12)
                    sys.stdout.buffer.write(b"\\xb8\\xad\\n> "); sys.stdout.buffer.flush()
            '''))
            class SplitSession(DiffusionSession):
                def command(self): return [sys.executable, "-u", str(script)]
            session = SplitSession("unused", "unused", 32, 1, timeout=2)
            try:
                self.assertEqual(session.generate("x")[0], "中")
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
