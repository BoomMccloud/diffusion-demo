# Tax-form loops

Temperature 0.6 for both arms; thinking off. Step % scores a line against its rule applied to the model's own inputs.

| order | arm | requests | parsed | key order ok % | all correct % | lines correct % | forward correct % | forward step % | backward step % | other step % | refund/owed correct % | median latency s | median tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| main_first | dllm | 3 | 3 | 100.0 | 0.0 | 67.3 | 33.3 | 40.0 | 100.0 | 91.4 | 33.3 | 1.797 | 977 |
| main_first | qwen | 3 | 3 | 100.0 | 0.0 | 65.5 | 20.0 | 20.0 | 100.0 | 93.8 | 33.3 | 6.015 | 870 |
| topo | dllm | 3 | 3 | 100.0 | 0.0 | 87.1 | 93.3 | 93.3 | 100.0 | 96.3 | 33.3 | 1.69 | 977 |
| topo | qwen | 3 | 3 | 100.0 | 0.0 | 88.3 | 93.3 | 100.0 | 100.0 | 95.1 | 33.3 | 6.447 | 873 |

## Forward step % by line

| order | arm | f1040_l1e | f1040_l10 | f1040_l12 | f1040_l19 | f1040_l23 |
|---|---|---|---|---|---|---|
| main_first | dllm | 66.7 | 0.0 | 66.7 | 66.7 | 0.0 |
| main_first | qwen | 0.0 | 0.0 | 33.3 | 66.7 | 0.0 |
| topo | dllm | 100.0 | 100.0 | 66.7 | 100.0 | 100.0 |
| topo | qwen | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |

## Topo minus main_first, forward step % (95% bootstrap interval)

- `dllm`: +53.3 (+26.7 to +86.7)
- `qwen`: +80.0 (+60.0 to +100.0)
