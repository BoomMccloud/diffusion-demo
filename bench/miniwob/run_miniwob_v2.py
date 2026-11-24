import json
import urllib.request
import re
import time
import subprocess
import ast
import sys
import os
import glob
import argparse
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))

API_URL = os.environ.get("MINIWOB_DIFFUSION_URL", "http://43.107.54.53:31003/v1/chat/completions")

SYSTEM_PROMPT = """You are an autonomous web agent solving MiniWoB++ benchmark tasks.
You receive:
1. The Task Goal.
2. Page Context (visible text, equations, tables, etc.).
3. Interactive elements on the page with their CSS selectors, values, states, and coordinates.

Available Actions:
- click(selector): click an element by selector
- fill(selector, text): type text into an input or textarea
- select(selector, text): select an option from a dropdown (<select>) element
- press(selector, key): focus an element and press a key (e.g. "Enter", "ArrowRight", "ArrowLeft")
- click_coords(x, y): click at coordinates (x, y) on canvas or page
- drag_coords(x1, y1, x2, y2): drag mouse from (x1, y1) to (x2, y2)

Guidelines:
1. Read the Goal and Page Context carefully.
2. Choose the most specific selector or action.
3. If multiple actions are needed (e.g. fill username, fill password, click submit), do ONE action per step.
4. Output your reasoning, then output exactly one action line:
Action: <action_call>

Examples:
Action: click("button:has-text('Submit')")
Action: fill("#password", "abcd")
Action: fill("#math-answer", "7")
Action: click(".email-thread:has-text('Casey') .star")
Action: click(".color[data-color='orange']")
Action: select("#options", "Antarctica")
Action: press(".ui-slider-handle", "ArrowRight")
Action: click_coords(75, 120)
Action: drag_coords(50, 100, 120, 100)
"""

class RateLimiter:
    """Enforces RPS < 2 by maintaining at least min_interval seconds between API calls."""
    def __init__(self, min_interval=1.0):
        self.min_interval = min_interval
        self.last_call_time = 0.0
        self.call_timestamps = []

    def acquire(self):
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.min_interval:
            sleep_needed = self.min_interval - elapsed
            time.sleep(sleep_needed)
        call_time = time.time()
        self.last_call_time = call_time
        self.call_timestamps.append(call_time)
        return call_time

    def get_stats(self):
        if len(self.call_timestamps) < 2:
            return {"total_calls": len(self.call_timestamps), "peak_rps": 0.0, "avg_rps": 0.0}
        
        intervals = [t2 - t1 for t1, t2 in zip(self.call_timestamps[:-1], self.call_timestamps[1:])]
        min_interval = min(intervals) if intervals else 1.0
        peak_rps = 1.0 / min_interval if min_interval > 0 else 0.0
        total_time = self.call_timestamps[-1] - self.call_timestamps[0]
        avg_rps = (len(self.call_timestamps) - 1) / total_time if total_time > 0 else 0.0
        return {
            "total_calls": len(self.call_timestamps),
            "peak_rps": peak_rps,
            "avg_rps": avg_rps
        }

rate_limiter = RateLimiter(min_interval=1.0)  # Guarantees RPS <= 1.0 < 2.0

# Token usage from the most recent API response.
last_usage = {}

# Set MINIWOB_STREAM=1 to stream responses and record when each piece of the
# reasoning and answer arrived. Off by default, matching the October runs.
STREAM = os.environ.get("MINIWOB_STREAM") == "1"

# Timing of the most recent call: start time and [seconds, reasoning chars, content chars] events.
last_stream = {}

def _read_stream(req, t0):
    reasoning, content, events = "", "", []
    with urllib.request.urlopen(req, timeout=30) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:") or line.endswith("[DONE]"):
                continue
            chunk = json.loads(line[5:])
            if chunk.get("usage"):
                last_usage.clear()
                last_usage.update(chunk["usage"])
            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                reasoning += delta.get("reasoning_content") or ""
                content += delta.get("content") or ""
            events.append([round(time.time() - t0, 3), len(reasoning), len(content)])
    last_stream["events"] = events
    return reasoning, content, time.time() - t0

