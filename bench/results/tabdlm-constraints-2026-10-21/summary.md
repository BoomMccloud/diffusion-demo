# Batch-wide constraints

30 records per request; temperature 0.6 for both arms; thinking off.

| condition | arm | requests | pass % | exactly 30 valid % | pass % by rule | median distance by rule | distinct ages | median latency s | median tokens |
|---|---|---|---|---|---|---|---|---|---|
| quota | dllm | 30 | 93.3 | 100.0 | {'quota': 93.3} | {'quota': 0} | 30 | 2.715 | 1155 |
| quota | qwen | 30 | 100.0 | 100.0 | {'quota': 100.0} | {'quota': 0} | 30 | 8.48 | 1152 |
| sorted | dllm | 30 | 100.0 | 100.0 | {'sorted': 100.0} | {'sorted': 0} | 30 | 2.903 | 1155 |
| sorted | qwen | 30 | 100.0 | 100.0 | {'sorted': 100.0} | {'sorted': 0} | 30 | 10.601 | 1151 |
| sum | dllm | 30 | 3.3 | 100.0 | {'sum': 3.3} | {'sum': 17} | 30 | 2.678 | 1156 |
| sum | qwen | 30 | 43.3 | 100.0 | {'sum': 43.3} | {'sum': 9} | 21 | 11.915 | 1154 |
| balance | dllm | 30 | 100.0 | 100.0 | {'balance': 100.0} | {'balance': 0} | 30 | 2.839 | 1156 |
| balance | qwen | 30 | 100.0 | 100.0 | {'balance': 100.0} | {'balance': 0} | 30 | 9.719 | 1154 |
| forward | dllm | 30 | 0.0 | 100.0 | {'forward': 0.0} | {'forward': 61} | 30 | 2.86 | 1158 |
| forward | qwen | 30 | 0.0 | 100.0 | {'forward': 0.0} | {'forward': 27} | 30 | 11.96 | 1158 |
| all | dllm | 30 | 0.0 | 100.0 | {'quota': 96.7, 'sorted': 100.0, 'sum': 0.0, 'balance': 100.0, 'forward': 0.0} | {'quota': 0, 'sorted': 0, 'sum': 135, 'balance': 0, 'forward': 107} | 30 | 2.554 | 1154 |
| all | qwen | 30 | 0.0 | 100.0 | {'quota': 100.0, 'sorted': 100.0, 'sum': 13.3, 'balance': 100.0, 'forward': 0.0} | {'quota': 0, 'sorted': 0, 'sum': 135, 'balance': 0, 'forward': 107} | 30 | 11.876 | 1136 |

## dLLM minus Qwen pass rate (95% bootstrap interval)

- `quota`: -0.067 (-0.167 to +0.000)
- `sorted`: +0.000 (+0.000 to +0.000)
- `sum`: -0.400 (-0.600 to -0.200)
- `balance`: +0.000 (+0.000 to +0.000)
- `forward`: +0.000 (+0.000 to +0.000)
- `all`: +0.000 (+0.000 to +0.000)
