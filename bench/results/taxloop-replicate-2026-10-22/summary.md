# Tax-form loops

Temperature 0.6 for both arms ({'strict_t0': 0.0, 'strict_t0_rep2': 0.0, 'strict_t0_rep3': 0.0} where listed); thinking off. Step % scores a line against its rule applied to the model's own inputs. Forward strict % counts a reordered or unparsed answer as failing all five forward links.

| order | arm | requests | parsed | key order ok % | all correct % | lines correct % | forward correct % | forward step % | forward strict % | backward step % | other step % | refund/owed correct % | median latency s | median tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| main_first | dllm | 150 | 150 | 74.7 | 0.0 | 64.5 | 31.1 | 39.3 | 15.5 | 97.9 | 91.8 | 41.0 | 2.305 | 977 |
| main_first | qwen | 150 | 149 | 98.0 | 0.0 | 63.7 | 19.9 | 21.3 | 20.9 | 98.9 | 93.5 | 44.0 | 8.369 | 870 |
| strict_skeleton | dllm | 150 | 149 | 43.0 | 0.0 | 67.7 | 47.5 | 64.4 | 9.3 | 93.0 | 91.9 | 40.3 | 2.186 | 921 |
| strict_skeleton | qwen | 150 | 150 | 99.3 | 0.0 | 63.7 | 19.2 | 19.2 | 19.1 | 99.5 | 92.6 | 42.0 | 9.226 | 919 |

## Forward step % by line

| order | arm | f1040_l1e | f1040_l10 | f1040_l12 | f1040_l19 | f1040_l23 |
|---|---|---|---|---|---|---|
| main_first | dllm | 31.3 | 26.7 | 60.0 | 50.7 | 28.0 |
| main_first | qwen | 20.8 | 2.0 | 47.6 | 32.0 | 4.1 |
| strict_skeleton | dllm | 61.1 | 56.1 | 77.0 | 69.6 | 58.1 |
| strict_skeleton | qwen | 16.7 | 0.7 | 50.3 | 27.5 | 0.7 |

## dLLM minus Qwen, forward strict % (95% bootstrap interval)

- `main_first`: -5.4 (-9.6 to -1.7); lenient +18.0 (+11.6 to +24.3)
- `strict_skeleton`: -9.8 (-13.3 to -6.2); lenient +45.2 (+38.0 to +52.5)
