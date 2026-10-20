# Medical record fill smoke test

Run on 2026-10-19. Script `experiments/medical-fill/smoke.py`, rows in
`experiments/medical-fill/results/smoke.jsonl` (112 rows, plus a 14-row probe).

## Question

The source PDF (`downloads/按原PDF病历案例的生成实验_480次对照.pdf`) has a model rewrite a whole
medical record to fill six blanks. Is that ever better than having the model emit only what changes,
with code doing the copying?

## Setup

One fictional record of 584 characters. Three tasks:

- `fill`: the PDF case. Six `[MASK_*]` slots, allergy must be 青霉素 twice, antibiotic from a list.
- `swap`: a correction at the end with no slots marked. The allergy becomes 左氧氟沙星, so the prescribed
  左氧氟沙星 must become 阿奇霉素. Edits depend on each other.
- `gender`: a correction at the end. The patient is male, so 性别 and all four 她 change.

Output modes: `full` (rewrite the record), `fields` (JSON of slot values, `fill` only), and `edits`
(JSON find/replace pairs applied in order by code). Pass means byte-equal to the expected record.

Arms: hosted dLLM `qwen36-iter22000-blk16-arverify-best` and `qwen/qwen3.6-35b-a3b` on OpenRouter.
Thinking off, temperature 0.8, 8 reps per cell, concurrency 4. Latency includes network and isn't
comparable across arms. The OpenRouter provider adds its own queueing.

## Results

| task | mode | dLLM pass | Qwen pass | median output tokens |
|---|---|---|---|---|
| fill | full | 6/8 | 8/8 | 368 |
| fill | fields | 8/8 | 8/8 | 73 |
| fill | edits | 6/8 | 8/8 | 215 to 236 |
| swap | full | 4/8 | 7/8 | 376 |
| swap | edits | 6/8 | 2/8 | 100 to 192 |
| gender | full | 8/8 | 8/8 | 370 |
| gender | edits | 8/8 | 7/8 | 144 to 190 |

- When the changing spans are known ahead, fields-only is perfect for both models at a fifth of the
  output tokens. Rewriting the record adds only copy risk.
- The full rewrite earns its keep only when nobody knows in advance which spans change (`swap`,
  `gender`). Even then, find/replace edits matched or beat it except on Qwen `swap`.
- Qwen `swap` edits failed mostly by dropping the parenthetical (`（某种抗生素）`) from `new`. In 2 of 8
  runs it left 左氧氟沙星 prescribed to a patient now recorded as allergic to it, because the earlier
  replacement had made its `old` text ambiguous.
- dLLM `swap` full failures included one run with the drugs swapped the wrong way (allergic to
  阿奇霉素, prescribed 青霉素) and one that leaked the English word "patients" into the record.

## Follow-up: simultaneous apply with one retry

Same day, rows in `experiments/medical-fill/results/patch.jsonl` (48 rows). `patch` mode locates every
`old` in the original text and applies all pairs at once, rejecting overlaps. A patch that can't be
applied (bad JSON, `old` not found exactly once, overlap) goes back to the model once with the error.
Wrong content is never fed back.

| task | dLLM edits → patch | Qwen edits → patch | retries that rescued the run |
|---|---|---|---|
| fill | 6/8 → 6/8 | 8/8 → 8/8 | dLLM 0/1, Qwen 2/2 |
| swap | 6/8 → 4/8 | 2/8 → 6/8 | dLLM 0/1, Qwen 0/0 |
| gender | 8/8 → 8/8 | 7/8 → 5/8 | dLLM 4/4, Qwen 0/1 |

- Removing the ordering removed the dangerous failure. With sequential edits, 2 Qwen records left
  左氧氟沙星 prescribed to a patient recorded as allergic to it. With patch mode, no applied patch did.
  The one unsafe-looking patch row (dLLM rep 3) failed to apply, so a pipeline would reject it.
- The retry fixes mechanical misses (6 of 9 retried runs passed) but can't fix content errors.
  Those are what remain: rewriting `（某种抗生素）` as `（抗生素名称）`, a stray space, a missed 她, or a
  duplicated sentence. These are the same copying slips as in full rewrites, confined to `new`.
- The dLLM quotes whole sentences as `old`, so its `new` carries more copied text and more chances to
  slip. Asking for the shortest unique `old` might help it most. At 8 reps, 2-run differences are noise.

## Follow-up: the model's real mask token through chat

Run 2026-10-20, script `experiments/medical-fill/real_mask.py`, rows in `results/real_mask.jsonl`.
The hosted tokenizer still maps " それ" to id 151669, which the provider confirmed is the model's mask
id, so " それ" in chat text sends a real mask. Each slot got four masks. The control wrote " [MASK]"
four times. Same instructions, dLLM only, 8 reps each, full rewrite.

