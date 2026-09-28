import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = REPO_ROOT / "bench" / "business_fixtures.py"


class BusinessFixtureContractTest(unittest.TestCase):
    def test_initial_screen_is_frozen_complete_and_self_validating(self):
        from bench import business_fixtures

        first = business_fixtures.build_manifest(cases_per_problem=3)
        second = business_fixtures.build_manifest(cases_per_problem=3)
        self.assertEqual(
            business_fixtures.compact_json(first),
            business_fixtures.compact_json(second),
            "same registered seed must produce byte-identical fixtures",
        )
        self.assertTrue(business_fixtures.verify_manifest(first))
        self.assertEqual(len(first["fixtures"]), 36)
        self.assertEqual(
            set(business_fixtures.PROBLEM_IDS),
            {fixture["problem_id"] for fixture in first["fixtures"]},
        )
        counts = {
            problem_id: sum(
                fixture["problem_id"] == problem_id for fixture in first["fixtures"]
            )
            for problem_id in business_fixtures.PROBLEM_IDS
        }
        self.assertEqual(set(counts.values()), {3})
        for problem_id in business_fixtures.PROBLEM_IDS:
            inputs = {
                business_fixtures.stable_hash(fixture["input"])
                for fixture in first["fixtures"]
                if fixture["problem_id"] == problem_id
            }
            self.assertEqual(
                len(inputs), 3, f"{problem_id} did not vary its three seeded inputs"
            )

        for fixture in first["fixtures"]:
            if fixture["problem_id"] == "M2":
                self.assertIn(
                    "DENY:DAILY_MEAL_CAP", fixture["reference_answer"]["values"]
                )
            if fixture["problem_id"] == "C3":
                self.assertNotIn("0", fixture["reference_answer"]["values"])

        tampered = copy.deepcopy(first)
        tampered_fixture = tampered["fixtures"][0]
        tampered_fixture["input"]["transactions"][0]["amount_cents"] += 1
        tampered_fixture["fixture_hash"] = business_fixtures.fixture_hash(tampered_fixture)
        unsigned_manifest = {
            key: value for key, value in tampered.items() if key != "manifest_hash"
        }
        tampered["manifest_hash"] = business_fixtures.stable_hash(unsigned_manifest)
        self.assertFalse(
            business_fixtures.verify_manifest(tampered),
            "a rehashed edit must not replace the fixture registered by its seed",
        )
        for header, replacement in (
            ("base_seed", first["base_seed"] + 1),
            ("schema_version", "business-fixtures-v999"),
            ("problem_ids", list(reversed(first["problem_ids"]))),
        ):
            with self.subTest(rehashed_header=header):
                tampered = copy.deepcopy(first)
                tampered[header] = replacement
                unsigned_manifest = {
                    key: value for key, value in tampered.items()
                    if key != "manifest_hash"
                }
                tampered["manifest_hash"] = business_fixtures.stable_hash(
                    unsigned_manifest
                )
                self.assertFalse(business_fixtures.verify_manifest(tampered))

        for fixture in first["fixtures"]:
            with self.subTest(case_id=fixture["case_id"]):
                self.assertEqual(fixture["decision_count"], 48)
                self.assertEqual(len(fixture["reference_answer"]["values"]), 48)
                self.assertEqual(
                    fixture["fixture_hash"],
                    business_fixtures.fixture_hash(fixture),
                )
                self.assertTrue(business_fixtures.validate_fixture(fixture))
                reference = business_fixtures.evaluate_answer(
                    fixture, fixture["reference_answer"]
                )
                self.assertTrue(reference["valid"], reference)

                corrupted = copy.deepcopy(fixture["reference_answer"])
                corrupted["values"][0] = "__INVALID__"
                rejected = business_fixtures.evaluate_answer(fixture, corrupted)
                self.assertFalse(rejected["valid"], rejected)
                self.assertTrue(
                    rejected["first_error"] == 0
                    or rejected["constraint_violations"],
                    rejected,
                )

        for fixture in first["fixtures"]:
            if fixture["scoring_mode"] != "constraint_objective":
                continue
            with self.subTest(noncanonical_global=fixture["case_id"]):
                alternate = fixture["alternate_valid_answer"]
                self.assertNotEqual(alternate, fixture["reference_answer"])
                result = business_fixtures.evaluate_answer(fixture, alternate)
                self.assertTrue(result["valid"], result)
                self.assertFalse(result["exact_match"])

    def test_each_problem_rule_has_an_independent_hand_calculated_oracle(self):
        from bench import business_fixtures as subject

        self.assertEqual(
            subject._solve_d1({
                "account_rules": {"airfare": "TRAVEL_AIR", "paper": "OFFICE"},
                "transactions": [{"category": "paper"}, {"category": "airfare"}],
            }),
            ["OFFICE", "TRAVEL_AIR"],
        )
        self.assertEqual(
            subject._solve_d2({"tickets": [
                {"tier": "ENTERPRISE", "region": "JP", "language": "DE", "product": "PAY", "issue": "BILLING"},
                {"tier": "STANDARD", "region": "US", "language": "JA", "product": "CORE", "issue": "ACCESS"},
                {"tier": "STANDARD", "region": "EU", "language": "EN", "product": "DATA", "issue": "OUTAGE"},
            ]}),
            ["JP_ENT_PAY_BILLING", "JA_CORE_ACCESS", "EU_DATA_OUTAGE"],
        )
        d3_policy = {"review_threshold_cents": {"IT": 100}, "orders": [
            {"supplier_status": "SANCTIONED", "jurisdiction": "DOMESTIC", "contract": True, "amount_cents": 1, "category": "IT"},
            {"supplier_status": "APPROVED", "jurisdiction": "RESTRICTED", "contract": True, "amount_cents": 1, "category": "IT"},
            {"supplier_status": "PENDING", "jurisdiction": "DOMESTIC", "contract": True, "amount_cents": 1, "category": "IT"},
            {"supplier_status": "APPROVED", "jurisdiction": "DOMESTIC", "contract": False, "amount_cents": 101, "category": "IT"},
            {"supplier_status": "APPROVED", "jurisdiction": "DOMESTIC", "contract": True, "amount_cents": 101, "category": "IT"},
        ]}
        self.assertEqual(subject._solve_d3(d3_policy), ["REJECT", "REJECT", "REVIEW", "REVIEW", "APPROVE"])

        m1 = {"lines": [
            {"kind": "ITEM", "quantity": 2, "unit_cents": 100, "tax_bps": 500, "reported_net_cents": 201, "reported_tax_cents": 10},
            {"kind": "ITEM", "quantity": 1, "unit_cents": 100, "tax_bps": 500, "reported_net_cents": 100, "reported_tax_cents": 4},
            {"kind": "ITEM", "quantity": 1, "unit_cents": 100, "tax_bps": 500, "reported_net_cents": 100, "reported_tax_cents": 5},
            {"kind": "SUBTOTAL", "reported_total_cents": 419},
        ]}
        self.assertEqual(subject._solve_m1(m1), ["PRICE_ERROR", "TAX_ERROR", "VALID", "SUBTOTAL_ERROR"])
        m2 = {
            "item_limit_cents": {"MEAL": 6000, "TAXI": 12000},
            "receipt_required_above_cents": 2500,
            "daily_meal_cap_cents": 9000,
            "expenses": [
                {"day": 1, "category": "MEAL", "amount_cents": 5000, "receipt": True},
                {"day": 1, "category": "MEAL", "amount_cents": 4500, "receipt": True},
                {"day": 1, "category": "TAXI", "amount_cents": 13000, "receipt": True},
                {"day": 1, "category": "TAXI", "amount_cents": 3000, "receipt": False},
            ],
        }
        self.assertEqual(subject._solve_m2(m2), ["APPROVE:OK", "DENY:DAILY_MEAL_CAP", "DENY:ITEM_LIMIT", "DENY:NO_RECEIPT"])
        m3 = {"inventory": {"A": 2, "B": 1, "C": 3}, "groups": [
            {"components": [{"id": "1", "sku": "A", "quantity": 2}, {"id": "2", "sku": "B", "quantity": 2}, {"id": "3", "sku": "C", "quantity": 1}], "required_line_ids": ["1", "2", "3"]},
        ]}
        self.assertEqual(subject._solve_m3(m3), ["FULFILL", "BACKORDER", "FULFILL", "BACKORDER"])

        self.assertEqual(
            subject._solve_c1({"opening_balance_cents": 10000, "events": [
                {"kind": "DEPOSIT", "amount_cents": 1000},
                {"kind": "WITHDRAWAL", "amount_cents": 500},
                {"kind": "INTEREST", "rate_bps": 100},
                {"kind": "FEE", "amount_cents": 105},
            ]}),
            ["11000", "10500", "10605", "10500"],
        )
        self.assertEqual(
            subject._solve_c2({"opening_stock": 5, "movements": [
                {"kind": "SALE", "quantity": 3}, {"kind": "DAMAGE", "quantity": 4},
                {"kind": "RETURN", "quantity": 2}, {"kind": "TRANSFER_OUT", "quantity": 4},
            ]}),
            ["2:ACCEPT", "2:REJECT", "4:ACCEPT", "0:ACCEPT"],
        )
        self.assertEqual(
            subject._solve_c3({"principal_cents": 10000, "periodic_rate_bps": 100, "fixed_payment_cents": 1000, "periods": [
                {"extra_payment_cents": 0}, {"extra_payment_cents": 100},
            ]}),
            ["9100", "8091"],
        )

        g1_data = {"minimum_rest_hours": 16, "employees": [
            {"id": "E", "skills": ["OPS"], "available_slots": [0, 1], "max_shifts": 1},
        ], "slots": [{"required_skill": "OPS", "start_hour": 0}, {"required_skill": "CARE", "start_hour": 8}]}
        g1_violations, _ = subject._validate_g1(g1_data, ["E", "E"])
        self.assertEqual(set(g1_violations), {"skill:1", "max_shifts:E", "rest:E"})

        g2_data = {"maximum_total_cost": 5, "warehouses": [
            {"id": "W", "regions": ["N"], "capacity_orders": 1, "stock": {"S": 1}, "cost_per_order": 3},
        ], "orders": [{"region": "N", "sku": "S", "quantity": 1}, {"region": "S", "sku": "S", "quantity": 1}]}
        g2_violations, cost = subject._validate_g2(g2_data, ["W", "W"])
        self.assertEqual(cost, 6)
        self.assertEqual(set(g2_violations), {"delivery:1", "capacity:W", "stock:W:S", "objective:cost"})

        g3_data = {"maximum_language_mismatches": 0, "tables": [
            {"id": "T", "capacity": 1, "accessible": False, "language": "EN"},
        ], "attendees": [
            {"team": "A", "needs_accessible": True, "language": "JA", "host": False},
            {"team": "A", "needs_accessible": False, "language": "EN", "host": False},
        ]}
        g3_violations, mismatches = subject._validate_g3(g3_data, ["T", "T"])
        self.assertEqual(mismatches, 1)
        self.assertEqual(set(g3_violations), {"accessibility:0", "capacity:T", "team_separation:T", "host:T", "objective:language"})

    def test_cli_emits_and_revalidates_one_canonical_manifest(self):
        self.assertTrue(GENERATOR.is_file())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "business-screen.json"
            generated = subprocess.run(
                [sys.executable, str(GENERATOR), "generate", "--output", str(output)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
            manifest = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["fixtures"]), 36)

            validated = subprocess.run(
                [sys.executable, str(GENERATOR), "validate", str(output), "--json"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(validated.returncode, 0, validated.stdout + validated.stderr)
            self.assertEqual(json.loads(validated.stdout)["status"], "ok")


if __name__ == "__main__":
    unittest.main()
