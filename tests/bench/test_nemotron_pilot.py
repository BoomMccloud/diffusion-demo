import unittest

from bench import business_fixtures as fixtures
from bench import nemotron_pilot as pilot


class LongFixtureTests(unittest.TestCase):
    def test_long_cases_extend_the_48_item_input(self):
        for problem_id in ("L0", "L1", "D1"):
            short = pilot.pilot_fixture(problem_id, 48, "v4", 1)
            long = pilot.pilot_fixture(problem_id, 256, "v4", 1)
            key = pilot.ITEM_LISTS[problem_id]
            self.assertEqual(len(long["input"][key]), 256)
            self.assertEqual(long["input"][key][:48], short["input"][key])

    def test_d1_default_count_keeps_frozen_fixture(self):
        frozen = fixtures.make_fixture("D1", 2)
        self.assertEqual(pilot.pilot_fixture("D1", 48, "v4", 2)["input"], frozen["input"])

    def test_fixture_indices_differ(self):
        inputs = {str(pilot.pilot_fixture("L0", 8, "v4", i)["input"]) for i in range(3)}
        self.assertEqual(len(inputs), 3)

    def test_other_business_problems_refuse_more_than_48(self):
        with self.assertRaises(SystemExit):
            pilot.pilot_fixture("C2", 64, "v4")


class LineFormatTests(unittest.TestCase):
    def setUp(self):
        self.fixture = pilot.pilot_fixture("L1", 8, "v5", 0)
        expected = pilot.SOLVERS["L1"](self.fixture["input"])
        self.lines = [f"{k}={v}" for k, v in zip(self.fixture["output_keys"], expected)]

    def score(self, text):
        return pilot.score_row(self.fixture, {"final_output": text, "stop_reason": "eos"})

    def test_exact_lines_are_correct(self):
        self.assertEqual(self.score("\n".join(self.lines))["outcome"], "correct")

    def test_quoted_values_fail_strict_but_pass_lenient(self):
        quoted = "\n".join(line.replace("=", '="') + '"' for line in self.lines)
        result = self.score(quoted)
        self.assertFalse(result["valid"])
        self.assertTrue(result["lenient_valid"])

    def test_fenced_output_is_invalid_format_strict_only(self):
        result = self.score("```\n" + "\n".join(self.lines) + "\n```")
        self.assertEqual(result["outcome"], "invalid_format")
        self.assertTrue(result["lenient_valid"])

    def test_missing_line_is_invalid(self):
        self.assertFalse(self.score("\n".join(self.lines[:-1]))["valid"])

    def test_prompt_has_no_quotes(self):
        self.assertNotIn('"', self.fixture["prompt"].split("Input:")[0])


class ThinkingTextTests(unittest.TestCase):
    def test_split(self):
        raw = "<think>\nadd 3\n</think>\n{\"a\":\"1\"}"
        self.assertEqual(pilot.thinking_text(raw), "add 3")
        self.assertEqual(pilot.strip_thinking(raw), '{"a":"1"}')
        self.assertIsNone(pilot.thinking_text('{"a":"1"}'))


if __name__ == "__main__":
    unittest.main()
