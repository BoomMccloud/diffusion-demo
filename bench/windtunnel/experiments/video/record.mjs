// diffusion-demo: record WebMCP attempts for a side-by-side video.
//
// Runs the unmodified wm-claude (pointed at our diffusion model) and wm-gemini
// arms through the harness's runBatch. Two wrappers add what the video needs
// without touching hash-pinned arm code: every browser context records video,
// and global fetch logs each model call's start, end and token counts.
//
// Usage (from the windtunnel root, with env.sh sourced):
//   node experiments/video/record.mjs --out /tmp/webmcp-video \
//     --tasks idurar-erp-crm:id-6,learnhouse:lh-7 \
//     --repeats 3
//
// Each attempt is saved as <out>/<task>/<model>-<k>.webm, with its row,
// video start time and model calls in <out>/takes.jsonl.
import fs from "node:fs";
import path from "node:path";
import { parseArgs } from "node:util";
import { chromium } from "playwright";
import { run as runWMClaude } from "../../arms/wm-claude.mjs";
import { run as runWMGemini } from "../../arms/wm-gemini.mjs";
import { bootCapsule } from "../../harness/capsule.mjs";
import { runBatch } from "../../harness/run.mjs";
import { loadTasks, resolveTask } from "../../harness/tasks.mjs";

const { values: args } = parseArgs({ options: {
  out: { type: "string" }, tasks: { type: "string" }, port: { type: "string", default: "3215" },
  repeats: { type: "string", default: "3" },
  "clover-model": { type: "string", default: "qwen36-iter22000-blk16-arverify-best" },
  "gemini-model": { type: "string", default: "gemini-3.6-flash" },
} });
if (!args.out || !args.tasks) throw new Error("--out and --tasks site:id,... are required");
for (const key of ["ANTHROPIC_BASE_URL", "GEMINI_API_KEY"]) if (!process.env[key]) throw new Error(`Missing ${key}`);

const ARMS = [
  { id: "wm-claude", key: "ours", run: runWMClaude, model: args["clover-model"], webmcp: true },
  { id: "wm-gemini", key: "gemini", run: runWMGemini, model: args["gemini-model"], webmcp: true },
];
const VIEWPORT = { width: 1280, height: 800 };
const out = path.resolve(args.out);
fs.mkdirSync(path.join(out, ".video"), { recursive: true });

// Model calls, appended as they finish. The arms read globalThis.fetch when
// they create their clients, so patching it here covers both providers.
const calls = [];
const realFetch = globalThis.fetch;
globalThis.fetch = async (input, init) => {
  const url = String(input?.url ?? input);
  const provider = url.includes("/v1/messages") ? "anthropic" : url.includes("/interactions") ? "gemini" : null;
  if (!provider) return realFetch(input, init);
  const t_start = Date.now();
  const response = await realFetch(input, init);
  const text = await response.clone().text();
  const t_end = Date.now();
  let usage = {};
  try { usage = JSON.parse(text).usage ?? {}; } catch {}
  const output_tokens = provider === "anthropic" ? usage.output_tokens ?? 0
    : (usage.total_output_tokens ?? 0) + (usage.total_thought_tokens ?? 0);
  calls.push({ provider, t_start, t_end, status: response.status, output_tokens, usage });
  return response;
};

// Every context records video; remember each page so its file can be found after close.
let current = null;
const real = await chromium.launch({ headless: true, ...(process.env.WT_CHROME ? { executablePath: process.env.WT_CHROME } : {}) });
const browser = {
  async newContext(options) {
    const context = await real.newContext({ ...options, viewport: VIEWPORT,
      recordVideo: { dir: path.join(out, ".video"), size: VIEWPORT } });
    current = { video_t0: Date.now(), page: null };
    const newPage = context.newPage.bind(context);
    context.newPage = async () => (current.page = await newPage());
    return context;
  },
};

const wanted = args.tasks.split(",").map((s) => { const [site, id] = s.split(":"); return { site, id }; });
const sites = [...new Set(wanted.map((t) => t.site))];
const log = path.join(out, "takes.jsonl");
const taken = {};
try {
  for (const [s, site] of sites.entries()) {
    const tasks = wanted.filter((t) => t.site === site)
      .map(({ id }) => resolveTask(loadTasks(site).find((t) => t.id === id) ?? (() => { throw new Error(`unknown task ${site}:${id}`); })(), 1));
    // Alternate which model goes first per site, so drift in load is shared.
    for (const method of s % 2 ? [...ARMS].reverse() : ARMS) {
      await runBatch({
        siteId: site, method, tasks, n: Number(args.repeats), seed: 1, port: Number(args.port), model: method.model, browser,
        boot: (id, options) => bootCapsule(id, { ...options, env: { ...process.env, WT_WEBMCP: "1" } }),
        onResult: async (row) => {
          const take = current;
          const dir = path.join(out, row.task_id);
          fs.mkdirSync(dir, { recursive: true });
          const k = (taken[`${row.task_id}/${method.key}`] = (taken[`${row.task_id}/${method.key}`] ?? 0) + 1);
          const video = path.join(dir, `${method.key}-${k}.webm`);
          if (take?.page) fs.renameSync(await take.page.video().path(), video);
          const mine = calls.filter((c) => take && c.t_start >= take.video_t0);
          fs.appendFileSync(log, JSON.stringify({ ...row, model_key: method.key, take: k, video: path.relative(out, video),
            video_t0: take?.video_t0, calls: mine }) + "\n");
          calls.length = 0;
          console.log(`${row.task_id} ${method.key}: ${row.success ? "passed" : "failed"} in ${row.agent_s} s, ${mine.length} model calls`);
        },
      });
    }
  }
} finally {
  await real.close();
}
