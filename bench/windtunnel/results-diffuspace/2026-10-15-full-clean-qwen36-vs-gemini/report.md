# WindTunnel run — full-clean-qwen36-vs-gemini

**Date:** 2026-10-15 · **Preset:** full · **Sites:** full
**Repeats per task:** 3 · **Approx. cost:** $2.0395

Reproduce:

```bash
npm run bench -- --preset full --sites full --arms wm-claude,wm-gemini
```

Task set: `development tasks` · Harness commit: `5ca8644e23826ebb30108e7bad240b61043bfe67-dirty` · N: `3`

## Headline — task×method combinations solved (out of 66)

**66/66 task×method combinations solved (100.0%).**

| Method | Model | Solved | % |
|---|---|---|---|
| wm-claude | qwen36-iter22000-blk16-arverify-best | 29/29 | 100.0% |
| wm-gemini | gemini-3.6-flash | 37/37 | 100.0% |

**One-line takeaway:** wm-claude, wm-gemini solved 66/66 task×method combinations.

## By difficulty tier

| Tier | wm-claude | wm-gemini |
|---|---|---|
| answer | 12/12 | 16/16 |
| act-short | 10/10 | 11/11 |
| act-long | 6/6 | 7/7 |
| transaction | 1/1 | 3/3 |

## By site (optional)

| Site | wm-claude | wm-gemini |
|---|---|---|
| tailwind-nextjs-blog | 2/2 | 2/2 |
| bulletproof-react | 2/2 | 2/2 |
| learnhouse | 7/7 | 7/7 |
| idurar-erp-crm | 8/8 | 8/8 |
| hi-events | 10/10 | 10/10 |
| easyappointments | 0/0 | 8/8 |

## Robustness (optional)

Not implemented.

## Notes

- Skipped runs (missing keys, timeouts): none recorded
- Anomalies or surprises: none recorded
- Sanity checks (the two control sites behaved as expected?): controls included — see the per-site table
