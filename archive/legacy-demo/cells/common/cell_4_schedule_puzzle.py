# --- CELL 4: SCHEDULE PUZZLE DEFINITION ---

import itertools
import json
import os
import random
from copy import deepcopy

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


# Cell 5 consumes only BENCHMARK_SPEC. To add a new puzzle later, copy this
# file and implement the same small contract at the bottom.
SCHEDULE_CASE_COUNT = 50
SCHEDULE_CASE_SEED = 20260814
SLOT_MINUTES = 30
SLOTS_PER_DAY = 32
DAY_START_MINUTES = 8 * 60

# TASK-005 (output-length crossover sweep). The model must emit every slot, so
# the horizon is the dial that sets output length without changing the task,
# the prompt shape, or the evaluator. One day (32 slots, ~510 output tokens) is
# the shipped default; the lab sweeps it upward via the environment variable.
SCHEDULE_HORIZON_DAYS = max(1, int(os.environ.get("SCHEDULE_HORIZON_DAYS", "1")))
SLOT_COUNT = SLOTS_PER_DAY * SCHEDULE_HORIZON_DAYS

FREE_ACTIVITY = "Free"
FREE_LOCATION = "None"

DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def day_label(day_index):
    """Unique per day. Weekday names alias past a week (day 0 and day 7 are
    both "Mon"), which would collide slot labels and activity names alike."""
    if SCHEDULE_HORIZON_DAYS <= len(DAY_NAMES):
        return DAY_NAMES[day_index]
    return f"D{day_index + 1}"


def minutes_to_clock(minutes):
    minutes %= 24 * 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def slot_clock(slot_index):
    """Label for a slot, unique across the horizon so a multi-day canvas
    cannot alias two slots onto the same "start" string."""
    day_index, offset = divmod(slot_index, SLOTS_PER_DAY)
    clock = minutes_to_clock(DAY_START_MINUTES + offset * SLOT_MINUTES)
    if SCHEDULE_HORIZON_DAYS == 1:
        return clock
    return f"{day_label(day_index)} {clock}"


SLOT_START_TIMES = [slot_clock(index) for index in range(SLOT_COUNT)]

HORIZON_NOUN = (
    "daily schedule" if SCHEDULE_HORIZON_DAYS == 1
    else f"{SCHEDULE_HORIZON_DAYS}-day schedule"
)
HORIZON_RANGE = f"from {SLOT_START_TIMES[0]} to {SLOT_START_TIMES[-1]}"


def empty_slot(index):
    return {
        "start": SLOT_START_TIMES[index],
        "activity": FREE_ACTIVITY,
        "location": FREE_LOCATION,
    }


# ---------------------------------------------------------
# Day archetypes
#
# Every case used to draw from one 6-event template, so all 50 rendered
# schedules looked alike. Each archetype below has its own vocabulary,
# location set, event count and density, which is what makes the canvases
# visually distinguishable at a glance.
# ---------------------------------------------------------

# (activity, location, min_slots, max_slots, earliest_slot, latest_start_slot)
DAY_ARCHETYPES = {
    "office_day": {
        "label": "Office day",
        "event_count": (5, 7),
        "pool": [
            ("Standup", "Office", 1, 1, 0, 2),
            ("Design review", "Office", 2, 3, 2, 8),
            ("Focus block", "Office", 3, 5, 3, 12),
            ("Lunch meeting", "Cafe", 2, 2, 7, 11),
            ("1:1 with manager", "Office", 1, 1, 12, 18),
            ("Client call", "Office", 1, 2, 13, 20),
            ("Gym", "Gym", 2, 3, 20, 26),
            ("Dinner", "Home", 2, 2, 22, 28),
        ],
    },
    "parent_day": {
        "label": "Parent day",
        "event_count": (6, 8),
        "pool": [
            ("Breakfast", "Home", 1, 2, 0, 1),
            ("School dropoff", "School", 1, 1, 1, 3),
            ("Remote work", "Home", 3, 4, 3, 9),
            ("Physio", "Clinic", 1, 2, 8, 14),
            ("School pickup", "School", 1, 1, 14, 17),
            ("Soccer practice", "Field", 2, 3, 17, 22),
            ("Dinner", "Home", 2, 2, 22, 26),
            ("Bedtime routine", "Home", 1, 2, 27, 30),
        ],
    },
    "clinic_day": {
        "label": "Clinic day",
        "event_count": (4, 6),
        "pool": [
            ("Fasting bloodwork", "Lab", 1, 1, 0, 2),
            ("Breakfast", "Cafe", 1, 2, 2, 5),
            ("Specialist consult", "Clinic", 2, 3, 4, 12),
            ("Imaging", "Hospital", 2, 4, 8, 18),
            ("Physio session", "Clinic", 1, 2, 16, 24),
            ("Dinner", "Home", 2, 2, 24, 29),
        ],
    },
    "wfh_day": {
        "label": "Work from home",
        "event_count": (3, 4),
        "pool": [
            ("Breakfast", "Home", 1, 2, 0, 2),
            ("Deep work", "Home", 4, 6, 3, 10),
            ("Team sync", "Home", 1, 1, 11, 18),
            ("Afternoon block", "Home", 3, 5, 14, 20),
            ("Dinner", "Home", 2, 2, 24, 29),
        ],
    },
    "travel_day": {
        "label": "Travel day",
        "event_count": (5, 6),
        "pool": [
            ("Hotel checkout", "Hotel", 1, 1, 0, 2),
            ("Airport transfer", "Airport", 2, 2, 2, 6),
            ("Flight", "Airport", 4, 6, 5, 12),
            ("Client meeting", "Client Site", 2, 3, 14, 20),
            ("Team dinner", "Restaurant", 2, 3, 22, 27),
            ("Hotel checkin", "Hotel", 1, 1, 27, 30),
        ],
    },
    "student_day": {
        "label": "Student day",
        "event_count": (5, 7),
        "pool": [
            ("Lecture", "Campus", 2, 3, 0, 4),
            ("Lab session", "Lab", 3, 4, 4, 10),
            ("Library block", "Library", 2, 4, 8, 16),
            ("Seminar", "Campus", 1, 2, 12, 20),
            ("Study group", "Library", 2, 3, 18, 24),
            ("Shift at cafe", "Cafe", 3, 4, 20, 26),
            ("Dinner", "Dorm", 1, 2, 26, 30),
        ],
    },
}