def query_model(messages):
    rate_limiter.acquire()
    payload = {
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.1,
        "chat_template_kwargs": {
            "enable_thinking": True
        }
    }
    if STREAM:
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
    model = os.environ.get("MINIWOB_DIFFUSION_MODEL")
    if model:
        payload["model"] = model
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("DIFFUSION_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers
    )
    t0 = time.time()
    last_stream.clear()
    last_stream["t_start"] = t0
    if STREAM:
        last_usage.clear()
        return _read_stream(req, t0)
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        latency = time.time() - t0
        last_usage.clear()
        last_usage.update(res.get("usage") or {})
        msg = res["choices"][0]["message"]
        return msg.get("reasoning_content", ""), msg.get("content", ""), latency

def parse_action(content, reasoning_content=""):
    for text in [content, reasoning_content]:
        if not text:
            continue
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("Action:"):
                act = line[len("Action:"):].strip()
                if act:
                    return act
        m = re.search(r"Action:\s*([a-zA-Z_]+\(.*\))", text)
        if m:
            return m.group(1).strip()
    return None

def execute_action(page, action_str):
    try:
        tree = ast.parse(action_str, mode='eval')
        call = tree.body
        func_name = call.func.id
        args = [ast.literal_eval(arg) for arg in call.args]
        
        if func_name == "click":
            sel = args[0]
            page.locator(sel).first.click(timeout=3500)
            return True
        elif func_name == "fill":
            sel, val = args[0], str(args[1])
            page.locator(sel).first.fill(val, timeout=3500)
            return True
        elif func_name == "select":
            sel, val = args[0], str(args[1])
            try:
                page.locator(sel).first.select_option(label=val, timeout=2500)
            except Exception:
                page.locator(sel).first.select_option(value=val, timeout=2500)
            return True
        elif func_name == "press":
            sel, key = args[0], str(args[1])
            page.locator(sel).first.press(key, timeout=2500)
            return True
        elif func_name == "click_coords":
            x, y = int(args[0]), int(args[1])
            page.mouse.click(x, y)
            return True
        elif func_name == "drag_coords":
            x1, y1, x2, y2 = int(args[0]), int(args[1]), int(args[2]), int(args[3])
            page.mouse.move(x1, y1)
            page.mouse.down()
            time.sleep(0.1)
            page.mouse.move(x2, y2)
            time.sleep(0.1)
            page.mouse.up()
            return True
    except Exception:
        pass
    
    # Fallback string parsing
    try:
        if action_str.startswith("click(") and action_str.endswith(")"):
            inner = action_str[len("click("):-1].strip()
            if (inner.startswith('"') and inner.endswith('"')) or (inner.startswith("'") and inner.endswith("'")):
                inner = inner[1:-1]
            page.locator(inner).first.click(timeout=3500)
            return True
        elif action_str.startswith("fill(") and action_str.endswith(")"):
            inner = action_str[len("fill("):-1].strip()
            parts = inner.split(",", 1)
            sel = parts[0].strip(" '\"")
            val = parts[1].strip(" '\"")
            page.locator(sel).first.fill(val, timeout=3500)
            return True
    except Exception as e:
        print(f"  [Execution warning for {action_str}: {e}]")
    return False

