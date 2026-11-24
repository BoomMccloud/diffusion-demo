# Gap test

Temperature 0.6 for both arms; thinking off. Linked % needs the requested key order and taxable equal to the model's own line26.

| order | memo words asked | arm | requests | key order ok % | linked % | taxable correct % | limit, excluded, line26 correct % | median memo words | median tokens | median latency s |
|---|---|---|---|---|---|---|---|---|---|---|
| backward | 0 | dllm | 30 | 100.0 | 100.0 | 83.3 | 83.3 | None | 52 | 0.263 |
| backward | 0 | qwen | 30 | 100.0 | 100.0 | 83.3 | 83.3 | None | 63 | 1.174 |
| backward | 15 | dllm | 30 | 100.0 | 100.0 | 83.3 | 83.3 | 12 | 90 | 0.383 |
| backward | 15 | qwen | 30 | 100.0 | 100.0 | 90.0 | 90.0 | 11 | 88 | 1.411 |
| backward | 60 | dllm | 30 | 100.0 | 100.0 | 83.3 | 83.3 | 32 | 118 | 0.785 |
| backward | 60 | qwen | 30 | 100.0 | 100.0 | 90.0 | 90.0 | 40 | 121 | 1.571 |
| backward | 250 | dllm | 30 | 100.0 | 100.0 | 80.0 | 80.0 | 146 | 248 | 1.973 |
| backward | 250 | qwen | 30 | 100.0 | 100.0 | 83.3 | 83.3 | 205 | 307 | 3.381 |
| backward | 1000 | dllm | 30 | 100.0 | 100.0 | 86.7 | 86.7 | 231 | 352 | 2.922 |
| backward | 1000 | qwen | 30 | 100.0 | 100.0 | 90.0 | 90.0 | 394 | 526 | 4.971 |
| forward | 0 | dllm | 30 | 100.0 | 13.3 | 3.3 | 80.0 | None | 52 | 0.307 |
| forward | 0 | qwen | 30 | 100.0 | 23.3 | 23.3 | 73.3 | None | 70 | 1.372 |
| forward | 15 | dllm | 30 | 100.0 | 16.7 | 16.7 | 83.3 | 12 | 73 | 0.421 |
| forward | 15 | qwen | 30 | 100.0 | 26.7 | 26.7 | 90.0 | 11 | 89 | 1.391 |
| forward | 60 | dllm | 30 | 100.0 | 30.0 | 16.7 | 73.3 | 32 | 114 | 0.788 |
| forward | 60 | qwen | 30 | 100.0 | 30.0 | 30.0 | 76.7 | 40 | 124 | 1.579 |
| forward | 250 | dllm | 30 | 100.0 | 23.3 | 20.0 | 83.3 | 122 | 219 | 1.785 |
| forward | 250 | qwen | 30 | 100.0 | 26.7 | 33.3 | 93.3 | 204 | 304 | 2.953 |
| forward | 1000 | dllm | 30 | 100.0 | 20.0 | 16.7 | 86.7 | 210 | 319 | 2.887 |
| forward | 1000 | qwen | 30 | 93.3 | 30.0 | 36.7 | 83.3 | 379 | 521 | 5.473 |

## dLLM minus Qwen, forward linked % (95% bootstrap interval)

- gap 0: -10.0 (-30.0 to +10.0)
- gap 15: -10.0 (-30.0 to +10.0)
- gap 60: +0.0 (-23.3 to +23.3)
- gap 250: -3.3 (-26.7 to +20.0)
- gap 1000: -10.0 (-30.0 to +10.0)