ARCHETYPE_NAMES = sorted(DAY_ARCHETYPES)

# Errand pool, tagged so a case can pick one whose location is not already
# in the day. That is what makes the travel term bite.
ERRAND_OPTIONS = [
    ("Pick up prescription", "Pharmacy", 1, 2),
    ("Buy groceries", "Market", 1, 3),
    ("Drop off package", "Post Office", 1, 1),
    ("Collect dry cleaning", "Dry Cleaner", 1, 1),
    ("Car service", "Garage", 2, 4),
    ("Bank appointment", "Bank", 1, 2),
    ("Vet visit", "Vet", 1, 2),
    ("Haircut", "Salon", 1, 2),
]

TASK_TYPES = ("insert_one", "insert_two", "cancel_and_insert", "move_and_insert")

TASK_LABELS = {
    "insert_one": "insert",
    "insert_two": "insert x2",
    "cancel_and_insert": "cancel+insert",
    "move_and_insert": "move+insert",
}


# ---------------------------------------------------------
# Travel model
# ---------------------------------------------------------

def travel_key(first, second):
    return "|".join(sorted((first, second)))


def travel_minutes(case, first, second):
    if first == second:
        return 0
    return int(case["travel_minutes"][travel_key(first, second)])


def build_travel_table(rng, locations):
    table = {}
    for first_index, first in enumerate(locations):
        for second in locations[first_index + 1:]:
            table[travel_key(first, second)] = rng.choice((30, 30, 60, 90))
    return table


def chain_travel_minutes(case, blocks):
    """Total travel over an ordered list of blocks, or None if infeasible."""
    total = 0
    for previous, current in zip(blocks, blocks[1:]):
        needed = travel_minutes(
            case, previous["location"], current["location"]
        )
        available = (
            current["start_slot"] - previous["end_slot"]
        ) * SLOT_MINUTES
        if available < needed:
            return None
        total += needed
    return total


# ---------------------------------------------------------
# Day construction
# ---------------------------------------------------------

def build_day(rng, archetype_name, slot_offset=0):
    """One day's appointments, shifted into its place in the horizon."""
    archetype = DAY_ARCHETYPES[archetype_name]
    low, high = archetype["event_count"]
    wanted = rng.randint(low, min(high, len(archetype["pool"])))
    chosen = rng.sample(archetype["pool"], wanted)

    events = []
    for activity, location, min_slots, max_slots, earliest, latest in chosen:
        duration = rng.randint(min_slots, max_slots)
        latest_start = min(latest, SLOTS_PER_DAY - duration)
        if latest_start < earliest:
            continue
        start_slot = slot_offset + rng.randint(earliest, latest_start)
        events.append(
            {
                "activity": activity,
                "location": location,
                "start_slot": start_slot,
                "duration_slots": duration,
                "end_slot": start_slot + duration,
            }
        )

    events.sort(key=lambda event: event["start_slot"])

    # Drop overlaps rather than retrying the whole draw; the sampler is
    # deliberately loose so densities vary between cases.
    kept = []
    for event in events:
        if kept and event["start_slot"] < kept[-1]["end_slot"]:
            continue
        kept.append(event)
    return kept


def build_horizon(rng, archetype_name):
    """Appointments across the whole horizon.

    At the default one-day horizon this is exactly `build_day`. Longer
    horizons draw a fresh archetype per day, so a 5-day canvas is a week of
    different-looking days rather than the same day repeated. Activity names
    are suffixed per day because the evaluator keys blocks by activity name
    and would otherwise see one appointment repeated across days.
    """
    if SCHEDULE_HORIZON_DAYS == 1:
        return build_day(rng, archetype_name, slot_offset=0)

    events = []
    for day_index in range(SCHEDULE_HORIZON_DAYS):
        day_archetype = (
            archetype_name if day_index == 0
            else rng.choice(ARCHETYPE_NAMES)
        )
        label = day_label(day_index)
        for event in build_day(
            rng, day_archetype, slot_offset=day_index * SLOTS_PER_DAY
        ):
            event["activity"] = f"{event['activity']} ({label})"
            events.append(event)
    return events


def free_span_candidates(occupied, duration, window=None):
    """Start slots where a block of `duration` fits without overlapping."""
    lower = 0 if window is None else window[0]
    upper = SLOT_COUNT if window is None else window[1]
    candidates = []
    for start_slot in range(lower, upper - duration + 1):
        span = range(start_slot, start_slot + duration)
        if any(slot in occupied for slot in span):
            continue
        candidates.append(start_slot)
    return candidates