def extract_dom_v2(page):
    info = page.evaluate("""() => {
        const taskArea = document.querySelector("#area") || document.body;
        
        // Extract meaningful text context
        let textContent = taskArea.innerText.trim();
        // Remove excessive empty lines
        textContent = textContent.replace(/\\n{3,}/g, '\\n\\n');

        const elements = [];
        const seenSelectors = new Set();

        // 1. Specific domain-rich elements
        // Colored boxes
        taskArea.querySelectorAll(".color").forEach((c) => {
            const col = c.getAttribute("data-color") || c.style.backgroundColor;
            const sel = col ? `.color[data-color="${col}"]` : ".color";
            elements.push({
                type: "color_box",
                color: col,
                selector: sel
            });
        });

        // Email threads & action icons
        taskArea.querySelectorAll(".email-thread").forEach((thread) => {
            const sender = thread.querySelector(".email-sender") ? thread.querySelector(".email-sender").innerText.trim() : "";
            const subject = thread.querySelector(".email-subject") ? thread.querySelector(".email-subject").innerText.trim() : "";
            if (sender) {
                elements.push({
                    type: "email_thread",
                    sender: sender,
                    subject: subject,
                    selector: `.email-thread:has-text("${sender}")`
                });
                elements.push({
                    type: "email_star",
                    for_sender: sender,
                    selector: `.email-thread:has-text("${sender}") .star`
                });
                elements.push({
                    type: "email_trash",
                    for_sender: sender,
                    selector: `.email-thread:has-text("${sender}") .trash`
                });
            }
        });

        // Datepicker calendar popup if visible
        const dp = document.querySelector("#ui-datepicker-div");
        if (dp && window.getComputedStyle(dp).display !== "none") {
            dp.querySelectorAll("a.ui-state-default").forEach((a) => {
                const day = a.innerText.trim();
                elements.push({
                    type: "calendar_day",
                    day: day,
                    selector: `#ui-datepicker-div a.ui-state-default:has-text("${day}")`
                });
            });
        }

        // Slider handles
        taskArea.querySelectorAll(".ui-slider").forEach((s) => {
            const handle = s.querySelector(".ui-slider-handle");
            const val = $(s).slider ? $(s).slider("value") : "";
            elements.push({
                type: "slider",
                value: val,
                selector: handle ? ".ui-slider-handle" : `#${s.id}`
            });
        });

        // 2. Standard interactive elements
        // Buttons
        document.querySelectorAll("button, [role='button'], input[type='button'], input[type='submit']").forEach((b) => {
            const txt = b.innerText ? b.innerText.trim() : (b.value || "");
            let sel = b.id ? '#' + b.id : '';
            if (!sel && b.className && typeof b.className === 'string') {
                if (b.className.includes('ui-dialog-titlebar-close')) sel = 'button.ui-dialog-titlebar-close';
                else if (b.className.includes('secondary-action')) sel = 'button.secondary-action';
            }
            if (!sel && txt) sel = `button:has-text("${txt}")`;
            if (!sel) sel = 'button';
            elements.push({
                type: "button",
                text: txt,
                selector: sel
            });
        });

        // Dropdowns
        taskArea.querySelectorAll("select").forEach((s) => {
            const opts = Array.from(s.options).map(o => o.text.trim());
            const sel = s.id ? '#' + s.id : (s.name ? `select[name="${s.name}"]` : 'select');
            elements.push({
                type: "select",
                selector: sel,
                options: opts.slice(0, 15),
                current_value: s.value
            });
        });

        // Accordion headers
        taskArea.querySelectorAll("h3, .ui-accordion-header").forEach((h) => {
            const txt = h.innerText.trim();
            const exp = h.getAttribute('aria-expanded') === 'true' || h.classList.contains('ui-accordion-header-active');
            elements.push({
                type: "accordion",
                text: txt,
                expanded: exp,
                selector: `h3:has-text("${txt}")`
            });
        });

        // Links
        taskArea.querySelectorAll("a, .alink, [role='link']").forEach((a) => {
            const txt = a.innerText.trim();
            if (txt) {
                let sel = a.id ? '#' + a.id : '';
                if (!sel) {
                    sel = a.tagName.toLowerCase() === 'a' ? `a:has-text("${txt}")` : `.alink:has-text("${txt}")`;
                }
                elements.push({
                    type: "link",
                    text: txt,
                    selector: sel
                });
            }
        });

        // Inputs & Textareas
        taskArea.querySelectorAll("input, textarea").forEach((inp) => {
            const tag = inp.tagName.toLowerCase();
            const t = tag === 'textarea' ? 'textarea' : (inp.type || 'text');
            if (['button', 'submit'].includes(t)) return;
            let label = '';
            if (inp.labels && inp.labels[0]) label = inp.labels[0].innerText.trim();
            else if (inp.parentElement && inp.parentElement.tagName.toLowerCase() === 'label') label = inp.parentElement.innerText.trim();
            else if (inp.parentElement) label = inp.parentElement.innerText.trim().slice(0, 30);
            
            const sel = inp.id ? '#' + inp.id : (inp.name ? `${tag}[name="${inp.name}"]` : `${tag}[type="${t}"]`);
            elements.push({
                type: "input",
                inputType: t,
                id: inp.id || '',
                label: label,
                value: inp.value || '',
                checked: inp.checked || false,
                selector: sel
            });
        });

        // Menu items
        taskArea.querySelectorAll("[role='menuitem'], .ui-menu-item-wrapper").forEach((m) => {
            const txt = m.innerText.trim();
            if (txt) {
                elements.push({
                    type: "menuitem",
                    text: txt,
                    selector: m.id ? '#' + m.id : `div[role="menuitem"]:has-text("${txt}")`
                });
            }
        });

        // Check if canvas exists with bounding box
        const canvases = [];
        taskArea.querySelectorAll("canvas").forEach((c) => {
            const r = c.getBoundingClientRect();
            canvases.push({
                width: Math.round(r.width),
                height: Math.round(r.height),
                center: [Math.round(r.x + r.width/2), Math.round(r.y + r.height/2)]
            });
        });

        return {
            textContent: textContent.slice(0, 300),
            elements: elements.slice(0, 25),
            canvases: canvases
        };
    }""")
    return info

