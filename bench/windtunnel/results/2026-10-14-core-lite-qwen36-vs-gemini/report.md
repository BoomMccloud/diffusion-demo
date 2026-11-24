# WindTunnel run — core-lite-qwen36-vs-gemini

**Date:** 2026-10-14 · **Preset:** lite · **Sites:** core
**Repeats per task:** 3 · **Approx. cost:** $0.2900

Reproduce:

```bash
npm run bench -- --preset lite --sites core --arms wm-claude,wm-gemini
```

Task set: `development tasks` · Harness commit: `5ca8644e23826ebb30108e7bad240b61043bfe67` · N: `3`

## Headline — task×method combinations solved (out of 14)

**14/14 task×method combinations solved (100.0%).**

| Method | Model | Solved | % |
|---|---|---|---|
| wm-claude | qwen36-iter22000-blk16-arverify-best | 7/7 | 100.0% |
| wm-gemini | gemini-3.6-flash | 7/7 | 100.0% |

**One-line takeaway:** wm-claude, wm-gemini solved 14/14 task×method combinations.

## By difficulty tier

| Tier | wm-claude | wm-gemini |
|---|---|---|
| answer | 5/5 | 5/5 |
| act-short | 2/2 | 2/2 |
| act-long | 0/0 | 0/0 |
| transaction | 0/0 | 0/0 |

## By site (optional)

| Site | wm-claude | wm-gemini |
|---|---|---|
| tailwind-nextjs-blog | 2/2 | 2/2 |
| bulletproof-react | 2/2 | 2/2 |
| directory-9d8 | 3/3 | 3/3 |

## Robustness (optional)

Not implemented.

## Notes

- Skipped runs (missing keys, timeouts): none recorded
- Anomalies or surprises: none recorded
- Sanity checks (the two control sites behaved as expected?): controls included — see the per-site table
