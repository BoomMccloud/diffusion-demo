# Clover Office evidence package

Updated 2026-11-19. Internal working evidence for marketing and partner discussions. The package records observed results and limits; it does not establish a general price-performance ranking. Model pricing and cost per completed task were not measured.

## Evidence at a glance

| Comparison | Result | What it means |
| --- | --- | --- |
| WorkBuddy Office, 50 tasks, deterministic checks | Clover 74.44%; Qwen3.6-Flash 72.14% | Equal-weight mean of one scored attempt per task. Same task set and main CodeBuddy settings; providers differ. Ten Qwen scores came from fresh replacement runs after a verifier transfer failure, and one came from a recovered log. No rubric judging. |
| Clover Office, combined checks | 70.40% | Same 50 Clover tasks with deferred Codex/Luna rubric grading and offline merging. Different metric from the deterministic-only figure. |
| GLM-5.2 Office, CodeBuddy | 79.60%, previously recorded from Tencent's leaderboard | External result, not a controlled comparison. The leaderboard states a three-run protocol; Clover used one attempt and non-native deferred rubric grading. The source row and version must be independently captured before publication: the current page renders its table dynamically and the row was not verified during this package update. |
| Clover and GLM-5.2 model sizes | 35B total / 3B active vs 744B / 40B | About 21.3 times fewer total and 13.3 times fewer active parameters for Clover. Parameters are not a direct measurement of memory, cost, or throughput. [Clover model article](https://huggingface.co/blog/Diffuspace/clover-35b-a3b-preview); [GLM model repository](https://github.com/zai-org/glm-5/blob/main/README.md). |
| WPS board demo, original writer | Clover 300/379 via WPS in 162.996 s. Qwen 251/379 via Python in 268.907 s; four WPS batches rejected and no WPS edits. | Single runs. The Qwen output did not satisfy the WPS editing requirement. Agent times include different tool behavior and paced WPS edits. |
| WPS board proxy stream rate, same two runs | Clover 1,216.6 vs Qwen 218.0 reported output tokens/s, approximately 5.6× | Provider completion tokens divided by summed first-to-last output-delta intervals. Not pure server decode TPS: excludes time to first output, includes provider-reported reasoning, and depends on network, chunking and token accounting. Hosted services and model providers differ. |
| WPS board, repaired writer Qwen | 305/379 via WPS in 237.467 s | Separate Qwen attempt with partial-acceptance writer. It is not an apples-to-apples result against the old-writer Clover run. |
| Local inference | Vendor reports 101.8 tokens/s for INT4 Clover on RTX 5070 Ti, 16 GB, on MATH-500. | Vendor result, not an Office benchmark. The WPS demos used hosted inference, even though WPS and CodeBuddy ran locally. See the [Clover model article](https://huggingface.co/blog/Diffuspace/clover-35b-a3b-preview). |

Clover won 21 task scores, Qwen won 24, and five were tied. The 2.30-point difference between their means is not evidence of statistical significance. The provider's `qwen3.6-flash` route has not been verified as the Qwen3.6-35B-A3B checkpoint.

## Contents

- `data/office-50-task-comparison.csv`: all 50 paired deterministic scores and Qwen score provenance. `data/office-50-task-summary.json` records the means and replacement counts.
- `data/qwen-original-scores.json` and `data/qwen-replacement-scores.json`: compiled source scores. The recovered channel-period verifier log is in `../qwen36-flash-office-2026-11-19/recovery/`.
- `data/clover-office-combined-scores.json` and `data/clover-grading-summary.json`: Clover task and rubric data, including the 70.40% combined result and grading methodology.
- `data/board-instrumented-original-summary.json`: original instrumented Clover and Qwen runs. Note that its Qwen entry is the earlier 305/379 non-WPS attempt, not the 251/379 repeat used in the video. The repeat's per-request log and output are in `../wps-office-pilot/board-video-qwen/runs/20261118-234234/`. Clover's run is in `../wps-office-pilot/board-video/runs/20261118-231505/`.
- `raw-spark/office-runs.tar.gz`: local copy of the Spark's retained Clover Office and Qwen Office job directories and three queue checkpoints. The archive has 114 verifier score files, 117 top-level directories, and includes original failed trials and replacement runs. `raw-spark/SHA256SUMS` records its SHA-256. The archive includes the root-owned score files, copied through a read-only container mount. It is an internal working archive, not a sanitized public release; benchmark artifacts can contain sensitive-looking strings. Review its contents before sharing externally.
- `historical/`: the earlier, incomplete 43-task snapshot. It is retained for provenance only and must not be used as the final result.
- `../qwen36-flash-office-2026-11-19/README.md`: configurations, verifier repair, original failures, and rerun history. `verifier-transfer.patch` preserves the fix.
- `../wps-office-pilot/README.md`: five-task WPS pilot, board attempts, writer behavior and caveats. `../wps-office-pilot/comparison-video/qwen36-original-repeat/comparison-large-text-30s.mp4` is the 30-second original-writer video. `../wps-office-pilot/comparison-video/qwen36-wpsfix/comparison-30s.mp4` shows the separately repaired writer.

## Reproducibility and limitations

The Office 50-task comparison uses CodeBuddy 2.109.3, the same task list and main rollout settings, serial execution, thinking enabled, and deterministic task checks. Providers and model-specific serving behavior differ. Published task timeouts, the 48-turn cap, and context constraints apply. The ten Qwen replacement attempts should not be described as retries selected for better scores: their original scores were unrecoverable because verifier files were not transferred; their original task workspaces were not retained. The first eleven original trials included ten unrecoverable scores and one recovered score. The full raw artifacts cannot reconstruct those missing workspaces.

Clover's combined score uses deferred rubric grading through Codex/Luna with offline merging, rather than the native leaderboard judge path. It should not be put next to Qwen's deterministic score as though the same metric. Tencent's GLM score, if independently verified, is directional context, not an official score for Clover or a controlled head-to-head.

The WPS output scores are deterministic check fractions, not benchmark-wide Office scores. The original Qwen writer rejects a whole batch when one edit fails validation; its failed WPS run subsequently wrote a Python-generated deck. The repaired writer changes those semantics. Request counts and token totals are provider-reported and reconciled with CodeBuddy. Different tokenizers and network conditions limit cross-provider throughput comparisons.

The original archive remains on the Spark in `~/diffusion-demo/runs/workbuddy-smoke/results/`; the package's archive captures the run files available on 2026-11-19. The original benchmark task images, model weights, provider internals and full hosting configuration are not included. The old 1,550 aggregate tokens/s endpoint result lacks a located raw archive and verified relationship to this Clover deployment; do not treat it as verified evidence for this comparison.

## Before external publication

1. Capture the exact Tencent leaderboard row, version, harness and date and verify 79.60%. Document the different evaluation protocols beside the comparison.
2. Verify DashScope model identity and run controlled speed tests with identified hardware, revisions, precision, tokenization, concurrency and task completion metrics. Do not present the proxy stream rate as measured local decode speed.
3. Measure actual prices, infrastructure costs and completed-task costs before claiming a price-performance ranking. Repeat runs to estimate variability.
4. Review the internal raw archive and videos for credentials, personal information and other content before public release. The benchmark folders and evidence package are currently untracked in Git; arrange appropriate backup or versioning.