def enumerate_arrangements(case, pinned, floating, limit=200000):
    """All feasible full-day layouts, as (blocks, total_travel_minutes).

    `floating` blocks carry candidate start slots; pinned blocks are fixed.
    """
    occupied = set()
    for block in pinned:
        occupied.update(range(block["start_slot"], block["end_slot"]))

    candidate_lists = []
    for block in floating:
        window = block.get("window")
        starts = free_span_candidates(
            occupied, block["duration_slots"], window
        )
        if not starts:
            return []
        candidate_lists.append(starts)

    results = []
    for combination in itertools.islice(
        itertools.product(*candidate_lists), limit
    ):
        placed = []
        spans = []
        clash = False
        for block, start_slot in zip(floating, combination):
            end_slot = start_slot + block["duration_slots"]
            if any(start_slot < other_end and other_start < end_slot
                   for other_start, other_end in spans):
                clash = True
                break
            spans.append((start_slot, end_slot))
            placed.append({**block, "start_slot": start_slot, "end_slot": end_slot})
        if clash:
            continue

        blocks = sorted(pinned + placed, key=lambda item: item["start_slot"])
        total = chain_travel_minutes(case, blocks)
        if total is None:
            continue
        results.append((blocks, total))
    return results


def schedule_from_blocks(blocks):
    schedule = [empty_slot(index) for index in range(SLOT_COUNT)]
    for block in blocks:
        for slot_index in range(block["start_slot"], block["end_slot"]):
            schedule[slot_index] = {
                "start": SLOT_START_TIMES[slot_index],
                "activity": block["activity"],
                "location": block["location"],
            }
    return schedule


def apply_window(rng, anchor_start, duration, difficulty, bounds=None):
    lower, upper = bounds if bounds else (0, SLOT_COUNT)
    slack = {"easy": 4, "medium": 2, "hard": 0}[difficulty]
    open_slot = max(lower, anchor_start - rng.randint(0, slack))
    close_slot = min(upper, anchor_start + duration + rng.randint(0, slack))
    return open_slot, close_slot


