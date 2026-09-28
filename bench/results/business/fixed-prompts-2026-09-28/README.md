# Fixed-prompt verification (POC, 2026-09-28)

Same A100 and runner as `../budget-32k-2026-09-28/` (incremental prefill,
2,048 ubatch, 32,768 context, 30,208 output allowance, same seed). The six
underspecified instructions in `bench/business_fixtures.py` now name their exact
output vocabulary or format. Inputs, seeds, and validators are unchanged. One
case per changed problem, each of which was invalid in an earlier run.

| Case | Blocks | Wall s | Stop | Valid | Correct | Before |
|---|---:|---:|---|---|---:|---|
| d2-001 | 24 | 34.2 | eog | yes | 48/48 | incorrect at 8,704 |
| d3-001 | 37 | 88.6 | eog | yes | 48/48 | 0/48 at 30,208 (label case) |
| m1-000 | 48 | 94.6 | eog | yes | 48/48 | 0/48 at 30,208 (numbers, not labels) |
| m2-001 | 50 | 79.1 | eog | yes | 48/48 | incorrect at 8,704 |
| c2-000 | 18 | 17.5 | eog | yes | 48/48 | incorrect at 8,704 |
| m3-002 | 38 | 97.8 | eog | no | 32/48 | 0/48 at 30,208 (labels) |

Five of six are now exact. m3-002 uses the right labels but its per-group
layout slips from decision 14, a model error rather than a format guess.
All six stopped at native EOG well under the allowance (at most 50 blocks).
Not a registered run; three seeds per problem remain untested.
