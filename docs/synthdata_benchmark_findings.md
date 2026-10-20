# Synthetic data benchmark findings

Run `2026-10-20` of `bench/synthdata` (plan in `bench/synthdata/README.md`). Output in
`bench/results/synthdata-2026-10-20/`: 15,528 generation rows, about 13,000 judgments.

## Result

The thesis did not hold. At its best temperature, the hosted dLLM
(`qwen36-iter22000-blk16-arverify-best`) does not yield more clean and distinct fictional inpatient
data per request than Qwen3.6-35B-A3B AR at its best temperature. On narratives they tie. On records
they tie on the looser measure available.

The dLLM's real differences:
- It is varied at low temperature, where Qwen needs a high temperature to be varied.
- It is less often clean.
- It is unusable above 0.8.
- It finishes batches about 1.3 to 1.5x faster on this endpoint at 8 concurrent requests.

## What was measured

Fictional Chinese inpatient data, judged blind by `gemini-3.8-flash`:
- **Formats:** `narrative`, 300 to 500 characters with a demographics line and seven sections, and
  `record`, a JSON object.
- **Prompting:** `open`, the same prompt every time, and `seeded`, 69 department, age band and sex
  combinations.
- **Settings:** temperatures 0.6 to 1.2, 3 replicates, 150 (open) or 138 (seeded) requests per cell,
  thinking off, 8 concurrent requests per model.

Yields are per 100 requests, so failed and malformed outputs count against the model.

- **Clean:** passes format and code checks (after a header-only format repair), and the judge finds
  a real diagnosis, no invented drugs, internal consistency, a fitting treatment, no garbled text, and
  the requested department, sex and age.
- **Distinct:** clean, with a new case key (chief complaint without durations, plus primary
  diagnosis), and for narratives also an embedding cosine below 0.97 to every record already kept.
  The count is averaged over 20 random orders.

## Narratives

Per 100 requests, mean over 3 replicates (range in brackets where it matters):

| prompting | model | temp | clean | distinct (key + embedding) | distinct (key only) |
|---|---|---|---|---|---|
| open | dLLM | 0.6 | 66 | 47 (37–53) | 52 |
| open | dLLM | 0.8 | 47 | 43 | 44 |
| open | dLLM | 1.0 | 2 | 2 | 2 |
| open | dLLM | 1.2 | 0 | 0 | 0 |
| open | Qwen | 0.6 | 76 | 21 | 35 |
| open | Qwen | 0.8 | 76 | 35 | 50 |
| open | Qwen | 1.0 | 70 | 40 | 54 |
| open | Qwen | 1.2 | 63 | 46 (44–50) | 56 |
| seeded | dLLM | 0.6 | 63 | 59 (57–62) | 60 |
| seeded | dLLM | 0.8 | 41 | 40 | 40 |
| seeded | dLLM | 1.0 | 1 | 1 | 1 |
| seeded | Qwen | 0.6 | 70 | 59 | 62 |
| seeded | Qwen | 0.8 | 70 | 63 | 65 |
| seeded | Qwen | 1.0 | 68 | 63 (61–64) | 64 |
| seeded | Qwen | 1.2 | 62 | not scored | 59 |

Pre-registered comparison (best temperature chosen on replicate 1, compared on replicates 2 and 3):

| prompting | temps | held-out gaps, dLLM minus Qwen (95% interval) |
|---|---|---|
| open | dLLM 0.6, Qwen 1.2 | +3 (−1 to +9), −8 (−12 to −3) |
| seeded | dLLM 0.6, Qwen 1.0 | +1 (−7 to +6), −5 (−9 to +1) |

The rule needed the dLLM ahead in both held-out replicates in both modes. It was ahead in one and
behind in the other.

- **Temperature.** Raising Qwen's temperature from 0.6 to 1.2 costs 13 clean records per 100 and
  more than doubles its distinct yield. The dLLM is already varied at 0.6. More than 70% of its clean
  records are distinct, but it has no headroom: 16 to 19% of its narratives are garbled at 0.8, and
  almost none are clean at 1.0.
- **Repetition.** In seeded mode, 92 to 97% of the dLLM's seeds got two different cases, against
  78 to 88% for Qwen. Key-only counts overstate Qwen more than the dLLM, because Qwen rewords the same
  case more often.
- **Stability.** One open replicate of the dLLM at 0.6 collapsed onto chronic gastritis and dropped to
  37 distinct.

## What the errors are

