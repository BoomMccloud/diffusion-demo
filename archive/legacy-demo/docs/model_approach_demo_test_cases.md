# Real-World Test Cases for Comparing AR and Diffusion Models

## Purpose

This project should demonstrate how different generation approaches can lead to different outcomes. It should not be presented only as a speed benchmark or a contest designed to make one model win.

An autoregressive model generates from left to right and commits to earlier output before producing later output. A diffusion model works across a block of output and can revise uncertain positions during denoising. The most revealing demonstrations therefore have one or more of these properties:

- An early decision depends on information that appears later.
- Several constraints must be satisfied across the entire answer.
- A nearly complete result must be repaired with minimal changes.
- Blank fields must be filled without changing fixed content.
- Changing one part of the solution affects several other parts.

Each demonstration should contain 50 different, reproducible cases. The interface should show both the final result and how each model arrived there.

## Recommended Demonstrations

### 1. Add an errand to an existing schedule

#### Scenario

A person already has a schedule containing appointments at different locations. The model must add one new errand while accounting for travel time, opening hours, appointment duration, and a required final arrival time.

Example:

- 9:00 to 10:00, dentist
- 12:30 to 1:30, lunch meeting
- 3:30, pick up child from school
- Pharmacy is open from 10:00 to 4:00
- Travel times are provided between every location
- Add a 20-minute pharmacy visit

#### What it demonstrates

An early scheduling decision can make a later appointment impossible. The output must be coordinated as a complete timeline.

#### Fifty-case variations

- Different appointment times and durations
- Different travel-time matrices
- Errands with opening and closing hours
- Fixed and flexible appointments
- Required breaks
- Multiple valid insertion points
- Cases with exactly one valid solution
- Cases where the new task cannot be added

#### Evaluation

- All fixed appointments preserved
- No overlapping events
- Travel time included
- Opening hours respected
- New errand completed
- Correctly identifies impossible cases
- Number of unnecessary schedule changes

#### Visual presentation

Show a daily calendar. Highlight conflicts in red and satisfied constraints in green. The AR panel grows from morning to evening. The diffusion panel begins as a complete schedule canvas whose uncertain time slots change during denoising.

---

### 2. Multi-stop errand route

#### Scenario

A person must visit several locations, respect deadlines and opening hours, and return home or reach a final destination.

Example:

> Start at home, collect a prescription, buy groceries, drop off a package, pick up a child at 4:00, and return home. Travel times and store hours are provided.

#### What it demonstrates

This is the real-world version of pathfinding. Choosing the next stop locally may make a later deadline impossible.

#### Fifty-case variations

- Different numbers of stops
- Different travel times
- Time-limited stops
- Required stop ordering
- Optional stops with priorities
- Traffic delays
- One temporarily closed route
- Impossible routes

#### Evaluation

- Every required stop visited
- Deadlines and opening hours respected
- Valid travel between stops
- Correct start and destination
- Total travel time
- Correct handling of impossible cases

#### Visual presentation

Use a simple map and timeline. Animate the route as it is generated or revised.

---

### 3. Grid pathfinding

#### Scenario

A robot must move through a grid, avoid walls, collect required items, and reach a destination.

#### What it demonstrates

This provides a controlled technical analogy for the errand-routing demonstration. Every move is easy to validate, and an early direction can create a dead end later.

#### Fifty-case variations

- Different grid sizes
- Different wall layouts
- Different start and destination cells
- One to four required items
- Required item order
- Narrow corridors
- Multiple valid routes
- Exactly one valid route
- No valid route

#### Evaluation

- Valid JSON
- Starts at the correct cell
- Every move is adjacent
- No wall collisions
- No out-of-bounds coordinates
- Required items visited
- Correct destination
- Route length compared with the shortest valid route

#### Visual presentation

Draw both paths side by side. Mark the first invalid move or missed requirement directly on the grid.

---

### 4. Repair a disrupted travel itinerary

#### Scenario

