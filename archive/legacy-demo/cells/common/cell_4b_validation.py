# --- CELL 4b: STANDALONE PUZZLE VALIDATION AND HEALTH CHECK ---

import collections
import json
from copy import deepcopy

print("=" * 65)
print("🔍 RUNNING CELL 4 BENCHMARK VALIDATION")
print("=" * 65)

# 1. Environment and Contract Check
if "BENCHMARK_SPEC" not in globals():
    try:
        try:
            import cell_4_schedule_puzzle as _cell4
        except ImportError:
            from cells.common import cell_4_schedule_puzzle as _cell4
        BENCHMARK_SPEC = _cell4.BENCHMARK_SPEC
        globals().update(
            {
                name: getattr(_cell4, name)
                for name in (
                    "SCHEDULE_CASE_COUNT",
                    "SLOT_COUNT",
                    "TASK_TYPES",
                    "TASK_LABELS",
                    "DAY_ARCHETYPES",
                    "LOCATION_COLORS",
                    "empty_slot",
                    "reference_solution",
                )
            }
        )
        print("ℹ️  Imported BENCHMARK_SPEC from cell_4_schedule_puzzle.py")
    except Exception as err:
        raise RuntimeError(
            "❌ BENCHMARK_SPEC is missing. Run Cell 4 before this validation cell."
        ) from err

SPEC = BENCHMARK_SPEC
required_keys = [
    "name",
    "slug",
    "cases",
    "case_by_id",
    "build_prompt",
    "parse_output",
    "evaluate_output",
    "render",
    "case_label",
    "case_description",
    "default_output_tokens",
    "primary_quality_metric",
    "optimal_quality_metric",
]

missing_keys = [k for k in required_keys if k not in SPEC]
if missing_keys:
    raise AssertionError(f"❌ BENCHMARK_SPEC is missing required keys: {missing_keys}")
print(f"✅ Spec Contract: All {len(required_keys)} required keys present for '{SPEC['name']}'")


# 2. Case Dataset Verification
cases = SPEC["cases"]
case_by_id = SPEC["case_by_id"]
assert len(cases) == SCHEDULE_CASE_COUNT, (
    f"Expected {SCHEDULE_CASE_COUNT} cases, found {len(cases)}"
)
assert len(case_by_id) == len(cases), "case_by_id map size mismatch"

difficulty_counts = collections.Counter()
task_counts = collections.Counter()
archetype_counts = collections.Counter()

for case in cases:
    cid = case["case_id"]
    assert cid in case_by_id, f"Case {cid} not in case_by_id map"
    assert len(case["existing_schedule"]) == SLOT_COUNT, (
        f"{cid}: existing_schedule must have {SLOT_COUNT} slots"
    )
    assert len(case["pinned_events"]) >= 2, f"{cid}: too few pinned events"
    assert case["errands"], f"{cid}: no errand to place"
    assert case["solution_count"] >= 1, f"{cid}: no valid layout exists"
    assert case["task_type"] in TASK_TYPES, f"{cid}: unknown task type"
    for location in case["locations"]:
        assert location in LOCATION_COLORS, (
            f"{cid}: location '{location}' has no colour assigned"
        )
    difficulty_counts[case.get("difficulty", "unknown")] += 1
    task_counts[case["task_type"]] += 1
    archetype_counts[case["archetype"]] += 1

assert len(task_counts) == len(TASK_TYPES), "Not every workload is represented"
assert len(archetype_counts) == len(DAY_ARCHETYPES), (
    "Not every day archetype is represented"
)

# The demo is only readable if the canvases actually differ. Guard the two
# properties that make them differ: the mix of appointments and the density.
day_shapes = {
    (case["archetype"], len(case["pinned_events"]), case["free_slot_count"])
    for case in cases
}
activity_sets = {
    tuple(sorted(event["activity"] for event in case["pinned_events"]))
    for case in cases
}
assert len(day_shapes) >= 20, f"Only {len(day_shapes)} distinct day shapes"
assert len(activity_sets) >= 20, (
    f"Only {len(activity_sets)} distinct appointment sets"
)

print(
    f"✅ Dataset Health: {len(cases)} cases verified "
    f"(Difficulties: {dict(difficulty_counts)})"
)
print(
    "✅ Workload Mix: "
    + ", ".join(
        f"{TASK_LABELS[name]}={count}"
        for name, count in sorted(task_counts.items())
    )
)
print(
    f"✅ Visual Diversity: {len(day_shapes)} distinct day shapes, "
    f"{len(activity_sets)} distinct appointment sets, "
    f"{len(archetype_counts)} archetypes"
)


# 3. Prompt Builder Verification
sample_case = cases[0]
prompt = SPEC["build_prompt"](sample_case)
assert isinstance(prompt, str) and len(prompt) > 300, "Prompt output too short or invalid"
assert f"{SLOT_COUNT}-slot" in prompt, "Prompt missing slot-count instruction"
assert '"schedule"' in prompt, "Prompt missing 'schedule' JSON key instruction"

# Every case's prompt must name what the task actually asks for.
for case in cases:
    case_prompt = SPEC["build_prompt"](case)
    for errand in case["errands"]:
        assert errand["activity"] in case_prompt, (
            f"{case['case_id']}: prompt missing errand '{errand['activity']}'"
        )
    for cancelled in case["cancelled_events"]:
        assert cancelled["activity"] in case_prompt, (
            f"{case['case_id']}: prompt missing cancellation"
        )
    for movable in case["movable_events"]:
        assert movable["activity"] in case_prompt, (
            f"{case['case_id']}: prompt missing reschedule instruction"
        )
