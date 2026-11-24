# Archive

This directory keeps material that is useful for provenance but is not part of
the current business dependency benchmark workflow.

## Contents

- `legacy-demo/`: superseded schedule-puzzle cells, the optimization lab,
  terminal runner, micro-benchmark, and their historical documentation.
- `artifact-bundles/`: compressed copies of already-extracted dependency-density
  evidence, plus the saved Linux `dependency-tokenizer` executable. Their
  original directory structure is preserved below this folder so provenance is
  easy to reconstruct. These bundles are not in git, because one exceeds
  GitHub's 100 MB file limit. They exist only in the original working copy, and
  `MANIFEST.sha256` records their hashes so a local copy can be verified.

The active source of truth remains `AGENTS.md`. Saved JSON, JSONL, logs,
registrations, manifests, and summaries stay under `bench/results/` because they
support the current 48-decision screen-size conclusion. Historical proposal
ledgers retain their original path references and are not rewritten.

Do not use archived scripts as current launch instructions. See `bench/README.md` for DGX Spark setup.
