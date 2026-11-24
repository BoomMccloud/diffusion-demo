# WindTunnel run — fill-dir-medusa-qwen36-vs-gemini

**Date:** 2026-10-15 · **Preset:** full · **Sites:** directory-9d8,nextjs-starter-medusa
**Repeats per task:** 3 · **Approx. cost:** $0.8860

Reproduce:

```bash
npm run bench -- --preset full --sites directory-9d8,nextjs-starter-medusa --arms wm-claude,wm-gemini
```

Task set: `development tasks` · Harness commit: `5ca8644e23826ebb30108e7bad240b61043bfe67-dirty` · N: `3`

## Headline — task×method combinations solved (out of 24)

**24/24 task×method combinations solved (100.0%).**

| Method | Model | Solved | % |
|---|---|---|---|
| wm-claude | qwen36-iter22000-blk16-arverify-best | 12/12 | 100.0% |
| wm-gemini | gemini-3.6-flash | 12/12 | 100.0% |

**One-line takeaway:** wm-claude, wm-gemini solved 24/24 task×method combinations.

## By difficulty tier

| Tier | wm-claude | wm-gemini |
|---|---|---|
| answer | 5/5 | 5/5 |
| act-short | 5/5 | 5/5 |
| act-long | 1/1 | 1/1 |
| transaction | 1/1 | 1/1 |

## By site (optional)

| Site | wm-claude | wm-gemini |
|---|---|---|
| directory-9d8 | 3/3 | 3/3 |
| nextjs-starter-medusa | 9/9 | 9/9 |

## Robustness (optional)

Not implemented.

## Notes

- Skipped runs (missing keys, timeouts): none recorded
- Anomalies or surprises: none recorded
- Sanity checks (the two control sites behaved as expected?): n/a — control sites not in this run
