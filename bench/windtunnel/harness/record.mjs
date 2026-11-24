// diffusion-demo: opt-in attempt recording, enabled only by `--record-video DIR`.
//
// Films each attempt's page with Playwright's recordVideo and logs wall-clock
// (Date.now() ms) timestamps for every model call, WebMCP tool call and main
// frame navigation. Arm code is not touched: model calls are seen through
// global fetch, which both the Anthropic SDK and the Gemini REST arm use, and
// tool calls through page.evaluate, which executeBridgeTool calls with
// { name, args }. Output: DIR/<task>/<arm>-<k>.webm and DIR/timings.json.
import fs from "node:fs";
import path from "node:path";

// After the arm returns and the harness has scored the attempt, keep the page
// open this long before run.mjs closes the context, so the film shows what the
// last tool call did to the page (Medusa navigates to the order confirmation
// ~150 ms after complete_checkout returns and renders it a second or two
// later). No metric includes this time: agent_s and wall_clock_s are taken
// before the context closes.
const HOLD_MS = 3000;

const modelProvider = (url) => url.includes("/v1/messages") ? "anthropic" : url.includes("/interactions") ? "gemini" : null;

export function createRecorder(dir) {
  const out = path.resolve(dir);
  const raw = path.join(out, ".video");
  fs.mkdirSync(raw, { recursive: true });
  const takes = [];
  const counts = {};
  let events = [];
  let current = null;

  const realFetch = globalThis.fetch;
  globalThis.fetch = async (input, init) => {
    const provider = modelProvider(String(input?.url ?? input));
    if (!provider) return realFetch(input, init);
    const event = { kind: "model", provider, t_start: Date.now() };
    events.push(event);
    try {
      const response = await realFetch(input, init);
      const text = await response.clone().text();
      event.t_end = Date.now();
      event.status = response.status;
      try { const usage = JSON.parse(text).usage; if (usage) event.usage = usage; } catch { /* non-JSON body */ }
      return response;
    } catch (error) {
      event.t_end = Date.now();
      event.error = error.message;
      throw error;
    }
  };

  const wrap = (browser) => ({
    close: () => browser.close(),
    async newContext(options = {}) {
      const size = options.viewport ?? { width: 1280, height: 800 };
      const context = await browser.newContext({ ...options, recordVideo: { dir: raw, size } });
      const newPage = context.newPage.bind(context);
      const close = context.close.bind(context);
      context.close = async (...rest) => {
        const take = current;
        await new Promise((resolve) => setTimeout(resolve, HOLD_MS));
        // The video file ends at close; its first frame comes at first paint,
        // so the video start is t_close minus the file's duration.
        if (take) take.t_close = Date.now();
        return close(...rest);
      };
      context.newPage = async () => {
        const video_t0 = Date.now();
        const page = await newPage();
        current = { video_t0, page };
        page.on?.("framenavigated", (frame) => {
          if (frame === page.mainFrame()) events.push({ kind: "navigation", t: Date.now(), url: frame.url() });
        });
        const evaluate = page.evaluate.bind(page);
        page.evaluate = async (fn, arg) => {
          if (!arg || typeof arg !== "object" || typeof arg.name !== "string" || !("args" in arg)) return evaluate(fn, arg);
          const event = { kind: "tool", name: arg.name, args: arg.args, t_start: Date.now() };
          events.push(event);
          try {
            const result = await evaluate(fn, arg);
            event.t_end = Date.now();
            event.result = JSON.stringify(result ?? null).slice(0, 2000);
            return result;
          } catch (error) {
            event.t_end = Date.now();
            event.error = error.message;
            throw error;
          }
        };
        return page;
      };
      return context;
    },
  });

  // Called with each finished row, after run.mjs has closed the context, so
  // the video file is complete.
  async function save(row) {
    const take = current;
    current = null;
    const key = `${row.task_id}/${row.arm}`;
    const k = (counts[key] = (counts[key] ?? 0) + 1);
    let video = null;
    const source = take?.page?.video?.() ? await take.page.video().path() : null;
    if (source && fs.existsSync(source)) {
      video = path.join(row.task_id, `${row.arm}-${k}.webm`);
      fs.mkdirSync(path.join(out, row.task_id), { recursive: true });
      fs.renameSync(source, path.join(out, video));
    }
    const { transcript, final_text, ...lean } = row;
    takes.push({ ...lean, take: k, video, video_t0: take?.video_t0 ?? null, t_close: take?.t_close ?? null, final_text, events });
    events = [];
    fs.writeFileSync(path.join(out, "timings.json"), JSON.stringify({ clock: "Date.now() ms", takes }, null, 2));
  }

  return { wrap, save };
}
