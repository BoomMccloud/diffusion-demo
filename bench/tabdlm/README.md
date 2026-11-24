# TabDLM consistency benchmark

Few-shot test of whether a model writes structured records whose fields agree with their own text
(Setting A), and reads structured fields back out of a description (Setting B). Built from the brief
in `writing-block.md`, which is based on TabDLM (arXiv 2602.22586), with changes forced by the data.
There is no fine-tuning, constrained decoding or JSON repair beyond stripping a code fence.

## Data

TabDLM's `biography` (ProfileBio) and `rel_amazon` CSVs, MIT licence, pinned to commit `91560d4`.
`data.py` downloads them to `bench/tabdlm/.data/` (git-ignored), and the manifest records each
file's URL and sha256. Few-shot rows come from `train.csv` and held-out inputs from `test.csv`.

What the data forced:
- **ProfileBio biographies are one template.** All 9,000 fit 8 variants, and one covers 77%. Career
  stage maps to 10-year age bins and income level to three salary bins. So:
  - Setting A shows three hand-written free-form biographies (`tasks.BIO_FREEFORM`) instead of the
    templated ones. It requires the exact age and salary in the text, and checks them exactly.
  - Setting B keeps the templated inputs, and the prompt states the bins. A regex reads every test
    biography back out (`tasks.bio_regex_extract`), so this cell is a sanity floor, not a result.
- **Amazon ratings are 68% five-star**, and about 30% of summaries are "Five Stars" and the like.
  - Setting B inputs are stratified by rating (4 per star at n = 20), and the summary is withheld.
  - Setting A applies the star-summary rule deterministically and leaves the rest to the judge.
- **`review_time` is a day offset and `brand` is often "Visit Amazon's X Page".** The schema in the
  prompt describes both.

## Cells

| dataset | setting | the model gets | the model returns | scoring |
|---|---|---|---|---|
| amazon | gen1, gen10 | instruction, schema, 3 rows (5, 3 and 1 star) | 1 object or an array of 10 | schema, star-summary rule, then a pinned judge for rating ↔ review, summary ↔ review, same book, no contradiction |
| amazon | extract | title, description, review | rating, top-level category | exact rating, within 1, macro-F1; category exact |
| bio | gen1, gen10 | instruction, schema, 3 free-form rows | 1 object or an array of 10 | schema, exact age and salary in the text, pronouns, and TabDLM's field match for state, college, degree and occupation |
| bio | extract | templated biography | the 7 attributes | Bio-MR bins for age and salary, exact for the rest |

Arms are the ones in `bench/synthdata/arms.py`, each at its best temperature from the 2026-10-20
synthdata run: dLLM at 0.6, Qwen at 1.0. Thinking is off, with 8 concurrent requests per arm.

## Floors

These use no model:
- `amazon_fewshot` and `amazon_real`: the judge on the 3 examples and 20 random real test rows.
- `amazon_bland`: 3 hand-made "Great read!" records. If these pass, consistency alone rewards
  saying nothing, so read it next to median words and the judge's `specific_claims`.
- `amazon_extract_majority`: always 5 stars and the top category.
- `bio_code_template`: a one-line f-string biography, which passes every Setting A check.
- `bio_extract_regex`: the template regex.

## Run

```bash
set -a; source .env.local; set +a
uv run --with openai --with numpy python -m bench.tabdlm all --run smoke-2026-10-20
```

- Stages are `generate`, `judge`, `score` and `all`. Each resumes and retries errored rows.
- `--n` sets requests per cell and arm. The default is 20.
- Output goes to `bench/results/tabdlm-<run>/`: `manifest.json`, `generations.jsonl` (gold
  fields, raw output, parsed records, tokens, latency; `tasks.prompt` rebuilds each prompt from its
  dataset, setting and idx), `judgments.jsonl`, `metrics.json` and
  `summary.md`.

## Long-range consistency (`longrange.py`)

The 2026-10-20 smoke found Setting A too easy: both models scored 91% to 100%, the same as bland
records. Synthdata found dLLM inconsistency rising with narrative length while Qwen's stayed flat.
This variant tests that directly, with code checks only.

Each request asks for B person records in one JSON array, B = 10, 30 or 50:
- **Fields:** age, birth_year, salary, sex, birth_state, college, degree, graduation_year,
  occupation and biography.
- **Checks on each record:**
  - The biography states the exact age, birth year, salary and graduation year.
  - It names the state, college and degree.
  - It names the occupation exactly.
  - Its pronouns match the sex.
  - `birth_year` is 2026 minus age, or one less.
  - `graduation_year` is at least `birth_year` + 18 and no later than 2026.
- **Across the batch:** no repeated (college, occupation) pair. A record that repeats an earlier
  pair fails.
- **Order:**
  - `fields` puts the biography last in each object.
  - `text` puts it first, so the attributes must repeat facts written earlier.
- **Failure rate:** missing records and schema failures count as failed positions.

Requests per arm: 55 at B = 10, 20 at B = 30 and 12 at B = 50, about 550 to 600 records per cell.
That's 348 requests in all. The arms and temperatures are as above.

Hypotheses, fixed before the first run:
- **H1, drift.** The dLLM's failure rate in positions 41 to 50 minus positions 1 to 10 at B = 50
  is above zero, with the 95% interval excluding zero.
- **H2, more drift than AR.** That drift minus Qwen's is above zero, with the interval excluding
  zero. This is the claim that the dLLM loses consistency over long output faster than AR.
- **H3, overall gap.** At B = 50, the dLLM's failure rate minus Qwen's is above zero.

Each is tested separately for both orders. As a secondary measure, H2 is also reported on returned
records only, so the drift isn't just stopping short of B. Intervals come from 2,000 bootstrap resamples of
requests, since records in one batch aren't independent.

```bash
uv run --with openai python -m bench.tabdlm.longrange all --run <name> --probe   # 1 request per cell
uv run --with openai python -m bench.tabdlm.longrange all --run <name>
```

## Batch-wide constraints (`constraints.py`)

The one untested place a parallel decoder might beat AR. Each request asks for 30 compact person
records (age, salary, sex, birth_state, occupation) as one JSON array, under one rule or all five:
- `quota`: each of the 10 occupations exactly 3 times
- `sorted`: salary never decreases down the list
- `sum`: the ages sum to exactly 1200
- `balance`: exactly 15 male and 15 female
- `forward`: the first record's salary equals the sum of the last three records' ages, a value
  that depends on records not yet written

A request passes when it returns exactly 30 valid records and every rule of its condition holds
exactly. The summary also gives each rule's median distance from satisfied.

Both arms run at temperature 0.6, matched, since this is a precision task and the dLLM degrades
above 0.8. That's 30 requests per condition per arm, 360 in all.

Hypotheses, fixed before the first run. No earlier result favors either model here, so these are
two-sided:
- **H1.** In the `all` condition, the dLLM's pass rate differs from Qwen's, with the 95% bootstrap
  interval excluding zero.
- **H2.** In at least one single-rule condition, the dLLM's pass rate is above Qwen's with the
  interval excluding zero. `sum` and `forward` are the rules where whole-list planning should
  matter most.

```bash
uv run --with openai python -m bench.tabdlm.constraints all --run <name> --probe
uv run --with openai python -m bench.tabdlm.constraints all --run <name>
```