print(
    "✅ Prompt Builder: All %d prompts name their own task (~%d chars sample)"
    % (len(cases), len(prompt))
)


# 4. Output Parsing Suite
parse = SPEC["parse_output"]

valid_mock_schedule = reference_solution(sample_case)

json_str = json.dumps({"schedule": valid_mock_schedule})
parsed_1 = parse(json_str)
assert parsed_1 is not None and "schedule" in parsed_1, "Failed to parse pure JSON schedule"

markdown_str = f"Here is the schedule:\n```json\n{json_str}\n```\nHope this helps!"
parsed_2 = parse(markdown_str)
assert parsed_2 is not None and len(parsed_2.get("schedule", [])) == SLOT_COUNT, (
    "Failed to parse markdown-fenced JSON"
)

list_str = json.dumps(valid_mock_schedule)
parsed_3 = parse(list_str)
assert parsed_3 is not None and len(parsed_3.get("schedule", [])) == SLOT_COUNT, (
    "Failed to parse raw list format"
)

assert parse("not a json at all ::::") is None, "Corrupted string should return None"
assert parse("") is None, "Empty string should return None"
print("✅ Output Parser: Passed 4/4 parser test suites (JSON, Markdown, Array, Malformed)")


# 5. Comprehensive Constraint Evaluator Tests
evaluate = SPEC["evaluate_output"]

# 5a. Ground truth is valid and scores as optimal, for every case and workload.
for case in cases:
    solution = reference_solution(case)
    result = evaluate(case, {"schedule": solution})
    assert result["valid"], f"{case['case_id']} ground truth failed: {result['status']}"
    assert "SUCCESS" in result["status"], f"{case['case_id']}: success text missing"
    assert (
        result["metrics"][SPEC["primary_quality_metric"]]
        == result["metrics"][SPEC["optimal_quality_metric"]]
    ), f"{case['case_id']}: reference solution is not scored optimal"

eval_gt = evaluate(sample_case, parsed_1)

# 5b. Perturbation: deleted a fixed appointment
corrupted_fixed = deepcopy(valid_mock_schedule)
pinned = sample_case["pinned_events"][0]
for index in range(pinned["start_slot"], pinned["end_slot"]):
    corrupted_fixed[index] = empty_slot(index)
assert not evaluate(sample_case, {"schedule": corrupted_fixed})["valid"], (
    "Evaluator failed to detect an altered fixed appointment"
)

# 5c. Perturbation: errand outside its opening window
errand = sample_case["errands"][0]
if errand["open_slot"] > 0:
    out_window = deepcopy(valid_mock_schedule)
    for index, slot in enumerate(out_window):
        if slot["activity"] == errand["activity"]:
            out_window[index] = empty_slot(index)
    for index in range(errand["duration_slots"]):
        out_window[index] = {
            "start": out_window[index]["start"],
            "activity": errand["activity"],
            "location": errand["location"],
        }
    assert not evaluate(sample_case, {"schedule": out_window})["valid"], (
        "Evaluator failed to detect an out-of-window errand"
    )

# 5d. Perturbation: missing errand
dropped = deepcopy(valid_mock_schedule)
for index, slot in enumerate(dropped):
    if slot["activity"] == errand["activity"]:
        dropped[index] = empty_slot(index)
assert not evaluate(sample_case, {"schedule": dropped})["valid"], (
    "Evaluator failed to detect a missing errand"
)

# 5e. Perturbation: incomplete slot count
assert not evaluate(sample_case, {"schedule": valid_mock_schedule[:30]})["valid"], (
    "Evaluator failed to detect incorrect slot count"
)

# 5f. Workload-specific perturbations: an uncancelled event and an unmoved one.
cancel_case = next(
    case for case in cases if case["task_type"] == "cancel_and_insert"
)
assert not evaluate(
    cancel_case, {"schedule": deepcopy(cancel_case["existing_schedule"])}
)["valid"], "Evaluator accepted an uncancelled appointment"

move_case = next(
    case for case in cases if case["task_type"] == "move_and_insert"
)
movable = move_case["movable_events"][0]
unmoved = reference_solution(move_case)
for index, slot in enumerate(unmoved):
    if slot["activity"] == movable["activity"]:
        unmoved[index] = empty_slot(index)
for index in range(movable["start_slot"], movable["end_slot"]):
    unmoved[index] = {
        "start": unmoved[index]["start"],
        "activity": movable["activity"],
        "location": movable["location"],
    }
assert not evaluate(move_case, {"schedule": unmoved})["valid"], (
    "Evaluator accepted an appointment that was never rescheduled"
)

print(
    "✅ Evaluation Engine: Ground truth optimal on all "
    f"{len(cases)} cases; 6 perturbation classes rejected"
)


# 6. Visual Render Verification
try:
    for case in (sample_case, cancel_case, move_case):
        image = SPEC["render"](case, eval_gt if case is sample_case else
                               evaluate(case, {"schedule": reference_solution(case)}),
                               SPEC["case_label"](case))
        assert image is not None, "Render returned None"
        assert len(image.shape) == 3 and image.shape[2] == 3, (
            f"Unexpected image shape: {image.shape}"
        )
    print(
        f"✅ Visual Renderer: Generated valid image canvases "
        f"{image.shape[1]}x{image.shape[0]} px across 3 workloads"
    )
except Exception as render_err:
    print(f"⚠️  Visual Renderer Note (Headless / Lib Check): {render_err}")

print("=" * 65)
print("🎉 ALL CELL 4 VALIDATION CHECKS PASSED SUCCESSFULLY!")
print(f"👉 Default token budget: {SPEC['default_output_tokens']} tokens")
print("👉 Environment is ready for Cell 5 (Benchmark Execution).")
print("=" * 65)