- Strict pass: real masks 1/8, text placeholder 3/8.
- Slot values were right in all 8 real-mask runs. Every real-mask failure dropped the parenthetical
  label after a slot, such as `（抗生素名称）` or `（再次确认过敏药物）`, and some also dropped the space
  before the value. The prompt said to keep only the filled content at masked spots, which may have
  invited this, so the instruction is a confound.
- Text-placeholder failures were format slips: `张 伟 强`, `62 岁`, a dropped header, an invented
  住院号.
- This is still the chat path. The model reads the masks as blanks and writes a new record after the
  prompt. It doesn't fill them in place, so this doesn't test bidirectional decoding.

Rerun with a v2 prompt that says to keep the labels (`--prompt v2`, `results/real_mask_v2.jsonl`):

- Strict pass: real masks 5/8, text placeholder 6/8. Within noise at 8 reps.
- Real-mask failures: 2 still dropped labels or merged the value into the next word, and 1 wrote
  `65 岁`. Every value was valid.
- Text-placeholder failures: 1 collapsed the record onto one line, and 1 prescribed 青霉素 to a patient
  recorded as allergic to 青霉素.
- The instruction caused most of the earlier gap. Real masks don't improve the chat fill.

## Follow-up: variety for synthetic data

Run 2026-10-20, script `experiments/medical-fill/synth.py`, rows in `results/synth.jsonl`, page built by
`report/build_data.py`. Each model wrote 50 fictional inpatient summaries as JSON at temperatures 0.6,
0.8, 1.0 and 1.2, 4 concurrent, thinking off. Code checked fields, age, prescription count, and drug
class against allergies. Variety is counted as distinct diagnoses among valid records.

| model | temp | valid | distinct diagnoses | distinct names | seconds per 50 |
|---|---|---|---|---|---|
| dLLM | 0.6 | 47 | 28 | 14 | 8.6 |
| dLLM | 0.8 | 43 | 31 | 22 | 8.2 |
| dLLM | 1.0 | 30 | 24 | 23 | 15.2 |
| dLLM | 1.2 | 1 | 1 | 1 | 107.3 |
| Qwen | 0.6 | 49 | 16 | 8 | 23.4 |
| Qwen | 0.8 | 46 | 21 | 9 | 21.3 |
| Qwen | 1.0 | 47 | 27 | 19 | 22.8 |
| Qwen | 1.2 | 42 | 31 | 24 | 26.0 |

- At the same temperature the dLLM is more varied. At 0.8, Qwen named 28 of 46 patients 张伟.
- Qwen at 1.2 matches the dLLM at 0.8 on variety and validity. The dLLM breaks down above 0.8.
- The dLLM's lasting edge is speed: 31 distinct diagnoses in 8 seconds against Qwen's 31 in 26.
  Qwen's time includes OpenRouter overhead.
- Both models sometimes prescribed a drug in the class of a listed allergy.

### Plausibility by temperature

`judge.py` sent each of the 305 valid records, blind to model and temperature, to `gemini-3.8-flash`
at temperature 0. Rows in `results/synth_judge.jsonl`. A record is clean when the judge finds a real
diagnosis, no invented drugs, prescriptions and complaint that fit the diagnosis, plausible age and
sex, and no garbled text.

| model | temp | clean / 50 | invented drugs | garbled | distinct diagnoses among clean |
|---|---|---|---|---|---|
| dLLM | 0.6 | 36 | 4 | 0 | 21 |
| dLLM | 0.8 | 35 | 2 | 1 | 25 |
| dLLM | 1.0 | 17 | 11 | 6 | 13 |
| dLLM | 1.2 | 0 | 0 | 0 | 0 |
| Qwen | 0.6 | 42 | 0 | 0 | 15 |
| Qwen | 0.8 | 39 | 1 | 0 | 18 |
| Qwen | 1.0 | 44 | 0 | 0 | 24 |
| Qwen | 1.2 | 38 | 1 | 0 | 28 |

- The dLLM's hallucinations rise with temperature: invented drugs such as 盐酸莫替丁片 and
  壬基金霉素胶囊, and mixed-script names such as 盐酸莫ส匹酮片. Qwen's stay near zero up to 1.2.
- The most common flag for both is a prescription that doesn't fit the diagnosis.
- Counting only clean records, Qwen at 1.2 (28 distinct diagnoses) beats the dLLM's best (25 at 0.8).
- One judge model, not hand-checked. Some drug-name calls are debatable, such as 酒石酸美托洛尔缓释片.

## Follow-up: distinctness as training data

