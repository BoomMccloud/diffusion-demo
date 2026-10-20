import json
import random
import unittest

import numpy as np

from bench.synthdata import config, tasks
from bench.synthdata.metrics import expected_distinct, greedy_distinct

GOOD = ("患者，女，62岁。\n【主诉】反复上腹痛伴反酸、烧心3个月，加重1周。\n【现病史】" + "患者症状反复。" * 20 +
        "\n【既往史】否认高血压。\n【入院检查】腹软。\n【诊断】1. 慢性非萎缩性胃炎伴糜烂；2. 胃食管反流病。"
        "\n【诊疗经过】予抑酸治疗。\n【出院医嘱】继续服药。")


class FormatRepairTest(unittest.TestCase):
    """Repairs seen in the 2026-10-20 smoke narratives."""

    def test_markdown_headers_become_brackets(self):
        raw = GOOD.replace("【主诉】", "**主诉：** ").replace("【诊断】", "**入院诊断：**")
        text, _, reason = tasks.check("narrative", None, raw)
        self.assertIsNone(reason)
        self.assertIn("【主诉】反复上腹痛", text)
        self.assertIn("【诊断】1. 慢性", text)
        self.assertFalse(tasks.raw_format_ok("narrative", None, raw))

    def test_preamble_and_opening_complaint_sentence(self):
        body = GOOD.split("\n", 2)[2]
        raw = "好的，这是一份虚构病历：\n\n患者，女，62岁，因“反复右上腹痛伴恶心2天”入院。\n" + body
        text, _, reason = tasks.check("narrative", None, raw)
        self.assertIsNone(reason)
        self.assertTrue(text.startswith("患者，女，62岁。\n【主诉】反复右上腹痛伴恶心2天"))

    def test_sectionless_prose_still_fails(self):
        _, _, reason = tasks.check("narrative", None, "患者，男，56岁，主诉“上腹痛”。现病史：" + "腹痛。" * 60)
        self.assertTrue(reason.startswith("missing"))

    def test_demographics_must_match_the_seed(self):
        seed = {"department": "消化内科", "sex": "男", "age_lo": 45, "age_hi": 64}
        self.assertEqual(tasks.check("narrative", seed, GOOD)[2], "off seed")
        self.assertIsNone(tasks.check("narrative", {**seed, "sex": "女"}, GOOD)[2])
        self.assertEqual(tasks.check("narrative", None, GOOD.split("\n", 1)[1])[2], "missing demographics")

    def test_clinical_text_is_untouched(self):
        self.assertEqual(tasks.repair_narrative(GOOD), GOOD)


class RecordCheckTest(unittest.TestCase):
    base = {"sex": "女", "age": 62, "department": "呼吸内科", "chief_complaint": "咳嗽咳痰1周",
            "diagnosis": "社区获得性肺炎", "allergies": ["青霉素"], "prescriptions": ["阿奇霉素片"]}

    def test_allergy_class_conflict(self):
        bad = {**self.base, "prescriptions": ["阿莫西林胶囊"]}
        self.assertEqual(tasks.check("record", None, json.dumps(bad, ensure_ascii=False))[2], "allergy conflict")

    def test_seed_mismatch(self):
        seed = {"department": "呼吸内科", "sex": "男", "age_lo": 18, "age_hi": 44}
        self.assertEqual(tasks.check("record", seed, json.dumps(self.base, ensure_ascii=False))[2], "off seed")

    def test_valid_record_in_code_fence(self):
        raw = "```json\n" + json.dumps(self.base, ensure_ascii=False) + "\n```"
        self.assertIsNone(tasks.check("record", None, raw)[2])


class CaseKeyTest(unittest.TestCase):
    def test_durations_collapse_but_disease_numbers_do_not(self):
        a = GOOD
        b = GOOD.replace("3个月，加重1周", "半年，加重3天")
        self.assertEqual(tasks.case_key("narrative", a, None), tasks.case_key("narrative", b, None))
        r1 = {"chief_complaint": "多饮多尿2年", "diagnosis": "1型糖尿病"}
        r2 = {"chief_complaint": "多饮多尿5年", "diagnosis": "2型糖尿病"}
        self.assertNotEqual(tasks.case_key("record", "", r1), tasks.case_key("record", "", r2))


class DistinctTest(unittest.TestCase):
    def test_near_copies_and_repeated_keys_are_dropped(self):
        sim = np.array([[1, .99, .5], [.99, 1, .5], [.5, .5, 1]])
        self.assertEqual(greedy_distinct(sim, ["a", "b", "c"], [0, 1, 2], 0.97), 2)
        self.assertEqual(greedy_distinct(sim, ["a", "b", "a"], [0, 2, 1], 0.4), 1)
        self.assertEqual(expected_distinct(sim, ["a", "b", "c"], 0.97, 10, random.Random(0)), 2)


class SeedGridTest(unittest.TestCase):
    def test_grid_excludes_male_obstetrics(self):
        grid = config.seed_grid()
        self.assertEqual(len(grid), 69)
        self.assertFalse([s for s in grid if s["department"] == "妇产科" and s["sex"] == "男"])


if __name__ == "__main__":
    unittest.main()
