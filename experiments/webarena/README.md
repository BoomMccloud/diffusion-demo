# WebArena agent tasks

Runs browser agents on realistic website workflows and analyzes their results.

## Run

Set up the [shared model API](../../docs/api-experiments.md#shared-api-setup-for-the-agent-benchmarks).
Use Python 3.12 in a dedicated environment. For the one-task smoke, set up
or obtain access to the benchmark's Reddit forum snapshot. For a full run,
set up a dedicated instance with all sites. Follow the
[WebArena fixture setup](https://github.com/web-arena-x/webarena/tree/main/environment_docker)
or the [BrowserGym setup](https://github.com/ServiceNow/BrowserGym/tree/v0.14.3/browsergym/webarena).
The local browser must be able to reach those sites, including URLs
embedded in their pages. Reserve the instance for your run because some
tasks modify the fixtures. Check storage before downloading individual
images. The forum tar in the [public mirror](https://archive.org/details/postmill-populated-exposed-withimg)
is about 53 GB before loading it into Docker.

```sh
uv venv --python 3.12 bench/webarena/.venv
. bench/webarena/.venv/bin/activate
uv pip install 'agentlab==0.4.2' 'browsergym==0.14.3'
python -m playwright install chromium
python -m nltk.downloader punkt_tab
```

On Linux, install Chromium's OS libraries with Playwright's
`install-deps chromium` command if the machine lacks them. BrowserGym
expects all seven variables. For `webarena.27`, the forum is the only
one that needs to be running when you skip the stock all-site warm-up.
Use your actual addresses and verify the forum is reachable:

```sh
site=http://127.0.0.1
export WA_HOMEPAGE="$site:80"
export WA_SHOPPING="$site:8082"
export WA_SHOPPING_ADMIN="$site:8083/admin"
export WA_REDDIT="$site:9999"
export WA_GITLAB="$site:9001"
export WA_WIKIPEDIA="$site:8081/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing"
export WA_MAP="$site:443"
curl -fsS "${WA_REDDIT%/}/" >/dev/null
```

From the repo root, preview and run the read-only forum task used in the
historical smoke. Its verifier uses string matching.

```sh
export AGENTLAB_EXP_ROOT="$(mktemp -d)"
python -m bench.webarena.run_webarena --tasks webarena.27 --list-tasks
python -m bench.webarena.run_webarena --model api --tasks webarena.27 \
  --skip-backend-warmup --max-new-tokens 4096 --suffix api-smoke
find "$AGENTLAB_EXP_ROOT" -name summary_info.json
```

Check the task's `summary_info.json` for `cum_reward` and `err_msg`.
Model requests are recorded in `$AGENTLAB_EXP_ROOT/llm_calls/`. A reward
of zero can be a valid scored failure. Before scaling up, set
`--context-window` to your route's context limit if it is below 131,072.
Use `--smoke 1` for one read-only task per site. For all 812 tasks, start
with fresh fixtures and omit the task filter and `--skip-backend-warmup`.
Tasks that grade free-text
answers or unachievable-task explanations also need a judge route.
Set `WA_JUDGE_BASE_URL`, `WA_JUDGE_MODEL`, and `WA_JUDGE_API_KEY` to your
judge's Chat Completions settings. Use `WA_JUDGE_MAX_TOKENS` if it needs
more than the default 768 output tokens. Without a custom route, BrowserGym
uses its built-in OpenAI judge on `gpt-4-1106-preview` and needs
`OPENAI_API_KEY` with access to that model. Record the judge model and
settings because changing them can change the scores.

On 2026-11-24 the hosted GLM API returned a native browser click, and the
runner converted it to a BrowserGym action that ran on a local Chromium
test page. The official one-task smoke could not start because the
historical fixture host denied SSH and the forum archive exceeded local
free space. There is no WebArena score from that check.

## Contents

- [webarena](code/webarena): code; stored at `bench/webarena`.
- [webarena_diffuspace_handoff.md](findings/webarena_diffuspace_handoff.md): findings; stored at `docs/webarena_diffuspace_handoff.md`.
- [webarena_qwen36_findings.md](findings/webarena_qwen36_findings.md): findings; stored at `docs/webarena_qwen36_findings.md`.

These links point to the original files, so existing commands and imports continue
to use their documented paths. Some result or download links refer to local,
untracked files and may be absent in another checkout. See the linked findings
or source README for methods, run status, and limitations before interpreting
results. Running model experiments may require the Spark, dependencies, and
credentials; this folder does not itself launch an experiment.