def format_observation(info):
    lines = []
    if info.get("textContent"):
        lines.append(f"Page Text Context:\n{info['textContent']}")
        lines.append("")
        
    lines.append("Interactive Elements:")
    for el in info.get("elements", []):
        t = el["type"]
        if t == "button":
            lines.append(f"- Button: text='{el['text']}', selector=`{el['selector']}`")
        elif t == "color_box":
            lines.append(f"- Color Box: color='{el['color']}', selector=`{el['selector']}`")
        elif t == "email_thread":
            lines.append(f"- Email Thread: sender='{el['sender']}', subject='{el['subject']}', selector=`{el['selector']}`")
        elif t == "email_star":
            lines.append(f"- Email Star Icon: for_sender='{el['for_sender']}', selector=`{el['selector']}`")
        elif t == "email_trash":
            lines.append(f"- Email Trash Icon: for_sender='{el['for_sender']}', selector=`{el['selector']}`")
        elif t == "calendar_day":
            lines.append(f"- Calendar Day Link: day='{el['day']}', selector=`{el['selector']}`")
        elif t == "slider":
            lines.append(f"- Slider: current_value={el['value']}, selector=`{el['selector']}` (Use press(selector, 'ArrowRight') or 'ArrowLeft')")
        elif t == "select":
            opts = ", ".join([f"'{o}'" for o in el["options"][:8]])
            lines.append(f"- Dropdown Select: options=[{opts}], selector=`{el['selector']}`")
        elif t == "accordion":
            lines.append(f"- Accordion Header: text='{el['text']}', expanded={el['expanded']}, selector=`{el['selector']}`")
        elif t == "link":
            lines.append(f"- Link: text='{el['text']}', selector=`{el['selector']}`")
        elif t == "menuitem":
            lines.append(f"- Menu Item: text='{el['text']}', selector=`{el['selector']}`")
        elif t == "input":
            inp_t = el["inputType"]
            lbl = f", label='{el['label']}'" if el["label"] else ""
            if inp_t in ("radio", "checkbox"):
                lines.append(f"- Input ({inp_t}): id='{el['id']}'{lbl}, checked={el['checked']}, selector=`{el['selector']}`")
            else:
                lines.append(f"- Input ({inp_t}): id='{el['id']}'{lbl}, current_value='{el['value']}', selector=`{el['selector']}`")
                
    if info.get("canvases"):
        for c in info["canvases"]:
            lines.append(f"- Canvas Area: size={c['width']}x{c['height']}, center=({c['center'][0]}, {c['center'][1]}). Use click_coords(x, y) or drag_coords(x1, y1, x2, y2).")
            
    return "\n".join(lines)