The model receives a complete itinerary and one disruption. It must repair the itinerary while preserving unaffected reservations and activities.

Example:

> The museum is now closed Tuesday. Move it to another open period without changing the hotel, dinner reservation, or train booking.

#### What it demonstrates

This emphasizes global revision and minimal editing. The best answer is not a completely new itinerary. It is the smallest valid repair.

#### Fifty-case variations

- Attraction closure
- Delayed train or flight
- Restaurant reservation moved
- Weather-dependent activity canceled
- Traveler becomes unavailable for part of a day
- Travel time increases
- Budget reduced
- One activity becomes mandatory

#### Evaluation

- New constraint satisfied
- Existing fixed reservations preserved
- No time or travel conflicts
- All required activities retained
- Number of unnecessary edits
- Total cost remains valid

#### Visual presentation

Show the original and repaired itinerary. Color only changed fields. Count changes that were not required.

---

### 5. Complete or repair a structured form

#### Scenario

The model receives JSON or a familiar form with fixed values, blanks, and possibly one inconsistency. It must fill or repair only the necessary fields.

Example:

```json
{
  "departure": "Taipei",
  "arrival": "Tokyo",
  "departure_date": "2026-09-10",
  "return_date": "_____",
  "nights": 4,
  "travelers": 2
}
```

#### What it demonstrates

The task tests infilling, structure preservation, and relationships between distant fields. It makes the idea of filling blanks across a complete canvas easy to understand.

#### Fifty-case variations

- Travel bookings
- Purchase orders
- Expense reports
- Event registrations
- Shipping forms
- Restaurant reservations
- Inventory records
- Forms with multiple related blanks
- Forms containing one inconsistent value

#### Evaluation

- Valid JSON or valid form structure
- Fixed fields remain unchanged
- Every required blank filled
- Dates and totals are consistent
- Only necessary fields changed
- Correctly identifies insufficient information

#### Visual presentation

Show fixed fields in gray, blanks in yellow, changed values in blue, and invalid relationships in red.

---

### 6. Wedding or dinner seating plan

#### Scenario

Assign guests to tables while satisfying table capacity, family grouping, accessibility, and interpersonal constraints.

#### What it demonstrates

Every placement changes the remaining possibilities. A locally reasonable early assignment can prevent a complete solution.

#### Fifty-case variations

- Different guest and table counts
- Families that should sit together
- Guests who must be separated
- Children seated near parents
- Wheelchair-accessible seats
- Hosts near priority guests
- Noise-sensitive guests away from speakers
- Cases with multiple or unique valid arrangements

#### Evaluation

- Every guest assigned exactly once
- Table capacities respected
- All hard constraints satisfied
- Number of preferences satisfied
- Fair distribution across tables

#### Visual presentation

Use a seating chart. Draw green connections for desired proximity and red connections for violations.

---

### 7. Weekly meal plan

#### Scenario

Create a meal plan that meets dietary restrictions, budget, nutrition targets, ingredient-expiration rules, and leftover reuse requirements.

#### What it demonstrates

Choosing meals early in the week affects budget, nutrition, ingredient use, and later meals. The output must balance totals across the entire week.

#### Fifty-case variations

- Different diets and allergies
- Different weekly budgets
- Calorie or protein targets
- Perishable ingredients that must be used early
- Leftovers required on specified days
- Limited cooking time
- No repeated meals
- One restaurant meal fixed in advance

#### Evaluation

- Dietary restrictions respected
- Budget respected
- Nutrition target met
- Required ingredients used before expiration
- Leftovers reused correctly
- Meal repetition constraints satisfied

#### Visual presentation

Show a seven-day calendar with live budget, nutrition, and ingredient-use meters.

---

### 8. Pack a suitcase

#### Scenario

Select items for a trip while covering planned activities and weather without exceeding baggage weight or volume.

#### What it demonstrates

Early packing choices consume limited capacity needed for requirements appearing elsewhere in the itinerary.

#### Fifty-case variations

