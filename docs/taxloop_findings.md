# Tax-form loop findings, 2026-10-22

## Question

Can the hosted dLLM write a value before the text that computes it, which bidirectional attention
should allow and left-to-right decoding shouldn't? Run: `python -m bench.taxloop.run all --run 2026-10-22`.
Results are in `bench/results/taxloop-2026-10-22/`.

## Setup

Each request gives one fictional taxpayer's facts and asks for five forms (1040, 2441, Schedule SE,
Schedule A, 8812) as one flat JSON object of 57 keys. The rules are invented and stated in full. Four
loops tie the forms together. Each other form copies the name and SSN from the 1040 and reads a 1040
value (wages or AGI), and five 1040 lines (1e, 10, 12, 19, 23) take a result back from that form.

- `main_first` asks for every 1040 line first, so those five lines come before the forms that compute them.
- `topo` asks for the same keys in dependency order.

30 cases per order and arm, temperature 0.6 for both arms, thinking off. "Step" scores a line against
its rule applied to the model's own inputs, so it measures whether the loop closes consistently.

## Results

| order | arm | key order followed | forward-link step % | backward-link step % | lines correct % | median latency s |
|---|---|---|---|---|---|---|
| main_first | dllm | 20 of 30 | 43.9 | 92.7 | 65.1 | 1.9 |
| main_first | qwen | 28 of 30 | 22.5 | 94.7 | 60.6 | 6.5 |
| topo | dllm | 30 of 30 | 98.0 | 100.0 | 75.5 | 1.8 |
| topo | qwen | 30 of 30 | 98.0 | 100.0 | 79.6 | 7.8 |

The dLLM's lead in `main_first` comes from the 10 answers where it broke the requested order. In
those it moved each other form's lines in front of the 1040 line that needs them, which is the `topo`
order, and its forward links held 85% of the time. On answers that kept the order, the forward links
held 24.0% for the dLLM and 22.9% for Qwen. No case in either arm closed all five forward links in
the requested order. Writing in dependency order fixed the links for both arms equally (98%).

### Strict rerun

`main_first_strict` adds: "Write the keys in exactly the order listed. Do not move any key earlier or
later, even when its value depends on keys listed after it. An answer with any key out of order is
rejected." Forward strict % counts a reordered or unparsed answer as failing all five forward links.

| order | arm | key order followed | forward step % | forward strict % |
|---|---|---|---|---|
| main_first | dllm | 20 of 30 | 43.9 | 16.0 |
| main_first | qwen | 28 of 30 | 22.5 | 21.3 |
| main_first_strict | dllm | 19 of 30 | 53.0 | 16.7 |
| main_first_strict | qwen | 30 of 30 | 25.3 | 25.3 |
| topo | either | 30 of 30 | 98.0 | 98.0 |

The instruction didn't stop the dLLM reordering. Scored strictly, it trails Qwen by 8.6 points
(95% bootstrap interval -16.7 to 0.0) with the strict prompt and 5.3 points (-13.4 to +2.7) without.
Qwen follows the order and computes about a quarter of the forward lines in its head.

### Why the dLLM reorders: three variants

Each adds to `main_first_strict`. `strict_t0` runs at temperature 0. `strict_rules_in_order` lists
the rules in output order, each tagged with its form, instead of grouped by form. `strict_skeleton`
adds a JSON template of the 57 keys in order, all null, to fill in. 30 cases per arm each.

| variant | dLLM answers reordered | dLLM forward strict % | Qwen forward strict % | dLLM minus Qwen (95% interval) |
|---|---|---|---|---|
| main_first_strict | 11 of 30 | 16.7 | 25.3 | -8.6 (-16.7 to 0.0) |
| strict_t0 | 3 of 30 | 19.3 | 26.0 | -6.7 (-15.3 to +2.0) |
| strict_rules_in_order | 9 of 30 | 12.7 | 19.3 | -6.6 (-14.0 to +1.3) |
| strict_skeleton | 23 of 30 | 6.7 | 22.0 | -15.3 (-22.0 to -8.0) |