Both models make the same kinds of narrative error:
- **Facts that disagree across sections.** A history denying surgery, then a C-section.
- **Medical-knowledge slips.** Hypertension graded 3 from a BP of 160/100, which is grade 2. Hb 95
  g/L called moderate anemia. Hp retested a week into treatment.

The dLLM repeats a few error templates, such as the hypertension grade, many times.

dLLM inconsistency rises with length, and Qwen's doesn't:

| characters | dLLM 0.6 inconsistent | Qwen 1.0–1.2 inconsistent |
|---|---|---|
| under 650 | 27% (n=518) | 25% (n=357) |
| 650–750 | 36% (n=244) | 31% (n=1014) |
| 750–850 | 50% (n=82) | 30% (n=317) |
| over 850 | 68% (n=19) | 24% (n=37) |

This fits a model that commits text in 16-token blocks and loses track of facts set earlier. Length
may also go with case complexity, so treat it as a lead, not a proof.

## Records

Embedding scores were not computed: the Gemini project hit its monthly spending cap during scoring.
These counts use the case key only.

| prompting | model | temp | format | clean | distinct (key only) |
|---|---|---|---|---|---|
| open | dLLM | 0.6 | 92 | 73 | 51 |
| open | dLLM | 0.8 | 86 | 66 | 56 |
| open | Qwen | 0.6 | 99 | 96 | 31 |
| open | Qwen | 0.8 | 98 | 89 | 40 |
| open | Qwen | 1.0 | 98 | 88 | 48 |
| open | Qwen | 1.2 | 94 | 80 | 56 |
| seeded | dLLM | 0.6 | 94 | 70 | 64 |
| seeded | dLLM | 0.8 | 89 | 57 | 55 |
| seeded | Qwen | 0.6 | 93 | 76 | 64 |
| seeded | Qwen | 0.8 | 90 | 72 | 64 |
| seeded | Qwen | 1.0 | 88 | 69 | 64 |
| seeded | Qwen | 1.2 | 86 | 65 | 63 |

- **Short output doesn't fix the clean rate.** The dLLM is at 70 to 73 at 0.6, against Qwen's 76 to
  96.
- **The error changes with the format.** In records, the dLLM's main failures are prescriptions that
  don't fit the diagnosis and invented drug names: 63 of 450 open records at 0.6, against 6 for Qwen
  at 0.6. Naming real drugs is a recall task, and the dLLM is weaker at it.
- **Distinct yield ties on the key measure:** 56 against 56 open and 64 against 64 seeded.
  - With open prompts on narratives, the key measure overstated Qwen by 10 to 15 points and the
    dLLM by 1 to 5. So embedding scores could give the dLLM an edge on open records. That is
    unresolved.
  - With seeded prompts, the two measures were within 3 points for both models, so the seeded
    record tie should hold.

## Speed

On this endpoint at 8 concurrent requests, both models decode about 125 tokens per second per request.
The dLLM finished batches 1.3 to 1.5x faster for two reasons:
- Its narratives are shorter, about 455 tokens against 500 to 510.
- It has a tighter slow tail: 90th percentile latency 4.4 s against 6.9 to 8.2 s.

Qwen runs through OpenRouter, whose queueing likely accounts for some of that tail. The dLLM's
reported 410 tokens per second for a single request does not carry over to 8 concurrent requests.

## Compared with the 2026-10-20 smoke

The smoke had the dLLM at 50 distinct narratives per 100 against Qwen's 35, from one run of 100
requests per cell. That did not replicate. The prompt also gained a demographics line and the judge
prompt changed, so the runs aren't strictly comparable.

## Deviations and limits

- **Skipped cells.** The dLLM's seeded narratives at 1.2 (58 of 414 run) and its records at 1.0 and
  1.2 were skipped mid-run, after open narratives showed 0 to 2% clean at those temperatures.
  Recorded in `manifest.json`.
- **Interrupted runs.** OpenRouter's key cap interrupted 3,750 Qwen requests. They were retried with
  the same seeds after the cap was raised.
- **Judge.** One judge model, not audited. Run `python -m bench.synthdata audit --run 2026-10-20` to
  export samples for labelling.
- **Similarity measure.** One embedding model, with τ = 0.97 set from smoke pairs.
- **Hardware.** The two models run on different hardware and services.

## What would be worth testing next

- Shorter narratives (150 to 250 characters), with everything else unchanged, to test whether length
  causes the dLLM's inconsistency.
- Short items where varied output matters and long-range consistency and drug recall don't, such as
  patient complaint sentences labelled with a triage level, or rewrites of a given note.