- Different trip lengths
- Hot, cold, or mixed weather
- Formal events
- Hiking, swimming, or business activities
- Laundry availability
- Carry-on-only limits
- Shared family items
- Required medical or accessibility items

#### Evaluation

- Every essential requirement covered
- Weight and volume limits respected
- No prohibited items
- Unnecessary duplication
- Weather and activity coverage

#### Visual presentation

Show the suitcase filling while a weight meter changes. Highlight missing activity coverage.

---

### 9. Employee shift scheduling

#### Scenario

Assign employees to shifts while respecting availability, skills, staffing minimums, maximum hours, rest periods, and fairness.

#### What it demonstrates

Solving one uncovered shift can create a shortage or labor-rule violation elsewhere. The schedule must be revised globally.

#### Fifty-case variations

- Retail store schedules
- Restaurant shifts
- Clinic coverage
- Required certifications
- Employee availability
- Maximum weekly hours
- Rest periods
- Requested days off
- Fair distribution of nights and weekends

#### Evaluation

- Every required shift covered
- Required skills present
- Availability respected
- Maximum hours and rest rules respected
- Fairness score
- Number of unnecessary assignments

#### Visual presentation

Use a weekly roster. Display coverage and fairness meters beside the schedule.

---

### 10. Household chore assignment

#### Scenario

Assign chores to household members using availability, age restrictions, preferences, duration, and fairness constraints.

#### What it demonstrates

The plan must be both complete and balanced. Assigning easy tasks early may leave one person with all difficult work.

#### Fifty-case variations

- Different household sizes
- Children with age restrictions
- Different availability windows
- Preferred and disliked chores
- Daily and weekly tasks
- Tasks requiring two people
- Fairness by time or difficulty

#### Evaluation

- Every chore assigned
- Availability respected
- Age and safety restrictions respected
- Workload balance
- Preference satisfaction

#### Visual presentation

Show assignments on a household calendar with a workload bar for each person.

---

### 11. Party menu and shopping list

#### Scenario

Create a menu and exact shopping list for a group while respecting dietary needs, package sizes, ingredients already owned, and a budget.

#### What it demonstrates

Quantities and totals depend on choices throughout the output. Changing one dish should revise several shopping-list entries.

#### Fifty-case variations

- Different guest counts
- Vegetarian, vegan, allergy, and religious restrictions
- Different budgets
- Ingredients already in the pantry
- Package-size constraints
- Required dishes
- Leftover limits
- One guest-count change applied to an existing plan

#### Evaluation

- Every dish has sufficient ingredients
- Dietary requirements covered
- Quantities scale correctly
- Existing ingredients deducted
- Package sizes handled
- Budget respected
- No unrelated list changes during repair cases

#### Visual presentation

Show the menu, shopping list, and running total together. Animate quantity revisions across related ingredients.

---

### 12. Tournament scheduling

#### Scenario

Schedule tournament matches across courts or fields while respecting match dependencies, venue availability, and minimum rest time.

#### What it demonstrates

Later matches depend on earlier matches. A schedule that initially appears valid may become impossible once rest and progression constraints are considered.

#### Fifty-case variations

- Single-elimination brackets
- Group stages followed by playoffs
- Different numbers of courts
- Venue closures
- Minimum rest periods
- Broadcast time slots
- Teams sharing coaches or players
- Weather delays requiring schedule repair

#### Evaluation

- Every match scheduled exactly once
- Dependency order respected
- No court conflicts
- Rest requirements satisfied
- Fixed broadcast slots preserved
- Makespan or completion time

#### Visual presentation

Show the bracket and venue timeline together. Highlight downstream conflicts caused by an earlier match.

---

### 13. Furniture layout

#### Scenario

Place furniture in a room while respecting room dimensions, doors, windows, walking clearance, and functional preferences.

#### What it demonstrates

Each placement affects the remaining usable space. A locally attractive early placement can prevent a valid complete layout.

#### Fifty-case variations

