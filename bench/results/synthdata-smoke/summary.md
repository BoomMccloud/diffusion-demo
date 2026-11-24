# Synthetic data benchmark

Yields are per 100 requests; ranges are across 1 replicate(s). Distinct counts clean records whose cosine to every kept record is below the threshold and whose case key is new.

## narrative, open

| model | temp | raw format | format | clean | distinct <0.97 | distinct <0.96 | Vendi | distinct/min |
|---|---|---|---|---|---|---|---|---|
| dllm | 0.8 | 83 | 100 | 17 | 17 | 17 | – | 16.2 |
| qwen | 0.8 | 100 | 100 | 83 | 83 | 83 | 1.8 | 34.1 |

## narrative, seeded

| model | temp | raw format | format | clean | distinct <0.97 | distinct <0.96 | within-seed distinct | Vendi | distinct/min |
|---|---|---|---|---|---|---|---|---|---|
| dllm | 0.8 | 83 | 100 | 17 | 17 | 17 | – | – | 17.6 |
| qwen | 0.8 | 100 | 100 | 83 | 83 | 83 | – | 2.0 | 49.7 |

## record, open

| model | temp | raw format | format | clean | distinct <0.97 | distinct <0.96 | Vendi | distinct/min |
|---|---|---|---|---|---|---|---|---|
| dllm | 0.8 | 100 | 100 | 67 | 67 | 67 | 1.7 | 334.3 |
| qwen | 0.8 | 83 | 83 | 83 | 33 | 33 | 1.5 | 40.2 |

## record, seeded

| model | temp | raw format | format | clean | distinct <0.97 | distinct <0.96 | within-seed distinct | Vendi | distinct/min |
|---|---|---|---|---|---|---|---|---|---|
| dllm | 0.8 | 83 | 83 | 33 | 33 | 33 | – | – | 176.0 |
| qwen | 0.8 | 83 | 83 | 50 | 50 | 50 | – | – | 32.0 |

## Pre-registered comparison

Each model at its best temperature by distinct yield on replicate 0, compared on held-out replicates. Interval: 80% subsamples of request slots or seeds, same slots for both models.

With one replicate, the temperature is chosen and compared on the same data, so this table only checks the pipeline.

| format | prompting | rep | temps | dllm distinct | qwen distinct | gap | 95% interval | dllm clean | qwen clean |
|---|---|---|---|---|---|---|---|---|---|
| narrative | open | 0 | dllm 0.8, qwen 0.8 | 17 | 83 | -67 | -100 to -50 | 17 | 83 |
| narrative | seeded | 0 | dllm 0.8, qwen 0.8 | 17 | 83 | -67 | -100 to -50 | 17 | 83 |
| record | open | 0 | dllm 0.8, qwen 0.8 | 67 | 33 | +33 | +0 to +50 | 67 | 83 |
| record | seeded | 0 | dllm 0.8, qwen 0.8 | 33 | 50 | -17 | -50 to +25 | 33 | 50 |