def build_case(case_index, master_seed=SCHEDULE_CASE_SEED):
    seed = master_seed + case_index * 9973
    rng = random.Random(seed)

    archetype_name = ARCHETYPE_NAMES[case_index % len(ARCHETYPE_NAMES)]
    task_type = TASK_TYPES[(case_index // 2) % len(TASK_TYPES)]
    difficulty = ("easy", "medium", "hard")[case_index % 3]

    for _ in range(4000):
        day_events = build_horizon(rng, archetype_name)

        # The task always lives inside ONE day of the horizon. Extra days are
        # context the model must transcribe but not reason about. That keeps
        # task difficulty constant while output length scales (TASK-005) — and
        # without it, a long horizon dilutes the constraints until
        # "move_and_insert" can no longer force a move at all.
        active_day = rng.randrange(SCHEDULE_HORIZON_DAYS)
        active_lower = active_day * SLOTS_PER_DAY
        active_upper = active_lower + SLOTS_PER_DAY
        active_bounds = (active_lower, active_upper)
        active_events = [
            event for event in day_events
            if active_lower <= event["start_slot"] < active_upper
        ]

        # cancel/move tasks consume one event, so ask for one more up front.
        minimum_events = 4 if task_type in (
            "cancel_and_insert", "move_and_insert"
        ) else 3
        if len(active_events) < minimum_events:
            continue

        errand_count = 2 if task_type == "insert_two" else 1
        day_locations = {event["location"] for event in day_events}
        errand_pool = [
            option for option in ERRAND_OPTIONS
            if option[1] not in day_locations
        ]
        if len(errand_pool) < errand_count:
            continue
        errand_specs = rng.sample(errand_pool, errand_count)

        pinned = deepcopy(day_events)
        active_ids = {
            (event["activity"], event["start_slot"]) for event in active_events
        }
        active_pinned = [
            event for event in pinned
            if (event["activity"], event["start_slot"]) in active_ids
        ]
        cancelled = []
        movable = []

        if task_type == "cancel_and_insert":
            # Cancelling an interior event opens a span the errand can use.
            interior = active_pinned[1:-1] or active_pinned
            victim = rng.choice(interior)
            pinned = [event for event in pinned if event is not victim]
            cancelled = [victim]
        elif task_type == "move_and_insert":
            interior = active_pinned[1:-1] or active_pinned
            candidate = rng.choice(interior)
            pinned = [event for event in pinned if event is not candidate]
            movable = [candidate]

        case = {
            "case_id": f"schedule_{case_index + 1:03d}",
            "case_seed": seed,
            "archetype": archetype_name,
            "archetype_label": DAY_ARCHETYPES[archetype_name]["label"],
            "task_type": task_type,
            "difficulty": difficulty,
            "horizon_days": SCHEDULE_HORIZON_DAYS,
            "active_day": active_day,
            "active_bounds": list(active_bounds),
        }

        errand_locations = {spec[1] for spec in errand_specs}
        all_locations = sorted(
            day_locations | errand_locations
        )
        case["locations"] = all_locations
        case["travel_minutes"] = build_travel_table(rng, all_locations)

        # Pinned events must already be mutually reachable.
        if chain_travel_minutes(case, pinned) is None:
            continue

        # Every placeable block is confined to the active day, which both keeps
        # the task the same size at any horizon and bounds the solver's search.
        floating = []
        for activity, location, min_slots, max_slots in errand_specs:
            floating.append(
                {
                    "kind": "errand",
                    "activity": activity,
                    "location": location,
                    "duration_slots": rng.randint(min_slots, max_slots),
                    "window": active_bounds,
                }
            )
        for event in movable:
            floating.append(
                {
                    "kind": "movable",
                    "activity": event["activity"],
                    "location": event["location"],
                    "duration_slots": event["duration_slots"],
                    "original_start_slot": event["start_slot"],
                    "window": active_bounds,
                }
            )

        # Anchor pass: find any feasible layout with no windows, then tighten
        # the errand windows around it according to difficulty.
        unrestricted = enumerate_arrangements(case, pinned, floating)
        if not unrestricted:
            continue

        anchor_blocks, _ = rng.choice(unrestricted)
        anchor_by_activity = {
            block["activity"]: block for block in anchor_blocks
        }
        for block in floating:
            if block["kind"] != "errand":
                continue
            anchor = anchor_by_activity[block["activity"]]
            open_slot, close_slot = apply_window(
                rng,
                anchor["start_slot"],
                block["duration_slots"],
                difficulty,
                bounds=active_bounds,
            )
            block["open_slot"] = open_slot
            block["close_slot"] = close_slot
            block["window"] = (open_slot, close_slot)

        arrangements = enumerate_arrangements(case, pinned, floating)
        if not arrangements:
            continue

        if task_type == "move_and_insert":
            # Only keep the case if leaving the movable event where it is
            # cannot work, so the task really requires moving it.
            stuck = [
                blocks for blocks, _ in arrangements
                if any(
                    block.get("kind") == "movable"
                    and block["start_slot"] == block["original_start_slot"]
                    for block in blocks
                )
            ]
            if stuck:
                continue

        baseline = chain_travel_minutes(case, pinned)
        best_total = min(total for _, total in arrangements)

        case["pinned_events"] = [
            {key: event[key] for key in
             ("activity", "location", "start_slot", "duration_slots", "end_slot")}
            for event in pinned
        ]
        case["cancelled_events"] = [
            {key: event[key] for key in
             ("activity", "location", "start_slot", "duration_slots", "end_slot")}
            for event in cancelled
        ]
        case["movable_events"] = [
            {
                "activity": block["activity"],
                "location": block["location"],
                "duration_slots": block["duration_slots"],
                "start_slot": block["original_start_slot"],
                "end_slot": block["original_start_slot"] + block["duration_slots"],
            }
            for block in floating if block["kind"] == "movable"
        ]
        case["errands"] = [
            {
                "activity": block["activity"],
                "location": block["location"],
                "duration_slots": block["duration_slots"],
                "open_slot": block["open_slot"],
                "close_slot": block["close_slot"],
            }
            for block in floating if block["kind"] == "errand"
        ]
        case["baseline_travel_minutes"] = baseline
        case["optimal_total_travel_minutes"] = best_total
        case["optimal_added_travel_minutes"] = best_total - baseline
        case["solution_count"] = len(arrangements)

        # The canvas shown to the model: pinned + movable + soon-to-be
        # cancelled events, all at their original positions.
        before_blocks = (
            case["pinned_events"]
            + case["movable_events"]
            + case["cancelled_events"]
        )
        case["existing_schedule"] = schedule_from_blocks(before_blocks)
        case["free_slot_count"] = sum(
            1 for slot in case["existing_schedule"]
            if slot["activity"] == FREE_ACTIVITY
        )
        return case

    raise RuntimeError(
        f"Could not generate case {case_index} "
        f"({archetype_name}/{task_type}/{difficulty})."
    )


SCHEDULE_CASES = [
    build_case(index) for index in range(SCHEDULE_CASE_COUNT)
]
SCHEDULE_CASE_BY_ID = {
    case["case_id"]: case for case in SCHEDULE_CASES
}


# ---------------------------------------------------------
# Prompt
# ---------------------------------------------------------

def errand_json(errand):
    return {
        "activity": errand["activity"],
        "location": errand["location"],
        "duration_minutes": errand["duration_slots"] * SLOT_MINUTES,
        "opens": slot_clock(errand["open_slot"]),
        "closes": slot_clock(errand["close_slot"]),
    }


def schedule_prompt(case):
    travel_rows = []
    for key, minutes in sorted(case["travel_minutes"].items()):
        first, second = key.split("|", 1)
        travel_rows.append({"from": first, "to": second, "minutes": minutes})

    instructions = [
        "1. Keep every appointment not named in the Task section exactly where "
        "it is (same start, activity, and location).",
        "2. Each added or moved item must occupy contiguous Free slots.",
        "3. Leave enough Free slots between consecutive appointments for the "
        "travel time between their locations.",
        "4. Every slot not used by an appointment must stay Free.",
        "5. Prefer the placement that adds the least total travel time.",
    ]

    task_lines = []
    errands = case["errands"]
    if len(errands) == 1:
        task_lines.append(
            "Add this errand:\n"
            + json.dumps(errand_json(errands[0]), separators=(",", ":"))
        )
    else:
        task_lines.append(
            f"Add all {len(errands)} of these errands. Both must fit in the "
            "same day, and the travel time between them counts:\n"
            + json.dumps(
                [errand_json(errand) for errand in errands],
                separators=(",", ":"),
            )
        )

    if case["cancelled_events"]:
        cancelled = case["cancelled_events"][0]
        task_lines.append(
            f"Cancel \"{cancelled['activity']}\" at {cancelled['location']} "
            f"({slot_clock(cancelled['start_slot'])}). Those slots become Free "
            "and may be reused."
        )

    if case["movable_events"]:
        movable = case["movable_events"][0]
        task_lines.append(
            f"Reschedule \"{movable['activity']}\" at {movable['location']}. "
            f"It currently starts at {slot_clock(movable['start_slot'])} and "
            f"lasts {movable['duration_slots'] * SLOT_MINUTES} minutes, but it "
            "must move somewhere else in the day so the errand fits. It may go "
            "anywhere legal; its duration and location do not change."
        )

    return f"""
You are editing a {SLOT_COUNT}-slot {HORIZON_NOUN} (30 minutes per slot, {HORIZON_RANGE}).
Day type: {case['archetype_label']}.

Task:
{chr(10).join(task_lines)}

Rules:
{chr(10).join(instructions)}

Travel times (minutes, symmetric):
{json.dumps(travel_rows, separators=(",", ":"))}

Current schedule canvas:
{json.dumps(case["existing_schedule"], separators=(",", ":"))}

Return the complete updated 32-slot schedule as a single JSON object with the "schedule" key:
{{"schedule": [
  {{"start": "08:00", "activity": "...", "location": "..."}},
  ... (all {SLOT_COUNT} slots, {HORIZON_RANGE})
]}}

Reason concisely without re-listing the schedule in thought, then output the complete 32-slot JSON object.
""".strip()


# ---------------------------------------------------------
# Evaluation
# ---------------------------------------------------------

def blocks_from_schedule(normalized):
    """Contiguous runs of the same (activity, location), excluding Free."""
    blocks = []
    for index, slot in enumerate(normalized):
        if slot["activity"] == FREE_ACTIVITY:
            continue
        if (
            blocks
            and blocks[-1]["end_slot"] == index
            and blocks[-1]["activity"] == slot["activity"]
            and blocks[-1]["location"] == slot["location"]
        ):
            blocks[-1]["end_slot"] = index + 1
            continue
        blocks.append(
            {
                "activity": slot["activity"],
                "location": slot["location"],
                "start_slot": index,
                "end_slot": index + 1,
            }
        )
    for block in blocks:
        block["duration_slots"] = block["end_slot"] - block["start_slot"]
    return blocks


def evaluate_schedule(case, schedule):
    metrics = {
        "task_type": case["task_type"],
        "archetype": case["archetype"],
        "errand_starts": None,
        "total_travel_minutes": None,
        "added_travel_minutes": None,
        "optimal_added_travel_minutes": case["optimal_added_travel_minutes"],
    }

    if not isinstance(schedule, list):
        return False, "No schedule array returned", metrics
    if len(schedule) != SLOT_COUNT:
        return (
            False,
            f"Expected {SLOT_COUNT} slots, received {len(schedule)}",
            metrics,
        )

    normalized = []
    for index, slot in enumerate(schedule):
        if not isinstance(slot, dict):
            return False, f"Slot {index} is not an object", metrics
        required = ("start", "activity", "location")
        if any(not isinstance(slot.get(key), str) for key in required):
            return False, f"Slot {index} has missing or invalid fields", metrics
        if slot["start"] != SLOT_START_TIMES[index]:
            return False, f"Slot {index} has the wrong start time", metrics
        normalized.append({key: slot[key] for key in required})

    blocks = blocks_from_schedule(normalized)
    by_activity = {}
    for block in blocks:
        by_activity.setdefault(block["activity"], []).append(block)

    for cancelled in case["cancelled_events"]:
        if cancelled["activity"] in by_activity:
            return (
                False,
                f"\"{cancelled['activity']}\" should have been cancelled",
                metrics,
            )

    expected_activities = set()

    for pinned in case["pinned_events"]:
        expected_activities.add(pinned["activity"])
        found = by_activity.get(pinned["activity"], [])
        if len(found) != 1:
            return (
                False,
                f"Fixed appointment \"{pinned['activity']}\" appears "
                f"{len(found)} times",
                metrics,
            )
        block = found[0]
        if (
            block["start_slot"] != pinned["start_slot"]
            or block["duration_slots"] != pinned["duration_slots"]
            or block["location"] != pinned["location"]
        ):
            return (
                False,
                f"Fixed appointment changed at "
                f"{slot_clock(pinned['start_slot'])} "
                f"(\"{pinned['activity']}\")",
                metrics,
            )

    for movable in case["movable_events"]:
        expected_activities.add(movable["activity"])
        found = by_activity.get(movable["activity"], [])
        if len(found) != 1:
            return (
                False,
                f"Rescheduled item \"{movable['activity']}\" appears "
                f"{len(found)} times",
                metrics,
            )
        block = found[0]
        if block["duration_slots"] != movable["duration_slots"]:
            return (
                False,
                f"\"{movable['activity']}\" changed duration",
                metrics,
            )
        if block["location"] != movable["location"]:
            return (
                False,
                f"\"{movable['activity']}\" changed location",
                metrics,
            )
        if block["start_slot"] == movable["start_slot"]:
            return (
                False,
                f"\"{movable['activity']}\" was not rescheduled",
                metrics,
            )

    errand_starts = []
    for errand in case["errands"]:
        expected_activities.add(errand["activity"])
        found = by_activity.get(errand["activity"], [])
        if len(found) != 1:
            return (
                False,
                f"Errand \"{errand['activity']}\" appears {len(found)} times",
                metrics,
            )
        block = found[0]
        if block["location"] != errand["location"]:
            return (
                False,
                f"Errand \"{errand['activity']}\" has the wrong location",
                metrics,
            )
        if block["duration_slots"] != errand["duration_slots"]:
            return (
                False,
                f"Errand \"{errand['activity']}\" has the wrong duration",
                metrics,
            )
        if not (
            block["start_slot"] >= errand["open_slot"]
            and block["end_slot"] <= errand["close_slot"]
        ):
            return (
                False,
                f"Errand \"{errand['activity']}\" is outside its opening window",
                metrics,
            )
        errand_starts.append(slot_clock(block["start_slot"]))

    extra = sorted(set(by_activity) - expected_activities)
    if extra:
        return False, f"Unexpected activity added: {extra[0]}", metrics

    metrics["errand_starts"] = errand_starts

    total_travel = chain_travel_minutes(case, blocks)
    if total_travel is None:
        for previous, current in zip(blocks, blocks[1:]):
            needed = travel_minutes(
                case, previous["location"], current["location"]
            )
            available = (
                current["start_slot"] - previous["end_slot"]
            ) * SLOT_MINUTES
            if available < needed:
                return (
                    False,
                    f"Only {available} min between "
                    f"\"{previous['activity']}\" and \"{current['activity']}\", "
                    f"{needed} min of travel needed",
                    metrics,
                )
        return False, "Travel times are not satisfied", metrics

    added = total_travel - case["baseline_travel_minutes"]
    metrics["total_travel_minutes"] = total_travel
    metrics["added_travel_minutes"] = added

    optimal = case["optimal_added_travel_minutes"]
    if added == optimal:
        quality = "optimal"
    else:
        quality = f"{added - optimal} extra travel minutes"
    return True, f"SUCCESS: Valid schedule, {quality}", metrics


# ---------------------------------------------------------
# Rendering
# ---------------------------------------------------------

# One entry per location in the corpus, so no two locations share a colour.
LOCATION_PALETTE = [
    "#bfdbfe", "#bbf7d0", "#fecaca", "#ddd6fe", "#fed7aa",
    "#a5f3fc", "#fbcfe8", "#d9f99d", "#fde68a", "#e2e8f0",
    "#c7d2fe", "#99f6e4", "#93c5fd", "#86efac", "#fca5a5",
    "#c4b5fd", "#fdba74", "#67e8f9", "#f9a8d4", "#bef264",
    "#fcd34d", "#cbd5e1", "#a5b4fc", "#5eead4",
]
FREE_COLOR = "#f8fafc"
ERRAND_EDGE = "#b45309"
MOVABLE_EDGE = "#6d28d9"


# Colours are assigned once over every location in the corpus, so "Home" is
# the same colour in every case and the eye can compare two canvases directly.
ALL_LOCATIONS = sorted(
    {entry[1] for archetype in DAY_ARCHETYPES.values()
     for entry in archetype["pool"]}
    | {option[1] for option in ERRAND_OPTIONS}
)
assert len(LOCATION_PALETTE) >= len(ALL_LOCATIONS), (
    f"{len(ALL_LOCATIONS)} locations need at least that many palette entries"
)
LOCATION_COLORS = {
    location: LOCATION_PALETTE[index]
    for index, location in enumerate(ALL_LOCATIONS)
}


def location_colors(case):
    return {
        location: LOCATION_COLORS.get(location, "#e5e7eb")
        for location in case["locations"]
    }


def render_schedule_image(case, schedule=None, title="Daily Schedule"):
    shown = (
        schedule if isinstance(schedule, list) else case["existing_schedule"]
    )
    colors = location_colors(case)
    errand_activities = {errand["activity"] for errand in case["errands"]}
    movable_activities = {
        movable["activity"] for movable in case["movable_events"]
    }
    cancelled_activities = {
        cancelled["activity"] for cancelled in case["cancelled_events"]
    }

    fig, ax = plt.subplots(
        figsize=(8.5, max(9.0, 9.0 * SLOT_COUNT / 32.0))
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(SLOT_COUNT, -1.6)
    ax.axis("off")
    ax.set_title(title, fontsize=12, fontweight="bold")

    subtitle = (
        f"{case['archetype_label']} · "
        f"{TASK_LABELS[case['task_type']]} · {case['difficulty']}"
    )
    ax.text(0.5, -0.9, subtitle, fontsize=9, ha="center", color="#374151")

    # Opening-window brackets in the left gutter, one column per errand, so
    # difficulty is visible instead of hidden in the prompt.
    for order, errand in enumerate(case["errands"]):
        x_position = 0.075 + order * 0.028
        ax.plot(
            [x_position, x_position],
            [errand["open_slot"] + 0.05, errand["close_slot"] - 0.05],
            color=ERRAND_EDGE,
            linewidth=2.5,
            solid_capstyle="butt",
        )
        for edge_slot in (errand["open_slot"], errand["close_slot"]):
            ax.plot(
                [x_position - 0.012, x_position + 0.012],
                [edge_slot, edge_slot],
                color=ERRAND_EDGE,
                linewidth=2.0,
            )

    for index in range(SLOT_COUNT):
        slot = (
            shown[index]
            if index < len(shown) and isinstance(shown[index], dict)
            else empty_slot(index)
        )
        activity = str(slot.get("activity", "Invalid"))
        location = str(slot.get("location", ""))
        is_free = activity == FREE_ACTIVITY

        color = FREE_COLOR if is_free else colors.get(location, "#e5e7eb")
        edge = "white"
        line_width = 1.0
        hatch = None
        if activity in errand_activities:
            edge, line_width = ERRAND_EDGE, 2.0
        elif activity in movable_activities:
            edge, line_width = MOVABLE_EDGE, 2.0
        elif activity in cancelled_activities:
            edge, line_width, hatch = "#dc2626", 1.5, "xx"

        ax.add_patch(
            plt.Rectangle(
                (0.15, index + 0.05),
                0.83,
                0.9,
                facecolor=color,
                edgecolor=edge,
                linewidth=line_width,
                hatch=hatch,
            )
        )
        ax.text(0.005, index + 0.62, SLOT_START_TIMES[index], fontsize=7)
        label = activity if is_free else f"{activity} · {location}"
        ax.text(
            0.17,
            index + 0.62,
            label,
            fontsize=7,
            fontweight="bold" if activity in errand_activities else "normal",
        )

    handles = [
        Patch(facecolor=colors[location], edgecolor="#9ca3af", label=location)
        for location in case["locations"]
    ]
    ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.01),
        ncol=min(4, len(handles)),
        fontsize=7,
        frameon=False,
    )

    plt.tight_layout()
    fig.canvas.draw()
    image = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
    plt.close(fig)
    return image


# ---------------------------------------------------------
# Generic puzzle contract consumed by Cells 5 and 6
# ---------------------------------------------------------

def benchmark_parse_output(text):
    if not isinstance(text, str):
        return None

    cleaned = text.replace("```json", "").replace("```JSON", "")
    cleaned = cleaned.replace("```", "").strip()
    decoder = json.JSONDecoder()
    for position, character in enumerate(cleaned):
        if character not in ("{", "["):
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[position:])
        except json.JSONDecodeError:
            continue

        if isinstance(value, dict):
            if isinstance(value.get("schedule"), list):
                return value
            if (
                isinstance(value.get("errand_start"), str)
                and isinstance(value.get("errand_end"), str)
            ):
                return value
        elif isinstance(value, list) and len(value) == SLOT_COUNT:
            return {"schedule": value}
    return None