- Bedrooms, offices, and living rooms
- Different room dimensions
- Door-swing and window constraints
- Accessibility clearances
- Required sight lines
- Power-outlet proximity
- Existing immovable furniture
- One new item added to an existing layout

#### Evaluation

- No overlaps
- Every item inside the room
- Doors and windows remain usable
- Required clearances respected
- Functional preferences satisfied
- Number of existing items moved in repair cases

#### Visual presentation

Render a simple floor plan and highlight collisions or blocked paths.

---

### 14. Delivery loading and drop-off order

#### Scenario

Load packages into a vehicle and select a delivery order while respecting capacity, delivery windows, fragile-item rules, and the need to access earlier deliveries.

#### What it demonstrates

Route order and physical loading order are interdependent. A package placed early can block something needed at the first stop.

#### Fifty-case variations

- Different vehicle capacities
- Weight distribution rules
- Fragile or refrigerated packages
- Delivery time windows
- Priority customers
- Package dependencies
- One canceled or urgent delivery inserted into an existing route

#### Evaluation

- Capacity respected
- Delivery windows met
- Loading order supports drop-off order
- Handling rules respected
- Every required delivery completed
- Minimal changes after an inserted delivery

#### Visual presentation

Show the route beside a simplified vehicle-loading diagram.

---

### 15. Edit a document under multiple constraints

#### Scenario

Revise a short announcement, invitation, or product description while preserving required phrases, facts, length, tone, and formatting.

#### What it demonstrates

The ending may require revisions to the beginning to satisfy a total word count, preserve facts, or avoid repetition. This is a natural text example without JSON or spatial reasoning.

#### Fifty-case variations

- Shorten to an exact word limit
- Change tone while preserving facts
- Insert one required sentence
- Preserve names, dates, and links
- Remove prohibited claims
- Repair inconsistent pronouns or tense
- Complete blanks inside a fixed template

#### Evaluation

- Required facts preserved
- Prohibited changes avoided
- Word or character limit satisfied
- Required phrases included
- Formatting retained
- Number of unnecessary edits

#### Visual presentation

Show a live diff. Color preserved text, required edits, and unnecessary edits differently.

## Prioritized Implementation Roadmap

Following the completion of **Add an errand to a schedule** (`cell_4_schedule_puzzle.py`), the remaining candidate problems are prioritized into three implementation tiers based on architectural contrast, deterministic validation feasibility, and visual intuition.

### Tier 1: Immediate Next Implementations (Highest Contrast & Direct BENCHMARK_SPEC Compatibility)

1. **Complete or repair a structured form (Scenario 5)**
   - **Why #1 priority**: Native to masked diffusion infilling. Fixed JSON keys/values are preserved while arbitrary blank fields (e.g., dates, totals, passenger counts) are infilled.
   - **Architectural demonstration**: Exposes AR's inability to condition early blank fields on distant later fields without token bloat or FIM (Fill-In-The-Middle) workarounds.
   - **Validation & Spec**: 100% deterministic schema validation, low token budget, straightforward `BENCHMARK_SPEC` integration.

2. **Grid pathfinding (Scenario 3)**
   - **Why #2 priority**: Precise mathematical ground truth benchmark. Clean 2D grid matrix with obstacles, required waypoints, and target destination.
   - **Architectural demonstration**: Exposes AR greedy lookahead traps (getting trapped in cul-de-sacs or missing distant deadlines) vs. Diffusion's global trajectory relaxation.
   - **Visuals**: Highly compelling side-by-side grid canvas animation in the web UI.

3. **Repair a disrupted travel itinerary (Scenario 4)**
   - **Why #3 priority**: Direct evolution of the schedule puzzle focusing on *minimal edit distance*.
   - **Architectural demonstration**: Tests whether models alter only affected appointments or destructively rewrite unaffected downstream bookings.
   - **Validation**: Strict diff-scoring against ground truth minimum edits.

### Tier 2: Combinatorial & Global Constraint Satisfaction (Next Wave)