def run_task_v2(page, task_name, idx, total, seed=None):
    url = f"http://127.0.0.1:8000/miniwob/{task_name}.html"
    try:
        page.goto(url, timeout=10000)
        page.wait_for_load_state("domcontentloaded", timeout=5000)
        if seed is not None:
            # Fix the episode's random draw so every model gets the same task instance.
            page.evaluate("(s) => Math.seedrandom(s)", str(seed))
        page.evaluate("() => { if (typeof core !== 'undefined') core.startEpisodeReal(); }")
        time.sleep(0.3)
    except Exception as e:
        print(f"Error loading {task_name}: {e}")
        return {"task": task_name, "goal": "Error loading", "steps": 0, "reward": 0.0, "passed": False, "history": []}

    goal = ""
    try:
        goal = page.evaluate("() => typeof core !== 'undefined' && core.getUtterance ? core.getUtterance() : document.querySelector('#query').innerText.trim()")
    except Exception:
        goal = task_name

    print(f"\n" + "="*60)
    print(f"[{idx}/{total}] 🎯 Task: {task_name}")
    print(f"📋 Goal: {goal}")
    print("="*60)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    max_steps = 10
    task_history = []
    step_log = []
    t_start = time.time()
    
    for step in range(1, max_steps + 1):
        obs = extract_dom_v2(page)
        obs_text = format_observation(obs)
        
        user_prompt = f"Goal: {goal}\n\n{obs_text}\n\nWhat is your next action?"
        messages.append({"role": "user", "content": user_prompt})
        
        print(f"  [Step {step}] 🤖 Querying model (RPS rate-limited)...")
        try:
            reasoning, content, latency = query_model(messages)
            print(f"  [Step {step}] ⏱ Latency: {latency:.2f}s | RPS status: OK")
            step_log.append({"step": step, "latency_s": round(latency, 3), "usage": dict(last_usage),
                             "reasoning_chars": len(reasoning or ""), "content_chars": len(content or ""),
                             "reasoning": reasoning or "", "content": content or "",
                             "t_start": last_stream.get("t_start"), "timeline": last_stream.get("events")})
        except Exception as e:
            print(f"  [Step {step}] ❌ API Query Error: {e}")
            break
            
        # If the episode timed out while the model was thinking, MiniWoB has put
        # its START cover over the page, and acting would only wait out Playwright
        # timeouts. Stop here so the recorded time ends with the episode.
        if page.evaluate("() => typeof WOB_DONE_GLOBAL !== 'undefined' && WOB_DONE_GLOBAL"):
            reward = page.evaluate("() => typeof WOB_REWARD_GLOBAL !== 'undefined' ? WOB_REWARD_GLOBAL : 0")
            print(f"  🏁 Outcome: episode ended before the action (Reward: {reward:.4f}, Steps: {step})")
            return {
                "task": task_name,
                "goal": goal,
                "steps": step,
                "reward": reward,
                "passed": reward > 0,
                "history": task_history,
                "seed": seed,
                "elapsed_s": round(time.time() - t_start, 3),
                "step_log": step_log
            }

        action = parse_action(content, reasoning)
        if not action:
            print(f"  [Step {step}] ❌ Could not parse action")
            break
            
        print(f"  [Step {step}] ⚡ Action: {action}")
        task_history.append(action)
        execute_action(page, action)
            
        time.sleep(0.4)
        
        reward = page.evaluate("() => typeof WOB_REWARD_GLOBAL !== 'undefined' ? WOB_REWARD_GLOBAL : 0")
        done = page.evaluate("() => typeof WOB_DONE_GLOBAL !== 'undefined' ? WOB_DONE_GLOBAL : false")
        
        if done:
            status = "PASSED" if reward > 0 else "FAILED"
            print(f"  🏁 Outcome: {status} (Reward: {reward:.4f}, Steps: {step})")
            return {
                "task": task_name,
                "goal": goal,
                "steps": step,
                "reward": reward,
                "passed": reward > 0,
                "history": task_history,
                "seed": seed,
                "elapsed_s": round(time.time() - t_start, 3),
                "step_log": step_log
            }
            
        messages.append({"role": "assistant", "content": f"Action: {action}"})
            
    reward = page.evaluate("() => typeof WOB_REWARD_GLOBAL !== 'undefined' ? WOB_REWARD_GLOBAL : 0")
    status = "PASSED" if reward > 0 else "FAILED"
    print(f"  🏁 Outcome: {status} (Reward: {reward:.4f}, Steps: {max_steps})")
    return {
        "task": task_name,
        "goal": goal,
        "steps": max_steps,
        "reward": reward,
        "passed": reward > 0,
        "history": task_history,
        "seed": seed,
        "elapsed_s": round(time.time() - t_start, 3),
        "step_log": step_log
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, choices=[1, 2, 3], required=True, help="Batch 1, 2, or 3")
    parser.add_argument("--seed", type=int, help="Seed every episode so runs see identical task instances")
    parser.add_argument("--video-dir", help="Record a Playwright video of the run into this directory")
    args = parser.parse_args()
    
    already_done = [
        "click-button", "enter-text", "login-user", "enter-password",
        "click-link", "click-dialog", "click-tab", "click-option",
        "click-checkboxes", "click-collapsible"
    ]
    
    all_files = sorted(glob.glob(HERE + "/miniwob-plusplus/miniwob/html/miniwob/*.html"))
    all_tasks = [os.path.basename(f)[:-5] for f in all_files]
    remaining = [t for t in all_tasks if t not in already_done]
    
    if args.batch == 1:
        batch_tasks = remaining[:50]
    elif args.batch == 2:
        batch_tasks = remaining[50:100]
    elif args.batch == 3:
        batch_tasks = remaining[100:]
        
    batch_num = args.batch
    print("="*60)
    print(f"🌐 RUNNING UPGRADED MINIWOB++ V2 BATCH {batch_num} ({len(batch_tasks)} TASKS)")
    print(f"Target API: {API_URL}")
    print(f"Rate Limiter: MIN_INTERVAL = 1.0s (Strictly RPS < 2)")
    print("="*60)
    
    task_results = []
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    output_file = HERE + f"/results/miniwob_v2_results_batch_{batch_num}.json"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(record_video_dir=args.video_dir) if args.video_dir else browser.new_context()
        page = context.new_page()
        
        for idx, task in enumerate(batch_tasks, 1):
            res = run_task_v2(page, task, idx, len(batch_tasks), seed=args.seed)
            task_results.append(res)
            with open(output_file, "w") as f:
                json.dump({
                    "batch": batch_num,
                    "count": len(task_results),
                    "results": task_results
                }, f, indent=2)
            
        context.close()
        browser.close()
        
    rate_stats = rate_limiter.get_stats()
    passed_count = sum(1 for r in task_results if r["passed"])
    acc = (passed_count / len(task_results)) * 100 if task_results else 0.0
    
    print("\n" + "="*70)
    print(f"🏆 UPGRADED BATCH {batch_num} RESULTS SUMMARY")
    print("="*70)
    print(f"🎯 Total Passed: {passed_count}/{len(task_results)} ({acc:.1f}%)")
    print(f"📊 Rate Limiting Stats:")
    print(f"   • Total API Requests: {rate_stats['total_calls']}")
    print(f"   • Peak Observed RPS:  {rate_stats['peak_rps']:.2f} (Strictly < 2.0 RPS)")
    print(f"   • Average RPS:        {rate_stats['avg_rps']:.2f}")
    print("="*70)

if __name__ == "__main__":
    main()
