# Gap test

Temperature 0.6 for both arms; thinking off. Linked % needs the requested key order and taxable equal to the model's own line26.

| order | memo words asked | arm | requests | key order ok % | linked % | taxable correct % | limit, excluded, line26 correct % | median memo words | median tokens | median latency s |
|---|---|---|---|---|---|---|---|---|---|---|
| backward | 0 | dllm | 2 | 100.0 | 100.0 | 100.0 | 100.0 | None | 76 | 0.393 |
| backward | 0 | qwen | 2 | 100.0 | 100.0 | 100.0 | 100.0 | None | 77 | 2.255 |
| backward | 15 | dllm | 2 | 100.0 | 100.0 | 100.0 | 100.0 | 12 | 100 | 0.537 |
| backward | 15 | qwen | 2 | 100.0 | 100.0 | 100.0 | 100.0 | 14 | 95 | 3.797 |
| backward | 60 | dllm | 2 | 100.0 | 100.0 | 100.0 | 100.0 | 32 | 119 | 0.823 |
| backward | 60 | qwen | 2 | 100.0 | 100.0 | 100.0 | 100.0 | 38 | 124 | 4.021 |
| backward | 250 | dllm | 2 | 100.0 | 100.0 | 100.0 | 100.0 | 181 | 296 | 2.318 |
| backward | 250 | qwen | 2 | 100.0 | 100.0 | 100.0 | 100.0 | 190 | 294 | 9.023 |
| backward | 1000 | dllm | 2 | 100.0 | 100.0 | 100.0 | 100.0 | 316 | 440 | 3.107 |
| backward | 1000 | qwen | 2 | 100.0 | 100.0 | 100.0 | 100.0 | 488 | 640 | 16.884 |
| forward | 0 | dllm | 2 | 100.0 | 0.0 | 0.0 | 50.0 | None | 52 | 0.4 |
| forward | 0 | qwen | 2 | 100.0 | 0.0 | 0.0 | 100.0 | None | 73 | 1.694 |
| forward | 15 | dllm | 2 | 100.0 | 50.0 | 0.0 | 50.0 | 15 | 104 | 0.584 |
| forward | 15 | qwen | 2 | 100.0 | 0.0 | 0.0 | 100.0 | 13 | 86 | 3.189 |
| forward | 60 | dllm | 2 | 100.0 | 0.0 | 0.0 | 100.0 | 31 | 118 | 0.868 |
| forward | 60 | qwen | 2 | 100.0 | 50.0 | 0.0 | 50.0 | 37 | 121 | 1.468 |
| forward | 250 | dllm | 2 | 100.0 | 0.0 | 0.0 | 100.0 | 190 | 305 | 2.202 |
| forward | 250 | qwen | 2 | 100.0 | 0.0 | 0.0 | 100.0 | 207 | 312 | 3.795 |
| forward | 1000 | dllm | 2 | 100.0 | 0.0 | 0.0 | 100.0 | 292 | 426 | 2.855 |
| forward | 1000 | qwen | 2 | 100.0 | 0.0 | 0.0 | 100.0 | 530 | 672 | 7.527 |

## dLLM minus Qwen, forward linked % (95% bootstrap interval)

- gap 0: +0.0 (+0.0 to +0.0)
- gap 15: +50.0 (+0.0 to +100.0)
- gap 60: -50.0 (-100.0 to +0.0)
- gap 250: +0.0 (+0.0 to +0.0)
- gap 1000: +0.0 (+0.0 to +0.0)