4. **Multi-stop errand route (Scenario 2)**: Time-windowed TSP connecting grid pathfinding to real-world scheduling with opening hours and traffic constraints.
5. **Wedding or dinner seating plan (Scenario 6)**: Graph coloring and constraint satisfaction problem (CSP) testing domain wipeout in AR vs. soft energy relaxation in Diffusion.
6. **Employee shift scheduling (Scenario 9)**: Tabular staffing matrix with skill requirements, labor hours, and mandatory rest buffers.

### Tier 3: Multi-Objective Optimization & Spatial Layouts (Future Extensions)

7. **Pack a suitcase (Scenario 8)**: Multi-capacity knapsack under weather/activity coverage constraints.
8. **Weekly meal plan (Scenario 7)**: Multi-objective balance of nutrition, budget, and perishable expiration rules.
9. **Furniture layout (Scenario 13)**: 2D continuous bounding-box spatial layout with clearance and door-swing geometry.
10. **Edit a document under multiple constraints (Scenario 15)**: Text-level revision under strict word count, tone, and preserved facts.

## How to Build the 50 Cases

Each case should contain:

- A unique case ID
- A natural-language prompt
- Structured source data
- Hard constraints that must always be satisfied
- Soft preferences that improve solution quality
- A deterministic validator
- A reference solution or proof that a solution exists
- A flag for intentionally impossible cases
- The same maximum output allowance for both models

Cases should be generated before either model runs and saved to a JSON file. Both models must receive the same cases in the same order.

A useful mix for each 50-case set is:

- 20 ordinary cases with several valid solutions
- 15 tightly constrained cases with one or very few valid solutions
- 10 repair or infilling cases where existing content should be preserved
- 5 impossible cases that the model must identify correctly

## What to Measure

### Primary outcome measures

- Fully valid solutions out of 50
- Hard-constraint satisfaction rate
- Correct impossible-case detection
- Valid structured-output rate

### Measures that reveal approach differences

- Unnecessary changes to fixed or already-valid content
- First point at which an invalid commitment appears
- Number of constraints that change from violated to satisfied during generation
- Whether errors cluster near the end of AR outputs
- Whether diffusion revisions converge or oscillate
- Whether distant, mutually dependent fields agree

### Performance measures

- Model load time, reported separately
- Generation time per case
- Median and percentile generation time
- Tokens or output units produced
- Peak GPU and system memory

## What the Audience Should See

The interface should not display only a final score. It should make the generation behavior visible.

### AR panel

- Reveal output from left to right
- Mark earlier choices as committed
- Highlight the first choice that creates a later conflict
- Show when a late constraint cannot be satisfied without rewriting earlier text

### Diffusion panel

- Begin with a complete output canvas or set of blanks
- Show uncertain positions changing during denoising
- Highlight fields that stabilize
- Show constraints turning from violated to satisfied

### Shared result panel

- Final output
- Hard constraints passed and failed
- Unnecessary edits
- Runtime excluding and including model load
- Aggregate success count across 50 cases

## Fairness and Interpretation

The demonstration should test a hypothesis, not assume the result.

- Use production-appropriate settings for each model.
- For constrained AR generation, temperature 0.0 or 0.1 is reasonable.
- Use DiffusionGemma's documented diffusion sampler defaults.
- Do not run the same deterministic prompt 50 times and call it 50 cases.
- Do not count model loading as generation for one model but not the other.
- Keep each model loaded while it processes all 50 cases when possible.
- Validate final outputs with code rather than subjective judgment.
- Report cases where AR performs better, diffusion performs better, both succeed, and both fail.
- Treat architecture as one explanatory factor, not proof that one model must always be more accurate.

## Suggested Narrative

The public story can be:

> Some tasks are naturally written from beginning to end. Other tasks require coordinating or revising many parts of an answer at once. We gave both models the same 50 real-world problems, then observed not only whether they succeeded, but how their generation processes handled global constraints, fixed content, and late-discovered conflicts.

This framing demonstrates meaningful behavioral differences without reducing the project to a simple speed race.
