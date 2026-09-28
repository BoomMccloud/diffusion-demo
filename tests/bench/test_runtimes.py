import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from bench import diffusion_runtime as runtime


class NativeTranscriptTest(unittest.TestCase):
    """Observed llama-diffusion-cli transcripts and Gemma 4 native channels."""

    answer = '{"values":["A","B"]}'

    def test_runner_transport_is_removed_around_the_reply(self):
        from bench.gemma_runtimes import diffusion_response_text
        plain = ('\rdiffusion step: 1/48 [==  ] 2%\n' + self.answer +
                 '\ntotal time: 123.4ms, time per step: 1ms\nthroughput: 1.0 tok/s (256 tok in 123.4ms)\n\n> ')
        self.assertEqual(diffusion_response_text(plain), self.answer)
        observed = ('0.15.602.834 W init: embeddings required but some input tokens were not marked as outputs -> overriding\n'
                    '0.16.167.310 I \rdiffusion step: 0/48 [   ] 0%0.16.305.651 I \rdiffusion step: 1/48 [=  ] 2%\n'
                    + self.answer + '\ntotal time: 1565.95ms, time per step: 173.99ms (9 steps over 1 blocks, entropy-bound)\n'
                    'throughput: 163.5 tok/s (256 tok in 1565.95ms), in-step parallel 1471 tok/s (256-tok canvas x 9.0 steps/block)\n\n> ')
        self.assertEqual(diffusion_response_text(observed), self.answer)
        self.assertTrue(diffusion_response_text("explanation\n" + plain).startswith("explanation"))

    def test_only_one_well_formed_thought_channel_is_split(self):
        from bench.gemma_runtimes import split_native_response
        thought = "<|channel>thought\nreasoning<channel|>" + self.answer
        self.assertEqual(split_native_response(thought), (self.answer, "reasoning"))
        for malformed in ("<|channel>thought\nreasoning" + self.answer,
                          thought + "<channel|>",
                          thought.replace("reasoning", "<|channel>thought\nreasoning")):
            with self.subTest(malformed=malformed):
                self.assertEqual(split_native_response(malformed), (malformed, None))


class TokenizerServiceTest(unittest.TestCase):
    def test_hex_line_protocol_counts_text_and_prompts(self):
        from bench.gemma_runtimes import TokenizerService
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / "tokenizer"
            helper.write_text("#!" + sys.executable + "\nimport sys\nfor line in sys.stdin:\n prompt = line.startswith('p:')\n"
                              " print(len(bytes.fromhex(line[2:] if prompt else line).decode('utf-8')) + (2 if prompt else 0), flush=True)\n")
            helper.chmod(0o700)
            tokenizer = TokenizerService(str(helper), "unused")
            try:
                self.assertEqual(tokenizer.count("first\nsecond"), 12)
                self.assertEqual(tokenizer.count("中"), 1)
                self.assertEqual(tokenizer.count(""), 0)
                self.assertEqual(tokenizer.count_prompt("中"), 3)
            finally:
                tokenizer.close()
            self.assertIsNotNone(tokenizer.process.poll())


class DiffusionSessionLifecycleTest(unittest.TestCase):
    """Real pipe/process boundary, using the runner's interactive wire protocol."""

    def setUp(self):
        from bench.gemma_runtimes import DiffusionSession

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
        from bench.gemma_runtimes import split_native_response

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
        from bench.gemma_runtimes import DiffusionSession
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
        from bench.gemma_runtimes import DiffusionSession
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


class NemotronRunnerTest(unittest.TestCase):
    def test_cases_are_jsonl_with_unique_ids(self):
        from bench import nemotron_runner as runner
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.jsonl"
            path.write_text('{"case_id":"a","prompt":"x"}\n\n{"case_id":"b","prompt":"y","max_new_tokens":64}\n')
            self.assertEqual([c["case_id"] for c in runner.load_cases(path)], ["a", "b"])
            path.write_text('{"case_id":"a","prompt":"x"}\n{"case_id":"a","prompt":"y"}\n')
            with self.assertRaises(SystemExit):
                runner.load_cases(path)

    def test_thinking_is_split_from_the_final_answer(self):
        from bench import nemotron_runner as runner
        self.assertEqual(runner.strip_thinking("<think>\nwork</think>\nanswer"), "answer")
        self.assertEqual(runner.thinking_text("<think>\nwork</think>\nanswer"), "work")
        self.assertIsNone(runner.thinking_text("answer"))


if __name__ == "__main__":
    unittest.main()