def benchmark_evaluate_output(case, parsed_output):
    if not isinstance(parsed_output, dict):
        valid, status, metrics = evaluate_schedule(case, None)
        return {
            "valid": valid,
            "status": status,
            "metrics": metrics,
            "display_value": None,
        }

    # Evaluate full emitted schedule canvas
    if isinstance(parsed_output.get("schedule"), list):
        schedule = parsed_output["schedule"]
        valid, status, metrics = evaluate_schedule(case, schedule)
        return {
            "valid": valid,
            "status": status,
            "metrics": metrics,
            "display_value": schedule,
        }

    # Fallback for timestamp outputs. Only meaningful for a plain single
    # insert; the other tasks need the whole canvas back.
    if case["task_type"] != "insert_one":
        return {
            "valid": False,
            "status": "This task requires the full 32-slot schedule",
            "metrics": {"task_type": case["task_type"]},
            "display_value": None,
        }

    start_time = parsed_output.get("errand_start")
    end_time = parsed_output.get("errand_end")
    if start_time not in SLOT_START_TIMES:
        return {
            "valid": False,
            "status": f"Invalid errand start time: {start_time}",
            "metrics": {},
            "display_value": None,
        }

    start_slot = SLOT_START_TIMES.index(start_time)
    errand = case["errands"][0]
    end_slot = start_slot + errand["duration_slots"]
    expected_end = slot_clock(end_slot)
    if end_time != expected_end:
        return {
            "valid": False,
            "status": (
                f"Errand end should be {expected_end}, received {end_time}"
            ),
            "metrics": {},
            "display_value": None,
        }

    schedule = deepcopy(case["existing_schedule"])
    if end_slot <= SLOT_COUNT:
        for index in range(start_slot, end_slot):
            schedule[index] = {
                "start": SLOT_START_TIMES[index],
                "activity": errand["activity"],
                "location": errand["location"],
            }

    valid, status, metrics = evaluate_schedule(case, schedule)
    return {
        "valid": valid,
        "status": status,
        "metrics": metrics,
        "display_value": schedule,
    }


