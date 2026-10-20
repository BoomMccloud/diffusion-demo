# Synthetic data benchmark

Yields are per 100 requests; ranges are across 3 replicate(s). Distinct counts clean records whose cosine to every kept record is below the threshold and whose case key is new.

## narrative, open

| model | temp | raw format | format | clean | distinct <0.97 | distinct <0.96 | Vendi | distinct/min |
|---|---|---|---|---|---|---|---|---|
| dllm | 0.6 | 99 (99–99) | 100 (100–100) | 66 (62–69) | 47 (37–53) | 40 (31–47) | 2.2 (2.2–2.3) | 62.6 (49.8–70.8) |
| dllm | 0.8 | 96 (95–98) | 99 (98–100) | 47 (44–49) | 43 (42–44) | 40 (38–42) | 2.4 (2.4–2.5) | 52.1 (51.0–53.5) |
| dllm | 1.0 | 19 (18–20) | 21 (20–22) | 2 (1–2) | 2 (1–2) | 2 (1–2) | – | 0.5 (0.2–0.6) |
| dllm | 1.2 | 0 (0–0) | 0 (0–0) | 0 (0–0) | 0 (0–0) | 0 (0–0) | – | 0.0 (0.0–0.0) |
| qwen | 0.6 | 100 (100–100) | 100 (100–100) | 76 (75–79) | 21 (20–21) | 15 (14–16) | 1.9 (1.8–1.9) | 23.0 (18.6–26.3) |
| qwen | 0.8 | 100 (100–100) | 100 (100–100) | 76 (73–80) | 35 (35–37) | 27 (27–28) | 2.3 (2.3–2.4) | 48.4 (46.6–49.4) |
| qwen | 1.0 | 100 (99–100) | 100 (99–100) | 70 (67–72) | 40 (36–42) | 30 (27–32) | 2.4 (2.4–2.5) | 47.0 (42.1–56.3) |
| qwen | 1.2 | 100 (99–100) | 100 (99–100) | 63 (60–67) | 46 (44–50) | 38 (34–43) | 2.5 (2.5–2.6) | 47.3 (41.9–51.0) |

## Pre-registered comparison

Each model at its best temperature by distinct yield on replicate 0, compared on held-out replicates. Interval: 80% subsamples of request slots or seeds, same slots for both models.

| format | prompting | rep | temps | dllm distinct | qwen distinct | gap | 95% interval | dllm clean | qwen clean |
|---|---|---|---|---|---|---|---|---|---|
| narrative | open | 1 | dllm 0.6, qwen 1.2 | 53 | 50 | +3 | -1 to +9 | 69 | 67 |
| narrative | open | 2 | dllm 0.6, qwen 1.2 | 37 | 45 | -8 | -12 to -3 | 62 | 63 |
