# WindTunnel run — fill-ea-qwen36

**Date:** 2026-10-15 · **Preset:** full · **Sites:** easyappointments
**Repeats per task:** 3 · **Approx. cost:** $0.5124

Reproduce:

```bash
npm run bench -- --preset full --sites easyappointments --arms wm-claude
```

Task set: `development tasks` · Harness commit: `5ca8644e23826ebb30108e7bad240b61043bfe67-dirty` · N: `3`

## Headline — task×method combinations solved (out of 8)

**8/8 task×method combinations solved (100.0%).**

| Method | Model | Solved | % |
|---|---|---|---|
| wm-claude | qwen36-iter22000-blk16-arverify-best | 8/8 | 100.0% |

**One-line takeaway:** wm-claude solved 8/8 task×method combinations.

## By difficulty tier

| Tier | wm-claude |
|---|---|
| answer | 4/4 |
| act-short | 1/1 |
| act-long | 1/1 |
| transaction | 2/2 |

## By site (optional)

| Site | wm-claude |
|---|---|
| easyappointments | 8/8 |

## Robustness (optional)

Not implemented.

## Notes

- Skipped runs (missing keys, timeouts): none recorded
- Anomalies or surprises: none recorded
- Sanity checks (the two control sites behaved as expected?): n/a — control sites not in this run