def benchmark_render(case, evaluation, title):
    return render_schedule_image(
        case,
        schedule=evaluation.get("display_value"),
        title=title,
    )


def benchmark_case_label(case):
    return (
        f"{case['case_id']} · {case['archetype_label']} · "
        f"{TASK_LABELS[case['task_type']]} · {case['difficulty']}"
    )


def benchmark_case_description(case):
    lines = [
        f"**{case['archetype_label']}** — "
        f"{len(case['pinned_events'])} fixed appointments across "
        f"{len(case['locations'])} locations, "
        f"{case['free_slot_count']} Free slots.",
    ]
    for errand in case["errands"]:
        lines.append(
            f"- Add **{errand['activity']}** at **{errand['location']}** for "
            f"{errand['duration_slots'] * SLOT_MINUTES} min, between "
            f"{slot_clock(errand['open_slot'])} and "
            f"{slot_clock(errand['close_slot'])}."
        )
    for cancelled in case["cancelled_events"]:
        lines.append(
            f"- Cancel **{cancelled['activity']}** at "
            f"{slot_clock(cancelled['start_slot'])}."
        )
    for movable in case["movable_events"]:
        lines.append(
            f"- Reschedule **{movable['activity']}** away from "
            f"{slot_clock(movable['start_slot'])}."
        )
    lines.append(
        f"Difficulty: **{case['difficulty']}** · "
        f"{case['solution_count']} valid layout"
        f"{'' if case['solution_count'] == 1 else 's'} · "
        f"best adds {case['optimal_added_travel_minutes']} travel min."
    )
    return "\n\n".join(lines)