Qwen kept the order in all 90 answers. In 39 of the dLLM's 44 reorderings, 2441 line 26 came before
1040 line 1e, so the model pulled the source forms ahead of the lines that need them.

- **Temperature 0 cuts reordering to 3 of 30.** The dLLM's most likely order is the requested one,
  and reordering is mostly a sampled alternative. In the requested order it still trails Qwen.
- **Listing rules in output order barely matters** (9 of 30 against 11). Grouping by form isn't the cause.
- **The template makes it much worse** (23 of 30), the opposite of what it does for an AR model. The
  cause is unknown. One guess is that the template's keys and nulls are close enough to the answer
  that the model copies structure loosely.

No variant gives the dLLM an advantage on the forward links while it keeps the order.

### Counterfactuals, predictions recorded before the run (2026-10-22)

1. `strict_no_loops`: `main_first_strict` with the five forward 1040 lines given as facts, so no 1040
   line needs a later form. Prediction: at 0.6 the dLLM reorders at most 2 of 30, against 11 of 30
   with the loops. If it still reorders about a third, the loops aren't the cause.
2. `strict_t0` repeated twice more with different seeds, dLLM only. Prediction: outputs are
   byte-identical to the first temperature-0 run. If they differ, temperature 0 isn't greedy on
   this server, and the 3 of 30 figure can't be read as the model's top choice.

Results:

1. **Confirmed.** With no forward references, the dLLM reordered 0 of 30 answers, and so did Qwen.
   Both computed the rest of the return about as well as before (forward-line step 82% and 86%,
   where the lines are now copies of given facts). The loops cause the reordering.
2. **Refuted.** None of the 30 temperature-0 answers came back identical across the three runs.
   The first difference in case 0 is at character 151. Reordering counts were 3, 8 and 8 of 30, so
   temperature 0 is not greedy on this server, and the earlier 3 of 30 was a low draw.

Across the five dLLM runs that ask for `main_first` keys (two at 0.6 and three at 0), some cases
reorder more than chance allows. Case 15 reordered in all 5 runs and cases 23 and 29 in 4. With one
rate for every case (27%), about 0.6 cases would reach 4 or more. So the habit is partly case-driven,
and the earlier overlap check (5 shared against 3.7 by chance) was too small to show it.

Revised reading: forward references cause the reordering. How often it shows up depends on sampling,
which this server doesn't switch off at temperature 0, and somewhat on the case.

So this screen shows no bidirectional advantage. The dLLM behaves like an AR model that sometimes
reorders its output to compute first. That fits the served model: it decodes 16-token blocks with
AR verification, and each loop spans hundreds of tokens, well beyond one block.

## Limits

- 30 cases per cell, one temperature, one prompt. The order violation is a confound the prompt allowed.
- No case reached all 57 lines correct in any cell. Arithmetic errors elsewhere (about 8% of other
  steps) dominate the full-return score.
- The 8812 tax cap never binds in these cases, so 8812 line 13 is a copy with no effect.

## Gap test, 2026-10-22

Does a forward reference get easier when its source is close? `python -m bench.taxloop.gap all --run
2026-10-22`, results in `bench/results/taxloop-gap-2026-10-22/`. One loop: the answer starts with
`taxable`, which must equal `line26`, computed two lines later as benefits minus the smallest of
benefits, 5000 and 4% of wages. A memo of about G words sits between them. The strict order instruction
is always on, and a reordered answer fails. Order `backward` writes `taxable` last as a check.

The forward value has to be fixed by the facts. If it were a free choice, such as the last word of a
story, an AR model could commit to it first and then write to match, so the test would show nothing.

Forward order, 30 cases per cell. Linked % means `taxable` equals the model's own `line26`.

