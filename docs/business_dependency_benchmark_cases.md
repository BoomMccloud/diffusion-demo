# Business Dependency Benchmark Cases

## Purpose

These twelve classic business problems translate the synthetic 48-value test
into recognizable work. Every case produces exactly 48 scored decisions in one
canonical JSON response. Each problem has a deterministic validator, so model
outputs can be compared by exact correctness, latency, and the location of the
first error.

The initial screen uses three fixtures per problem. A promoted problem should
later use at least ten frozen fixtures. Both models receive the same source data,
instructions, output schema, and maximum generation allowance.

## Direct problems

Every output depends only on the corresponding input record.

### D1. Accounts-payable expense classification

- **Input:** 48 transactions with merchant, description, amount, currency, and
  approved chart-of-accounts rules.
- **Output:** 48 account codes, one per transaction, in source order.
- **Example use:** Classify airfare as `TRAVEL_AIR`, cloud hosting as
  `SOFTWARE_INFRASTRUCTURE`, and office paper as `OFFICE_SUPPLIES`.
- **Validator:** A rule engine independently derives the one permitted account
  code for each transaction and requires an exact 48-element array.

### D2. Customer-support ticket routing

- **Input:** 48 tickets with product, issue type, customer tier, language, and
  region.
- **Output:** 48 destination queues.
- **Example use:** Route a Japanese enterprise billing dispute to
  `JP_ENTERPRISE_BILLING`.
- **Validator:** A deterministic routing table maps every record to one queue;
  no decision uses another ticket's result.

### D3. Purchase-order compliance screening

- **Input:** 48 purchase orders with supplier status, amount, category, contract
  flag, and jurisdiction.
- **Output:** 48 decisions from `APPROVE`, `REVIEW`, or `REJECT`.
- **Example use:** Reject a sanctioned supplier and review an uncontracted order
  above its category threshold.
- **Validator:** Published policy rules calculate each decision independently.

## Mixed-dependency problems

Some outputs are independent, while others depend on a nearby result or shared
subtotal. The response still contains exactly 48 decisions.

### M1. Invoice line validation and subtotal checks

- **Input:** 48 invoice lines grouped into 12 four-line sections. Each section
  contains ordinary lines followed by a subtotal line.
- **Output:** 48 statuses from `VALID`, `PRICE_ERROR`, `TAX_ERROR`, or
  `SUBTOTAL_ERROR`.
- **Example use:** Validate individual quantity-times-price calculations, then
  verify each section subtotal against its preceding three lines.
- **Validator:** Recomputes every line and section subtotal using fixed decimal
  arithmetic.

### M2. Expense-report policy review

- **Input:** 48 expenses grouped by trip day, with category limits, receipt
  status, and daily meal caps.
- **Output:** 48 reimbursement decisions and reason codes.
- **Example use:** A taxi is evaluated independently, while the final meal on a
  day depends on meals already approved for that day.
- **Validator:** Applies per-item rules and recomputes each day's cumulative cap
  in source order.

### M3. Order fulfillment with bundle rules

- **Input:** 48 order lines containing ordinary products and predefined bundles,
  plus inventory by SKU.
- **Output:** 48 statuses from `FULFILL`, `BACKORDER`, or `INVALID_BUNDLE`.
- **Example use:** Ordinary lines depend only on stock; bundle lines also depend
  on the availability and status of their neighboring component lines.
- **Validator:** Simulates inventory reservation within each bundle group and
  checks all 48 statuses exactly.

## Chained problems

Every output after the first depends on the preceding state. A mistake can
propagate through the remainder of the response.

### C1. Daily cash-balance ledger

- **Input:** Opening cash plus 48 ordered deposits, withdrawals, fees, and
  interest events.
- **Output:** The account balance after each event.
- **Example use:** Entry 37 must start from the balance produced by entry 36.
- **Validator:** Uses fixed-point arithmetic to replay all events and compare all
  48 balances exactly.

### C2. Inventory movement ledger

- **Input:** Opening stock plus 48 ordered receipts, sales, returns, damages, and
  transfers for one SKU.
- **Output:** Available inventory after every movement.
- **Example use:** A sale may be accepted only if the previous step left enough
  available stock.
- **Validator:** Replays the ledger, enforces nonnegative inventory, and checks
  every resulting balance and rejection flag.

### C3. Loan amortization schedule

- **Input:** Principal, periodic interest rate, fixed payment, and 48 periods
  with occasional extra payments.
- **Output:** The ending principal for each period.
- **Example use:** Each month's interest and ending balance depend on the prior
  month's ending balance.
- **Validator:** Uses a registered rounding rule and fixed-point arithmetic to
  calculate all 48 balances.

## Global-constraint problems

Every assignment participates in constraints spanning the complete solution.
The decisions are jointly evaluated rather than calculated as a left-to-right
chain.

### G1. Employee shift assignment

- **Input:** 48 shift slots, employees, skills, availability, maximum hours,
  rest requirements, and minimum staffing rules.
- **Output:** One employee assignment for each shift slot.
- **Example use:** Filling one overnight shift changes which employees can cover
  the following morning and whether weekly hour limits remain feasible.
- **Validator:** Checks coverage, skills, availability, uniqueness, rest time,
  and hour limits across the complete schedule.

### G2. Warehouse-to-order allocation

- **Input:** 48 customer orders, warehouse stock, shipping regions, capacity,
  and delivery commitments.
- **Output:** One fulfillment warehouse for each order.
- **Example use:** Assignments compete for shared stock and warehouse capacity;
  all promised delivery dates must remain feasible.
- **Validator:** Aggregates allocations by SKU and warehouse, checks capacities
  and delivery eligibility, and scores shipping cost against a known optimum or
  registered bound.

### G3. Conference seating assignment

- **Input:** 48 attendees, table capacities, team-separation rules,
  accessibility needs, language preferences, and host-placement constraints.
- **Output:** One table assignment for every attendee.
- **Example use:** Each placement consumes capacity and affects several other
  attendees, but there is no required sequential calculation order.
- **Validator:** Checks that every attendee appears once, capacities hold, all
  hard pairwise constraints pass, and the registered preference score is met.

## Comparison outputs

For every model and fixture, retain:

- Exact validity of all 48 decisions.
- Number of correct individual decisions.
- First incorrect decision, when an ordered ground truth exists.
- Hard-constraint violations for global problems.
- Request-to-final-output latency and GPU time.
- Complete raw output, reasoning channel, native stop reason, prompt and result
  token counts, model identity, runner identity, and fixture hash.

The first business screen should use D1, M1, C1, and G1. Together they cover the
four dependency structures with familiar data, exact validators, and compact
explanations. The remaining eight problems test whether any observed result
generalizes beyond one business domain.