BENCHMARK_SPEC = {
    "name": "Schedule Repair",
    "slug": "schedule-repair",
    "cases": SCHEDULE_CASES,
    "case_by_id": SCHEDULE_CASE_BY_ID,
    "build_prompt": schedule_prompt,
    "parse_output": benchmark_parse_output,
    "evaluate_output": benchmark_evaluate_output,
    "render": benchmark_render,
    # ~14 tokens per emitted slot plus reasoning headroom. Must scale with the
    # horizon or a long canvas is truncated by the budget rather than by the
    # model, which would silently invalidate a length sweep (TASK-005).
    "default_output_tokens": max(4096, 256 + SLOT_COUNT * 20),
    "case_label": benchmark_case_label,
    "case_description": benchmark_case_description,
    "primary_quality_metric": "added_travel_minutes",
    "optimal_quality_metric": "optimal_added_travel_minutes",
}


def reference_solution(case):
    """Best-scoring legal layout, used by the self test."""
    floating = []
    for errand in case["errands"]:
        floating.append(
            {
                "kind": "errand",
                "activity": errand["activity"],
                "location": errand["location"],
                "duration_slots": errand["duration_slots"],
                "window": (errand["open_slot"], errand["close_slot"]),
            }
        )
    for movable in case["movable_events"]:
        floating.append(
            {
                "kind": "movable",
                "activity": movable["activity"],
                "location": movable["location"],
                "duration_slots": movable["duration_slots"],
                "original_start_slot": movable["start_slot"],
                # Must match the window used when the optimum was computed,
                # or the solver can find a cheaper layout than the recorded one.
                "window": tuple(case["active_bounds"]),
            }
        )
    arrangements = enumerate_arrangements(
        case, deepcopy(case["pinned_events"]), floating
    )
    arrangements = [
        (blocks, total) for blocks, total in arrangements
        if all(
            block.get("kind") != "movable"
            or block["start_slot"] != block["original_start_slot"]
            for block in blocks
        )
    ]
    blocks, _ = min(arrangements, key=lambda item: item[1])
    return schedule_from_blocks(blocks)


