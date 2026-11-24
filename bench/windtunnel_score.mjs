// Scores our WindTunnel runs with the board's composite (scripts/readme-charts.mjs):
// 60% attempt success + 20% (1 - log-normalized median cost)
// + 20% (1 - log-normalized median agent time), normalized across every row on
// the board. Our diffusion model is priced at Mercury 2.5's list rates.
//
// Usage: node bench/windtunnel_score.mjs <config-name>=<run.json|dir of N.json>[,...] ...
import fs from "node:fs";
import path from "node:path";
import { isInfraRow } from "./windtunnel/harness/lib.mjs";

const ROOT = path.resolve(import.meta.dirname, "windtunnel");
const MERCURY = { input: 0.20, cached: 0.02, output: 0.75 };
const DIFFUSION_MODEL = "qwen36-iter22000-blk16-arverify-best";

const median = (xs) => { const s = [...xs].sort((a, b) => a - b); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const passed = (r) => r.pass === true || r.pass === "true" || r.success === true;
const aggregate = (rows) => ({
  n: rows.length,
  solved: (() => { const by = {}; for (const r of rows) (by[r.task_id] ??= []).push(passed(r)); return Object.values(by).filter((v) => v.filter(Boolean).length * 2 > v.length).length; })(),
  tasks: new Set(rows.map((r) => r.task_id)).size,
  success: 100 * rows.filter(passed).length / rows.length,
  cost: median(rows.map((r) => +r.est_cost_usd || 0)),
  agent: median(rows.map((r) => +r.agent_s || 0)),
  tokens: median(rows.map((r) => (+r.input_tokens || 0) + (+r.cached_tokens || 0) + (+r.cache_write_tokens || 0) + (+r.output_tokens || 0))),
});

function loadRows(source) {
  const stat = fs.statSync(source);
  if (stat.isFile()) return JSON.parse(fs.readFileSync(source, "utf8")).rows;
  return fs.readdirSync(source).filter((f) => /^\d+\.json$/.test(f)).map((f) => JSON.parse(fs.readFileSync(path.join(source, f), "utf8")));
}

// The standalone arm ran through the harness's Anthropic pricing fallback;
// reprice those rows at Mercury's rates. Jev + ours rows are already priced
// that way by experiments/jev/webmcp/diffusion.mjs.
const reprice = (r) => r.model === DIFFUSION_MODEL
  ? { ...r, est_cost_usd: ((+r.input_tokens || 0) * MERCURY.input + (+r.cached_tokens || 0) * MERCURY.cached + (+r.output_tokens || 0) * MERCURY.output) / 1e6 }
  : r;

const canon = JSON.parse(fs.readFileSync(path.join(ROOT, "results/canonical/run.json"), "utf8")).rows.filter((r) => !isInfraRow(r));
const board = [...new Set(canon.map((r) => `${r.arm}\u0000${r.model}`))].map((key) => {
  const [arm, model] = key.split("\u0000");
  return { name: `${model} · ${arm}`, ours: false, ...aggregate(canon.filter((r) => r.arm === arm && r.model === model)) };
});

for (const spec of process.argv.slice(2)) {
  const [name, sources] = spec.split("=");
  const rows = sources.split(",").flatMap(loadRows).filter((r) => !isInfraRow(r)).map(reprice);
  board.push({ name, ours: true, ...aggregate(rows) });
}

const normalize = (values, value) => {
  const p = values.map(Math.log), c = Math.log(value);
  const min = Math.min(...p), max = Math.max(...p);
  return max === min ? 1 : (c - min) / (max - min);
};
const scored = board.map((b) => ({ ...b,
  score: 100 * (0.6 * b.success / 100
    + 0.2 * (1 - normalize(board.map((a) => a.cost), b.cost))
    + 0.2 * (1 - normalize(board.map((a) => a.agent), b.agent))) }))
  .sort((a, b) => b.score - a.score);

console.log("rank  score  success  solved   n    med$      med_s  config");
scored.forEach((b, i) => console.log(
  `${String(i + 1).padStart(4)}  ${b.score.toFixed(1).padStart(5)}  ${b.success.toFixed(1).padStart(6)}%  ${`${b.solved}/${b.tasks}`.padStart(5)}  ${String(b.n).padStart(3)}  ${b.cost.toFixed(4).padStart(7)}  ${b.agent.toFixed(2).padStart(6)}  ${b.ours ? "* " : "  "}${b.name}`));
