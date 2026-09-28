# --- CELL 6: UI CALLBACK ADAPTERS ---

# This cell contains no widgets and launches no server. It keeps UI-specific
# formatting separate from the model engine so failures are easier to isolate.

for required_name in (
    "BENCHMARK_SPEC",
    "PUZZLE_CASES",
    "PUZZLE_CASE_BY_ID",
    "run_single_demo",
    "run_benchmark_suite",
):
    if required_name not in globals():
        raise RuntimeError(
            f"{required_name} is missing. Run Cells 4 and 5 first."
        )


UI_CASE_OPTIONS = [
    (BENCHMARK_SPEC["case_label"](case), case["case_id"])
    for case in PUZZLE_CASES
]


def ui_case_description(case_id):
    case = PUZZLE_CASE_BY_ID[case_id]
    return (
        f"### {case_id}\n\n"
        + BENCHMARK_SPEC["case_description"](case)
    )


def ui_run_single(case_id, attempt):
    attempt = max(1, int(attempt))
    ar_result, diff_result, summary = run_single_demo(
        case_id=case_id,
        attempt=attempt,
    )
    return (
        ar_result["image"],
        diff_result["image"],
        summary,
        ar_result["raw_output"],
        diff_result["raw_output"],
    )


def ui_run_suite(case_count, attempts):
    case_count = max(1, min(int(case_count), len(PUZZLE_CASES)))
    attempts = max(1, int(attempts))
    _, summary, rows, result_path = run_benchmark_suite(
        case_count=case_count,
        attempts=attempts,
    )
    table = [
        [
            row["model"],
            row["attempts"],
            f"{row['success_rate']:.1%}",
            f"{row['optimal_rate']:.1%}",
            round(row["median_response_seconds"], 2),
        ]
        for row in rows
    ]
    return summary, table, result_path


print(f"✅ Cell 6: UI adapters ready for {PUZZLE_NAME}")
print("Run Cell 7 to launch the browser interface.")