def validator_self_test(verbose=True):
    import collections

    # 1. Dataset shape
    assert len(SCHEDULE_CASES) == SCHEDULE_CASE_COUNT, (
        f"Expected {SCHEDULE_CASE_COUNT} cases, found {len(SCHEDULE_CASES)}"
    )
    task_counts = collections.Counter(
        case["task_type"] for case in SCHEDULE_CASES
    )
    archetype_counts = collections.Counter(
        case["archetype"] for case in SCHEDULE_CASES
    )
    assert len(task_counts) == len(TASK_TYPES), "Not every task type is used"
    assert len(archetype_counts) == len(DAY_ARCHETYPES), (
        "Not every day archetype is used"
    )
    shapes = {
        (
            case["archetype"],
            len(case["pinned_events"]),
            case["free_slot_count"],
        )
        for case in SCHEDULE_CASES
    }
    assert len(shapes) >= 20, f"Only {len(shapes)} distinct day shapes"

    # 2. Every case is solvable, and the optimum is achievable.
    for case in SCHEDULE_CASES:
        solution = reference_solution(case)
        valid, status, metrics = evaluate_schedule(case, solution)
        assert valid, f"{case['case_id']} reference solution failed: {status}"
        assert (
            metrics["added_travel_minutes"]
            == case["optimal_added_travel_minutes"]
        ), f"{case['case_id']} optimum mismatch"

    sample_case = SCHEDULE_CASES[0]
    solution = reference_solution(sample_case)

    # 3. Prompt builder
    for case in SCHEDULE_CASES:
        prompt = schedule_prompt(case)
        assert len(prompt) > 300 and '"schedule"' in prompt, (
            f"{case['case_id']} prompt is invalid"
        )

    # 4. Output parsing (clean JSON, markdown, bare list, malformed)
    json_text = json.dumps({"schedule": solution})
    assert benchmark_parse_output(json_text), "Parser failed on JSON"
    assert benchmark_parse_output(f"```json\n{json_text}\n```"), (
        "Parser failed on Markdown"
    )
    assert benchmark_parse_output(json.dumps(solution)), "Parser failed on List"
    assert benchmark_parse_output("garbage ::::") is None, (
        "Parser accepted malformed input"
    )

    # 5. Evaluation contract
    eval_res = benchmark_evaluate_output(
        sample_case, benchmark_parse_output(json_text)
    )
    assert eval_res["valid"], eval_res["status"]

    # 6. Perturbation rejection, one per failure mode
    corrupted = deepcopy(solution)
    pinned = sample_case["pinned_events"][0]
    for index in range(pinned["start_slot"], pinned["end_slot"]):
        corrupted[index] = empty_slot(index)
    assert not benchmark_evaluate_output(
        sample_case, {"schedule": corrupted}
    )["valid"], "Evaluator accepted a deleted fixed appointment"

    dropped = deepcopy(solution)
    errand = sample_case["errands"][0]
    for index, slot in enumerate(dropped):
        if slot["activity"] == errand["activity"]:
            dropped[index] = empty_slot(index)
    assert not benchmark_evaluate_output(
        sample_case, {"schedule": dropped}
    )["valid"], "Evaluator accepted a missing errand"

    for case in SCHEDULE_CASES:
        if case["task_type"] != "cancel_and_insert":
            continue
        kept = deepcopy(case["existing_schedule"])
        assert not benchmark_evaluate_output(
            case, {"schedule": kept}
        )["valid"], "Evaluator accepted an uncancelled appointment"
        break

    for case in SCHEDULE_CASES:
        if case["task_type"] != "move_and_insert":
            continue
        solution = reference_solution(case)
        movable = case["movable_events"][0]
        unmoved = deepcopy(solution)
        for index, slot in enumerate(unmoved):
            if slot["activity"] == movable["activity"]:
                unmoved[index] = empty_slot(index)
        for index in range(movable["start_slot"], movable["end_slot"]):
            unmoved[index] = {
                "start": SLOT_START_TIMES[index],
                "activity": movable["activity"],
                "location": movable["location"],
            }
        assert not benchmark_evaluate_output(
            case, {"schedule": unmoved}
        )["valid"], "Evaluator accepted an unmoved appointment"
        break

    if verbose:
        print(
            f"✅ Spec Contract: all keys valid for '{BENCHMARK_SPEC['name']}'"
        )
        print(
            f"✅ Dataset: {SCHEDULE_CASE_COUNT} reproducible cases, "
            f"{len(shapes)} distinct day shapes, "
            f"{len(archetype_counts)} archetypes, {len(task_counts)} workloads"
        )
        print(
            "   workloads: "
            + ", ".join(
                f"{TASK_LABELS[name]}={count}"
                for name, count in sorted(task_counts.items())
            )
        )
        print("✅ Solver: every case solvable and its optimum reachable")
        print(
            "✅ Parser & Evaluator: JSON, Markdown, Array & 4 perturbation "
            "tests passed"
        )
        print(
            f"✅ Cell 4: {BENCHMARK_SPEC['name']} puzzle ready "
            f"(Output tokens: {BENCHMARK_SPEC['default_output_tokens']})"
        )


validator_self_test(verbose=True)
