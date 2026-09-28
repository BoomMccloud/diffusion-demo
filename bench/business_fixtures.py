#!/usr/bin/env python3
"""Deterministic fixtures for the twelve business dependency benchmarks.

This module is deliberately standard-library-only. It generates frozen inputs,
reference answers, validation metadata, and content hashes. It does not load or
execute either model runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path


SCHEMA_VERSION = "business-fixtures-v1"
BASE_SEED = 20260907
DECISION_COUNT = 48
DEFAULT_CASES_PER_PROBLEM = 3
PROBLEM_IDS = (
    "D1", "D2", "D3",
    "M1", "M2", "M3",
    "C1", "C2", "C3",
    "G1", "G2", "G3",
)
PROBLEMS = {
    "D1": ("direct", "accounts-payable-classification"),
    "D2": ("direct", "support-ticket-routing"),
    "D3": ("direct", "purchase-order-compliance"),
    "M1": ("mixed", "invoice-subtotal-validation"),
    "M2": ("mixed", "expense-policy-review"),
    "M3": ("mixed", "bundle-aware-fulfillment"),
    "C1": ("chained", "cash-balance-ledger"),
    "C2": ("chained", "inventory-movement-ledger"),
    "C3": ("chained", "loan-amortization"),
    "G1": ("global", "employee-shift-assignment"),
    "G2": ("global", "warehouse-order-allocation"),
    "G3": ("global", "conference-seating"),
}


def compact_json(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def stable_hash(value):
    if not isinstance(value, str):
        value = compact_json(value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fixture_hash(fixture):
    return stable_hash({key: value for key, value in fixture.items() if key != "fixture_hash"})


def _round_ratio(numerator, denominator):
    """Round a nonnegative rational half up using integer arithmetic."""
    return (int(numerator) * 2 + int(denominator)) // (2 * int(denominator))


def _seed(problem_id, fixture_index, base_seed):
    return int(base_seed) + PROBLEM_IDS.index(problem_id) * 100_003 + int(fixture_index) * 9_973


def _generate_d1(rng):
    categories = [
        ("airfare", "TRAVEL_AIR"),
        ("lodging", "TRAVEL_LODGING"),
        ("cloud", "SOFTWARE_INFRASTRUCTURE"),
        ("paper", "OFFICE_SUPPLIES"),
        ("legal", "PROFESSIONAL_LEGAL"),
        ("courier", "SHIPPING_COURIER"),
    ]
    merchants = ["Aster", "Beacon", "Cobalt", "Delta", "Elm", "Fjord"]
    transactions = []
    for index in range(DECISION_COUNT):
        category, _ = rng.choice(categories)
        transactions.append({
            "id": f"TX{index + 1:02d}",
            "merchant": rng.choice(merchants),
            "description": f"approved {category} purchase",
            "category": category,
            "amount_cents": rng.randrange(900, 250_001),
            "currency": rng.choice(["USD", "EUR", "JPY"]),
        })
    return {"account_rules": dict(categories), "transactions": transactions}


def _solve_d1(data):
    rules = data["account_rules"]
    return [rules[item["category"]] for item in data["transactions"]]


def _generate_d2(rng):
    products = ["CORE", "PAY", "DATA"]
    issues = ["BILLING", "ACCESS", "OUTAGE"]
    tickets = []
    for index in range(DECISION_COUNT):
        tickets.append({
            "id": f"T{index + 1:02d}",
            "product": rng.choice(products),
            "issue": rng.choice(issues),
            "tier": rng.choice(["STANDARD", "ENTERPRISE"]),
            "language": rng.choice(["EN", "JA", "DE"]),
            "region": rng.choice(["US", "JP", "EU"]),
        })
    return {"tickets": tickets}


def _solve_d2(data):
    values = []
    for ticket in data["tickets"]:
        if ticket["tier"] == "ENTERPRISE":
            prefix = ticket["region"] + "_ENT"
        elif ticket["language"] != "EN":
            prefix = ticket["language"]
        else:
            prefix = ticket["region"]
        values.append(f"{prefix}_{ticket['product']}_{ticket['issue']}")
    return values


def _generate_d3(rng):
    thresholds = {"GENERAL": 75_000, "IT": 125_000, "CONSTRUCTION": 200_000}
    orders = []
    for index in range(DECISION_COUNT):
        orders.append({
            "id": f"PO{index + 1:02d}",
            "supplier_status": rng.choices(
                ["APPROVED", "PENDING", "SANCTIONED"], weights=[7, 2, 1]
            )[0],
            "amount_cents": rng.randrange(10_000, 300_001),
            "category": rng.choice(list(thresholds)),
            "contract": bool(rng.randrange(2)),
            "jurisdiction": rng.choice(["DOMESTIC", "ALLIED", "RESTRICTED"]),
        })
    return {"review_threshold_cents": thresholds, "orders": orders}


def _solve_d3(data):
    values = []
    for order in data["orders"]:
        if order["supplier_status"] == "SANCTIONED" or order["jurisdiction"] == "RESTRICTED":
            decision = "REJECT"
        elif order["supplier_status"] != "APPROVED":
            decision = "REVIEW"
        elif not order["contract"] and order["amount_cents"] > data["review_threshold_cents"][order["category"]]:
            decision = "REVIEW"
        else:
            decision = "APPROVE"
        values.append(decision)
    return values


def _generate_m1(rng):
    lines = []
    for section in range(12):
        correct_totals = []
        for offset in range(3):
            quantity = rng.randrange(1, 9)
            unit_cents = rng.randrange(125, 7_501)
            tax_bps = rng.choice([0, 500, 750, 1000])
            correct_net = quantity * unit_cents
            correct_tax = _round_ratio(correct_net * tax_bps, 10_000)
            net_delta = rng.choices([0, 1, -1], weights=[7, 2, 1])[0]
            tax_delta = rng.choices([0, 1, -1], weights=[7, 2, 1])[0]
            lines.append({
                "id": f"I{section + 1:02d}-{offset + 1}",
                "kind": "ITEM",
                "quantity": quantity,
                "unit_cents": unit_cents,
                "tax_bps": tax_bps,
                "reported_net_cents": correct_net + net_delta,
                "reported_tax_cents": correct_tax + tax_delta,
            })
            correct_totals.append(correct_net + correct_tax)
        subtotal_delta = rng.choices([0, 1, -2], weights=[7, 2, 1])[0]
        lines.append({
            "id": f"I{section + 1:02d}-S",
            "kind": "SUBTOTAL",
            "reported_total_cents": sum(correct_totals) + subtotal_delta,
        })
    return {"rounding": "half_up_cents", "lines": lines}


def _solve_m1(data):
    values = []
    section_totals = []
    for line in data["lines"]:
        if line["kind"] == "ITEM":
            net = line["quantity"] * line["unit_cents"]
            tax = _round_ratio(net * line["tax_bps"], 10_000)
            section_totals.append(net + tax)
            if line["reported_net_cents"] != net:
                values.append("PRICE_ERROR")
            elif line["reported_tax_cents"] != tax:
                values.append("TAX_ERROR")
            else:
                values.append("VALID")
        else:
            values.append("VALID" if line["reported_total_cents"] == sum(section_totals) else "SUBTOTAL_ERROR")
            section_totals = []
    return values


def _generate_m2(rng):
    limits = {"MEAL": 6_000, "TAXI": 12_000, "HOTEL": 30_000, "SUPPLIES": 8_000}
    expenses = []
    for day in range(12):
        categories = ["MEAL", "MEAL", rng.choice(list(limits)), rng.choice(list(limits))]
        for offset in range(4):
            category = categories[offset]
            forced_meal = offset < 2
            expenses.append({
                "id": f"E{day + 1:02d}-{offset + 1}",
                "day": day + 1,
                "category": category,
                "amount_cents": (
                    rng.randrange(4_800, 5_501)
                    if forced_meal
                    else rng.randrange(700, limits[category] + 4_001)
                ),
                "receipt": True if forced_meal else rng.random() >= 0.18,
            })
    return {
        "item_limit_cents": limits,
        "receipt_required_above_cents": 2_500,
        "daily_meal_cap_cents": 9_000,
        "expenses": expenses,
    }


def _solve_m2(data):
    approved_meals = {}
    values = []
    for expense in data["expenses"]:
        amount = expense["amount_cents"]
        category = expense["category"]
        if amount > data["receipt_required_above_cents"] and not expense["receipt"]:
            decision = "DENY:NO_RECEIPT"
        elif amount > data["item_limit_cents"][category]:
            decision = "DENY:ITEM_LIMIT"
        elif category == "MEAL" and approved_meals.get(expense["day"], 0) + amount > data["daily_meal_cap_cents"]:
            decision = "DENY:DAILY_MEAL_CAP"
        else:
            decision = "APPROVE:OK"
            if category == "MEAL":
                approved_meals[expense["day"]] = approved_meals.get(expense["day"], 0) + amount
        values.append(decision)
    return values


def _generate_m3(rng):
    groups = []
    inventory = {}
    for group_index in range(12):
        components = []
        for offset in range(3):
            sku = f"SKU{group_index + 1:02d}{chr(65 + offset)}"
            quantity = rng.randrange(1, 5)
            inventory[sku] = rng.randrange(1, 7)
            components.append({"id": f"L{group_index + 1:02d}-{offset + 1}", "sku": sku, "quantity": quantity})
        required = [item["id"] for item in components]
        if rng.random() < 0.2:
            required = required[:-1] + [f"UNKNOWN{group_index:02d}"]
        groups.append({
            "bundle_id": f"B{group_index + 1:02d}",
            "components": components,
            "required_line_ids": required,
        })
    return {"inventory": inventory, "groups": groups}


def _solve_m3(data):
    stock = dict(data["inventory"])
    values = []
    for group in data["groups"]:
        components = group["components"]
        valid_bundle = group["required_line_ids"] == [item["id"] for item in components]
        enough = [stock[item["sku"]] >= item["quantity"] for item in components]
        values.extend("FULFILL" if available else "BACKORDER" for available in enough)
        if not valid_bundle:
            values.append("INVALID_BUNDLE")
        elif not all(enough):
            values.append("BACKORDER")
        else:
            values.append("FULFILL")
            for item in components:
                stock[item["sku"]] -= item["quantity"]
    return values


def _generate_c1(rng):
    events = []
    for index in range(DECISION_COUNT):
        kind = rng.choices(["DEPOSIT", "WITHDRAWAL", "FEE", "INTEREST"], weights=[4, 4, 1, 1])[0]
        event = {"id": f"C{index + 1:02d}", "kind": kind}
        if kind == "INTEREST":
            event["rate_bps"] = rng.choice([5, 10, 20])
        else:
            event["amount_cents"] = rng.randrange(100, 20_001)
        events.append(event)
    return {"opening_balance_cents": 250_000 + rng.randrange(50_001), "events": events}


def _solve_c1(data):
    balance = data["opening_balance_cents"]
    values = []
    for event in data["events"]:
        if event["kind"] == "DEPOSIT":
            balance += event["amount_cents"]
        elif event["kind"] in ("WITHDRAWAL", "FEE"):
            balance -= event["amount_cents"]
        else:
            balance += _round_ratio(balance * event["rate_bps"], 10_000)
        values.append(str(balance))
    return values


def _generate_c2(rng):
    movements = []
    kinds = ["RECEIPT", "SALE", "RETURN", "DAMAGE", "TRANSFER_OUT"]
    for index in range(DECISION_COUNT):
        movements.append({
            "id": f"M{index + 1:02d}",
            "kind": rng.choice(kinds),
            "quantity": rng.randrange(1, 21),
        })
    return {"opening_stock": 80 + rng.randrange(21), "movements": movements}


def _solve_c2(data):
    stock = data["opening_stock"]
    values = []
    for movement in data["movements"]:
        quantity = movement["quantity"]
        if movement["kind"] in ("RECEIPT", "RETURN"):
            stock += quantity
            status = "ACCEPT"
        elif quantity <= stock:
            stock -= quantity
            status = "ACCEPT"
        else:
            status = "REJECT"
        values.append(f"{stock}:{status}")
    return values


def _generate_c3(rng):
    periods = []
    for index in range(DECISION_COUNT):
        periods.append({
            "period": index + 1,
            "extra_payment_cents": rng.choices([0, 5_000, 10_000], weights=[8, 1, 1])[0],
        })
    return {
        "principal_cents": 1_500_000 + rng.randrange(100_001),
        "periodic_rate_bps": rng.choice([40, 50, 60]),
        "fixed_payment_cents": 32_000,
        "rounding": "half_up_cents",
        "periods": periods,
    }


def _solve_c3(data):
    principal = data["principal_cents"]
    values = []
    for period in data["periods"]:
        interest = _round_ratio(principal * data["periodic_rate_bps"], 10_000)
        due = principal + interest
        payment = min(due, data["fixed_payment_cents"] + period["extra_payment_cents"])
        principal = due - payment
        values.append(str(principal))
    return values


def _generate_g1(rng):
    employee_cycle = [None] * 12
    even_employees = [f"E{index:02d}" for index in range(0, 12, 2)]
    odd_employees = [f"E{index:02d}" for index in range(1, 12, 2)]
    rng.shuffle(even_employees)
    rng.shuffle(odd_employees)
    employee_cycle[::2] = even_employees
    employee_cycle[1::2] = odd_employees
    reference = [employee_cycle[slot % 12] for slot in range(DECISION_COUNT)]
    alternate = [employee_cycle[(slot + 2) % 12] for slot in range(DECISION_COUNT)]
    required_availability = {f"E{index:02d}": set() for index in range(12)}
    for slot, employee_id in enumerate(reference):
        required_availability[employee_id].add(slot)
    for slot, employee_id in enumerate(alternate):
        required_availability[employee_id].add(slot)
    employees = []
    for index in range(12):
        employee_id = f"E{index:02d}"
        optional = {
            slot for slot in range(DECISION_COUNT)
            if slot % 2 == index % 2 and rng.random() < 0.25
        }
        employees.append({
            "id": employee_id,
            "skills": ["OPS" if index % 2 == 0 else "CARE"],
            "available_slots": sorted(required_availability[employee_id] | optional),
            "max_shifts": 4,
        })
    slots = [{"id": f"S{slot:02d}", "required_skill": "OPS" if slot % 2 == 0 else "CARE", "start_hour": slot * 8} for slot in range(DECISION_COUNT)]
    return {"employees": employees, "slots": slots, "minimum_rest_hours": 16}, reference, alternate


def _validate_g1(data, values):
    employees = {item["id"]: item for item in data["employees"]}
    violations = []
    assignments = {}
    for index, (slot, employee_id) in enumerate(zip(data["slots"], values)):
        employee = employees.get(employee_id)
        if employee is None:
            violations.append(f"unknown_employee:{index}")
            continue
        if index not in employee["available_slots"]:
            violations.append(f"unavailable:{index}")
        if slot["required_skill"] not in employee["skills"]:
            violations.append(f"skill:{index}")
        assignments.setdefault(employee_id, []).append(slot["start_hour"])
    for employee_id, hours in assignments.items():
        if len(hours) > employees[employee_id]["max_shifts"]:
            violations.append(f"max_shifts:{employee_id}")
        if any(b - a < data["minimum_rest_hours"] for a, b in zip(sorted(hours), sorted(hours)[1:])):
            violations.append(f"rest:{employee_id}")
    return violations, 0


def _generate_g2(rng):
    regions = ["N", "S", "W"]
    warehouses = []
    for index in range(6):
        region = regions[index // 2]
        warehouses.append({
            "id": f"W{index}",
            "regions": [region],
            "capacity_orders": 8,
            "stock": {f"SKU{sku}": 100 for sku in range(4)},
            "cost_per_order": 10,
        })
    orders = []
    reference = []
    alternate = []
    region_counts = {region: 0 for region in regions}
    for index in range(DECISION_COUNT):
        region = regions[index % len(regions)]
        pair_start = regions.index(region) * 2
        side = region_counts[region] % 2
        region_counts[region] += 1
        orders.append({"id": f"O{index:02d}", "region": region, "sku": f"SKU{rng.randrange(4)}", "quantity": rng.randrange(1, 5)})
        reference.append(f"W{pair_start + side}")
        alternate.append(f"W{pair_start + (1 - side)}")
    return {"warehouses": warehouses, "orders": orders, "maximum_total_cost": 480}, reference, alternate


def _validate_g2(data, values):
    warehouses = {item["id"]: item for item in data["warehouses"]}
    counts = {key: 0 for key in warehouses}
    stock_used = {key: {} for key in warehouses}
    violations = []
    total_cost = 0
    for index, (order, warehouse_id) in enumerate(zip(data["orders"], values)):
        warehouse = warehouses.get(warehouse_id)
        if warehouse is None:
            violations.append(f"unknown_warehouse:{index}")
            continue
        counts[warehouse_id] += 1
        total_cost += warehouse["cost_per_order"]
        if order["region"] not in warehouse["regions"]:
            violations.append(f"delivery:{index}")
        used = stock_used[warehouse_id].get(order["sku"], 0) + order["quantity"]
        stock_used[warehouse_id][order["sku"]] = used
    for warehouse_id, warehouse in warehouses.items():
        if counts[warehouse_id] > warehouse["capacity_orders"]:
            violations.append(f"capacity:{warehouse_id}")
        for sku, used in stock_used[warehouse_id].items():
            if used > warehouse["stock"].get(sku, 0):
                violations.append(f"stock:{warehouse_id}:{sku}")
    if total_cost > data["maximum_total_cost"]:
        violations.append("objective:cost")
    return violations, total_cost


def _generate_g3(rng):
    even_language = rng.choice(["EN", "JA"])
    odd_language = "JA" if even_language == "EN" else "EN"
    tables = [{"id": f"T{index}", "capacity": 6, "accessible": index % 2 == 0, "language": even_language if index % 2 == 0 else odd_language} for index in range(8)]
    team_names = rng.sample([f"TEAM{index}" for index in range(12)], 6)
    attendees = []
    for index in range(DECISION_COUNT):
        attendees.append({
            "id": f"A{index:02d}",
            "team": team_names[index // 8],
            "needs_accessible": index % 2 == 0,
            "language": even_language if index % 2 == 0 else odd_language,
            "host": index < 8,
        })
    reference = [f"T{index % 8}" for index in range(DECISION_COUNT)]
    alternate = [f"T{(index + 2) % 8}" for index in range(DECISION_COUNT)]
    return {"tables": tables, "attendees": attendees, "maximum_language_mismatches": 0}, reference, alternate


def _validate_g3(data, values):
    tables = {item["id"]: item for item in data["tables"]}
    occupants = {key: [] for key in tables}
    violations = []
    language_mismatches = 0
    for index, (attendee, table_id) in enumerate(zip(data["attendees"], values)):
        table = tables.get(table_id)
        if table is None:
            violations.append(f"unknown_table:{index}")
            continue
        occupants[table_id].append(attendee)
        if attendee["needs_accessible"] and not table["accessible"]:
            violations.append(f"accessibility:{index}")
        if attendee["language"] != table["language"]:
            language_mismatches += 1
    for table_id, seated in occupants.items():
        if len(seated) > tables[table_id]["capacity"]:
            violations.append(f"capacity:{table_id}")
        teams = [item["team"] for item in seated]
        if len(teams) != len(set(teams)):
            violations.append(f"team_separation:{table_id}")
        if sum(item["host"] for item in seated) != 1:
            violations.append(f"host:{table_id}")
    if language_mismatches > data["maximum_language_mismatches"]:
        violations.append("objective:language")
    return violations, language_mismatches


GENERATORS = {
    "D1": _generate_d1, "D2": _generate_d2, "D3": _generate_d3,
    "M1": _generate_m1, "M2": _generate_m2, "M3": _generate_m3,
    "C1": _generate_c1, "C2": _generate_c2, "C3": _generate_c3,
    "G1": _generate_g1, "G2": _generate_g2, "G3": _generate_g3,
}
SOLVERS = {
    "D1": _solve_d1, "D2": _solve_d2, "D3": _solve_d3,
    "M1": _solve_m1, "M2": _solve_m2, "M3": _solve_m3,
    "C1": _solve_c1, "C2": _solve_c2, "C3": _solve_c3,
}
GLOBAL_VALIDATORS = {"G1": _validate_g1, "G2": _validate_g2, "G3": _validate_g3}


INSTRUCTIONS = {
    "D1": "Map each transaction category through account_rules.",
    "D2": "Route ENTERPRISE by region plus ENT; otherwise use a non-EN language or the region, then append product and issue. Join the parts with underscores, for example US_ENT_PAY_ACCESS or JP_DATA_OUTAGE.",
    "D3": "Reject sanctioned suppliers or restricted jurisdictions; review nonapproved suppliers or uncontracted orders above the category threshold; otherwise approve. Output APPROVE, REVIEW, or REJECT.",
    "M1": "For each item recompute net and half-up tax, with price errors taking precedence over tax errors. Validate each subtotal against the three correct item totals. Return one value per line: PRICE_ERROR, TAX_ERROR, or VALID for ITEM lines, and SUBTOTAL_ERROR or VALID for SUBTOTAL lines.",
    "M2": "In source order apply receipt, item-limit, and cumulative approved daily-meal-cap rules, returning decision and reason as one string: APPROVE:OK, DENY:NO_RECEIPT, DENY:ITEM_LIMIT, or DENY:DAILY_MEAL_CAP.",
    "M3": "Check component stock and bundle membership per group. Reserve stock only when the complete bundle is valid and fulfillable. For each group return one value per component, FULFILL if current stock covers its quantity or else BACKORDER, then one value for the group: INVALID_BUNDLE, BACKORDER, or FULFILL.",
    "C1": "Replay all cash events in order. Interest is rounded half up to cents. Return the balance in cents after every event.",
    "C2": "Replay inventory movements in order. Reject outbound movements that would make stock negative. Return stock and ACCEPT or REJECT after every movement as STOCK:STATUS, for example 71:ACCEPT.",
    "C3": "For each period compute half-up interest, apply the fixed and extra payment without paying beyond the amount due, and return ending principal cents.",
    "G1": "Assign one available, skilled employee to every slot while respecting maximum shifts and minimum rest hours.",
    "G2": "Assign one eligible warehouse to every order without exceeding order capacity or SKU stock and keep total cost within the registered maximum.",
    "G3": "Assign every attendee to one table, respecting capacity, accessibility, team separation, one host per table, and the language-mismatch bound.",
}


def _answer(values):
    return {"values": [str(value) for value in values]}


def make_fixture(problem_id, fixture_index, base_seed=BASE_SEED):
    if problem_id not in PROBLEMS:
        raise ValueError(f"unknown problem id: {problem_id}")
    if int(fixture_index) < 0:
        raise ValueError("fixture_index must be nonnegative")
    seed = _seed(problem_id, fixture_index, base_seed)
    generated = GENERATORS[problem_id](random.Random(seed))
    alternate = None
    if problem_id in GLOBAL_VALIDATORS:
        input_data, reference_values, alternate_values = generated
        reference = _answer(reference_values)
        alternate = _answer(alternate_values)
        scoring_mode = "constraint_objective"
    else:
        input_data = generated
        reference = _answer(SOLVERS[problem_id](input_data))
        scoring_mode = "exact"
    dependency_class, name = PROBLEMS[problem_id]
    prompt = (
        "Return exactly one compact JSON object with the form {\"values\":[\"...\"]} "
        "and no other text. Produce exactly 48 string values in source order. "
        + INSTRUCTIONS[problem_id]
        + " Input:"
        + compact_json(input_data)
    )
    fixture = {
        "schema_version": SCHEMA_VERSION,
        "case_id": f"business-{problem_id.lower()}-{int(fixture_index):03d}",
        "problem_id": problem_id,
        "problem_name": name,
        "dependency_class": dependency_class,
        "fixture_index": int(fixture_index),
        "seed": seed,
        "decision_count": DECISION_COUNT,
        "scoring_mode": scoring_mode,
        "input": input_data,
        "prompt": prompt,
        "prompt_hash": stable_hash(prompt),
        "reference_answer": reference,
    }
    if alternate is not None:
        fixture["alternate_valid_answer"] = alternate
    fixture["fixture_hash"] = fixture_hash(fixture)
    return fixture


def _answer_values(answer):
    if not isinstance(answer, dict) or set(answer) != {"values"}:
        return None
    values = answer.get("values")
    if not isinstance(values, list) or len(values) != DECISION_COUNT:
        return None
    if not all(isinstance(value, str) for value in values):
        return None
    return values


def evaluate_answer(fixture, answer):
    values = _answer_values(answer)
    exact_match = answer == fixture["reference_answer"] if values is not None else False
    if values is None:
        return {
            "valid": False,
            "exact_match": False,
            "per_decision_correct": 0,
            "first_error": 0,
            "constraint_violations": ["canonical_answer_contract"],
            "objective_value": None,
        }
    problem_id = fixture["problem_id"]
    if problem_id in SOLVERS:
        expected = [str(value) for value in SOLVERS[problem_id](fixture["input"])]
        correct = [actual == wanted for actual, wanted in zip(values, expected)]
        first_error = next((index for index, matched in enumerate(correct) if not matched), None)
        return {
            "valid": all(correct),
            "exact_match": exact_match,
            "per_decision_correct": sum(correct),
            "first_error": first_error,
            "constraint_violations": [],
            "objective_value": None,
        }
    violations, objective = GLOBAL_VALIDATORS[problem_id](fixture["input"], values)
    return {
        "valid": not violations,
        "exact_match": exact_match,
        "per_decision_correct": None,
        "first_error": None,
        "constraint_violations": violations,
        "objective_value": objective,
    }


def validate_fixture(fixture):
    required = {
        "schema_version", "case_id", "problem_id", "problem_name",
        "dependency_class", "fixture_index", "seed", "decision_count",
        "scoring_mode", "input", "prompt", "prompt_hash",
        "reference_answer", "fixture_hash",
    }
    if not isinstance(fixture, dict) or not required <= set(fixture):
        return False
    if fixture["schema_version"] != SCHEMA_VERSION or fixture["problem_id"] not in PROBLEMS:
        return False
    if fixture["decision_count"] != DECISION_COUNT:
        return False
    if fixture["prompt_hash"] != stable_hash(fixture["prompt"]):
        return False
    if fixture["fixture_hash"] != fixture_hash(fixture):
        return False
    problem_offset = PROBLEM_IDS.index(fixture["problem_id"]) * 100_003
    fixture_offset = int(fixture["fixture_index"]) * 9_973
    registered_base_seed = int(fixture["seed"]) - problem_offset - fixture_offset
    regenerated = make_fixture(
        fixture["problem_id"], fixture["fixture_index"], registered_base_seed
    )
    if compact_json(fixture) != compact_json(regenerated):
        return False
    if not evaluate_answer(fixture, fixture["reference_answer"])["valid"]:
        return False
    if fixture["problem_id"] in GLOBAL_VALIDATORS:
        alternate = fixture.get("alternate_valid_answer")
        if alternate == fixture["reference_answer"] or not evaluate_answer(fixture, alternate)["valid"]:
            return False
    return True


def build_manifest(cases_per_problem=DEFAULT_CASES_PER_PROBLEM, base_seed=BASE_SEED):
    cases_per_problem = int(cases_per_problem)
    if cases_per_problem <= 0:
        raise ValueError("cases_per_problem must be positive")
    fixtures = [
        make_fixture(problem_id, fixture_index, base_seed)
        for problem_id in PROBLEM_IDS
        for fixture_index in range(cases_per_problem)
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "base_seed": int(base_seed),
        "cases_per_problem": cases_per_problem,
        "problem_ids": list(PROBLEM_IDS),
        "fixtures": fixtures,
    }
    manifest["manifest_hash"] = stable_hash(manifest)
    return manifest


def verify_manifest(manifest):
    if not isinstance(manifest, dict):
        return False
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if manifest.get("manifest_hash") != stable_hash(unsigned):
        return False
    if manifest.get("schema_version") != SCHEMA_VERSION:
        return False
    if manifest.get("problem_ids") != list(PROBLEM_IDS):
        return False
    base_seed = manifest.get("base_seed")
    if not isinstance(base_seed, int) or isinstance(base_seed, bool):
        return False
    fixtures = manifest.get("fixtures")
    cases_per_problem = manifest.get("cases_per_problem")
    if (
        not isinstance(fixtures, list)
        or not isinstance(cases_per_problem, int)
        or isinstance(cases_per_problem, bool)
        or cases_per_problem <= 0
    ):
        return False
    if len(fixtures) != len(PROBLEM_IDS) * cases_per_problem:
        return False
    if len({fixture.get("case_id") for fixture in fixtures if isinstance(fixture, dict)}) != len(fixtures):
        return False
    expected_pairs = {(problem_id, index) for problem_id in PROBLEM_IDS for index in range(cases_per_problem)}
    actual_pairs = {(fixture.get("problem_id"), fixture.get("fixture_index")) for fixture in fixtures if isinstance(fixture, dict)}
    seeds_match_header = all(
        isinstance(fixture, dict)
        and fixture.get("problem_id") in PROBLEMS
        and isinstance(fixture.get("fixture_index"), int)
        and not isinstance(fixture.get("fixture_index"), bool)
        and fixture.get("seed") == _seed(
            fixture.get("problem_id"), fixture.get("fixture_index"), base_seed
        )
        for fixture in fixtures
    )
    return (
        actual_pairs == expected_pairs
        and seeds_match_header
        and all(validate_fixture(fixture) for fixture in fixtures)
    )


def _write_manifest(manifest, output):
    serialized = compact_json(manifest) + "\n"
    if output == "-":
        sys.stdout.write(serialized)
    else:
        Path(output).write_text(serialized, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate")
    generate.add_argument("--output", default="-")
    generate.add_argument("--cases-per-problem", type=int, default=DEFAULT_CASES_PER_PROBLEM)
    generate.add_argument("--base-seed", type=int, default=BASE_SEED)
    validate = subparsers.add_parser("validate")
    validate.add_argument("manifest")
    validate.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "generate":
        manifest = build_manifest(args.cases_per_problem, args.base_seed)
        _write_manifest(manifest, args.output)
        return 0
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    valid = verify_manifest(manifest)
    report = {"status": "ok" if valid else "failed", "fixture_count": len(manifest.get("fixtures", []))}
    if args.json:
        print(compact_json(report))
    else:
        print(f"{report['status']}: {report['fixture_count']} fixtures")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