`distinct.py` measures a cell at a fixed sample size N, averaged over 20 random subsets:
character 3-gram variety, gzip redundancy, and `gemini-embedding-001` similarity (mean pairwise,
nearest neighbour, share of near-duplicates above 0.95 cosine, and the Vendi score, the effective
number of distinct samples).

### JSON records, content fields only, clean records, N=30

| cell | distinct 3-grams | nearest-neighbour cos | near-dup | Vendi |
|---|---|---|---|---|
| dLLM 0.6 | 0.272 | 0.951 | 63% | 2.51 |
| dLLM 0.8 | 0.367 | 0.928 | 41% | 2.93 |
| Qwen 0.8 | 0.211 | 0.973 | 91% | 2.26 |
| Qwen 1.2 | 0.298 | 0.951 | 63% | 2.60 |

At equal sample size the dLLM at 0.8 is more distinct than Qwen at 1.2, even among clean records.
The earlier distinct-diagnosis count (25 against 28) favoured Qwen because it had more clean records.

### Free-text narratives

`narr.py`: 100 narratives of 300 to 500 characters per cell with seven required sections and no
patient name, judged by `gemini-3.8-flash` for invented drugs, internal consistency, treatment fit and
garbled text. Rows in `results/narr.jsonl` and `results/narr_judge.jsonl`.

| cell | format ok | clean / 100 | seconds | distinct dx in 30 | nearest-neighbour cos | near-dup | Vendi |
|---|---|---|---|---|---|---|---|
| dLLM 0.6 | 79 | 57 | 81 | 17.0 | 0.959 | 84% | 1.93 |
| dLLM 0.8 | 64 | 32 | 92 | 18.2 | 0.950 | 58% | 2.15 |
| Qwen 0.8 | 100 | 79 | 150 | 14.1 | 0.977 | 98% | 1.71 |
| Qwen 1.2 | 98 | 55 | 150 | 17.3 | 0.967 | 89% | 1.96 |

- At matched quality (dLLM 0.6 and Qwen 1.2, both about 56 clean per 100), distinctness is about
  equal, and the dLLM is about 1.9x faster.
- The dLLM at 0.8 is the most distinct, but only 32 of 100 are clean. It often swapped the required
  `【主诉】` headers for markdown `**主诉：**`, and 14 of its judged narratives were garbled.
- Every cell collapses onto the same topic. 慢性非萎缩性胃炎伴糜烂 is the top diagnosis for all four.
  A real data pipeline seeds each request with a department or condition, so variety within a seed
  is the next thing to measure.
- Embedding similarity is high for all narratives (nearest neighbour 0.95 to 0.98), so the 0.95
  near-duplicate threshold is loose for long text. Use the Vendi score and distinct diagnoses for
  comparison.

### Clean, distinct records per minute

`narr.normalize` repairs headers only: `**主诉：**`, `主诉：` and `【入院诊断】` become the required
`【主诉】` and `【诊断】`, a leading `好的，这是…：` line is dropped, and an opening `患者因“…”入院` becomes
`【主诉】`. It rescued 50 dLLM and 2 Qwen narratives. The 7 still invalid are a refusal, sectionless
prose, a 4,301-character runaway and narratives missing sections. Rescued records were judged the same
way (`results/narr_norm.jsonl`, `results/narr_norm_judge.jsonl`).

A clean record is distinct if its embedding cosine to every record already kept in that cell, in
generation order, is below 0.97. Pairs at 0.965 to 0.975 read as the same case with a different
duration, so 0.97 is lenient. 0.96 is shown as a stricter check.

| cell | clean / 100 | distinct ≥0.97 / 100 | distinct ≥0.96 / 100 | seconds | distinct per minute (0.97) |
|---|---|---|---|---|---|
| dLLM 0.6 | 74 | 50 | 34 | 81 | 37.2 |
| dLLM 0.8 | 49 | 47 | 36 | 92 | 30.7 |
| Qwen 0.8 | 79 | 22 | 10 | 150 | 8.8 |
| Qwen 1.2 | 56 | 35 | 21 | 150 | 14.0 |

- Per 100 requests, with speed taken out, dLLM 0.6 yields 50 distinct clean narratives against
  Qwen's best of 35. Per minute the gap is 37 against 14.
- Qwen 0.8 is clean but repetitive: 79 clean, 22 distinct. Many are the same
  `反复上腹痛伴反酸、烧心3个月，加重1周` case.
- This reverses the subset-average comparison above. Counting unique cases rewards a cell that keeps
  finding new ones, and penalises one that clusters tightly around a few.
- Limits: one run per cell, one judge, the greedy count depends on order, and Qwen's time includes
  OpenRouter overhead.

## Limits

One short record, 8 reps per cell, thinking off, one prompt wording per mode. No real patient data,
no clinical judgment. The record is far shorter than a full medical history, so this says nothing
about long-context recall.