| memo words asked | dLLM memo words | dLLM linked % | Qwen memo words | Qwen linked % | dLLM minus Qwen (95% interval) |
|---|---|---|---|---|---|
| 0 | none | 13.3 | none | 23.3 | -10.0 (-30.0 to +10.0) |
| 15 | 12 | 16.7 | 11 | 26.7 | -10.0 (-30.0 to +10.0) |
| 60 | 32 | 30.0 | 40 | 30.0 | 0.0 (-23.3 to +23.3) |
| 250 | 122 | 23.3 | 204 | 26.7 | -3.3 (-26.7 to +20.0) |
| 1000 | 210 | 20.0 | 379 | 30.0 | -10.0 (-30.0 to +10.0) |

In `backward` order both models linked 100% and got the three calculation lines right 80% to 90% of
the time, so the arithmetic is within reach. Written first, `taxable` is mostly a guess. Across all
gaps the dLLM wrote the full benefits 53 times, zero 21 times, and benefits minus 5000 18 times out of
150. Qwen made the same guesses less often.

Distance doesn't matter for either model, and the dLLM never leads. The closest case isn't inside one
decoding block, though. With no memo, `taxable` is about 25 tokens from `line26`, past the dLLM's
16-token block. This format can't test a within-block forward reference: putting the source lines
before `taxable` makes it a backward copy. So this shows no help from bidirectional attention at
25 tokens or more. It doesn't test the dLLM's attention within a single 16-token block.

The memo fell short of the asked length, most of all for the dLLM, so read the gap by actual words.

## Replication, predictions recorded before the run (2026-10-22)

The dLLM led only when reordered answers counted: forward-line step % in `main_first` (43.9 against
22.5) and `strict_skeleton` (80.7 against 22.0). Rerun both orders on 150 new cases (indices 30 to
179), both arms, temperature 0.6, in `bench/results/taxloop-replicate-2026-10-22/`.

Predictions:
1. Lenient forward step %, which credits reordered answers: the dLLM leads Qwen in both orders, with a
   95% interval above zero.
2. Strict forward %, which fails reordered answers: the dLLM doesn't lead in either order.
3. On answers that kept the order, the dLLM and Qwen are within 5 points of each other.
4. The dLLM reorders 25% to 45% of `main_first` answers and more than 60% of `strict_skeleton` answers.

Results, 150 cases per cell (one Qwen `main_first` and one dLLM skeleton answer didn't parse):

| order | arm | reordered | lenient forward step % | strict forward % | forward step %, order kept | lines correct % |
|---|---|---|---|---|---|---|
| main_first | dllm | 38 of 150 | 39.3 | 15.5 | 20.7 | 64.5 |
| main_first | qwen | 3 of 149 | 21.3 | 20.9 | 21.5 | 63.7 |
| strict_skeleton | dllm | 85 of 149 | 64.4 | 9.3 | 21.9 | 67.7 |
| strict_skeleton | qwen | 1 of 150 | 19.2 | 19.1 | 19.2 | 63.7 |

dLLM minus Qwen, 95% bootstrap intervals:

| order | lenient | strict | order kept only |
|---|---|---|---|
| main_first | +18.0 (+11.6 to +24.3) | -5.4 (-9.6 to -1.7) | -0.8 (-5.2 to +3.6) |
| strict_skeleton | +45.2 (+38.0 to +52.5) | -9.8 (-13.3 to -6.2) | +2.7 (-2.1 to +7.9) |

1. **Confirmed.** The lenient lead replicates in both orders, with intervals well above zero.
2. **Confirmed.** Scored strictly, the dLLM trails, and with 150 cases both intervals now sit below zero.
3. **Confirmed.** On answers that kept the order, the arms differ by -0.8 and +2.7 points.
4. **Partly.** `main_first` reordering was 25%, at the low edge of the predicted range. The skeleton
   gave 57%, short of the predicted 60%.

The dLLM's lead is real and repeatable, and it comes entirely from reordering. Its reordered answers
closed 94% and 97% of the forward links, and its order-kept answers matched Qwen. If field order
doesn't matter to the user, the dLLM returns more correct forward values (31.1% against 19.9% in
`main_first`). The cause is that it writes in dependency order, which an AR model also does when asked
(98% in `topo`). It isn't evidence of bidirectional attention.
