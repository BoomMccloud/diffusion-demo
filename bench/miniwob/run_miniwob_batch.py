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

API_URL = "http://43.107.54.53:31003/v1/chat/completions"

SYSTEM_PROMPT = """You are an autonomous web agent solving MiniWoB++ benchmark tasks.
You receive:
1. The Task Goal.
2. The interactive elements on the page with their current values, checked states, and CSS selectors.

Available Actions:
- click(selector): click an element by selector
- fill(selector, text): type text into an input or textarea
- select(selector, text): select an option from a dropdown (<select>) element

Guidelines:
1. Read the Goal carefully.
2. Look at what is already filled or selected on the page.
3. If the goal requires multiple inputs or checkboxes, do one action at a time.
4. Output your reasoning, then output exactly one action line:
Action: <action_call>

Examples:
Action: click("button:has-text('Submit')")
Action: fill("#password", "abcd")
Action: click("#ch0")
Action: select("#options", "Antarctica")
Action: click("button.ui-dialog-titlebar-close")
Action: click(".alink:has-text('word')")
Action: click("a:has-text('Tab #2')")
Action: click("h3:has-text('Section #12')")
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
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        latency = time.time() - t0
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
        # First try ast literal parse
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
    except Exception:
        pass
    
    # Fallback string parsing for unquoted or complex selectors
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
        elif action_str.startswith("select(") and action_str.endswith(")"):
            inner = action_str[len("select("):-1].strip()
            parts = inner.split(",", 1)
            sel = parts[0].strip(" '\"")
            val = parts[1].strip(" '\"")
            try:
                page.locator(sel).first.select_option(label=val, timeout=2500)
            except Exception:
                page.locator(sel).first.select_option(value=val, timeout=2500)
            return True
    except Exception as e:
        print(f"  [Execution warning for {action_str}: {e}]")
    return False

def extract_dom_summary(page):
    elements = page.evaluate("""() => {
        const results = [];
        const taskArea = document.querySelector('#area') || document.body;
        
        // 1. Buttons (any button on the page or dialog)
        document.querySelectorAll('button').forEach((b) => {
            const txt = b.innerText.trim();
            let sel = b.id ? '#' + b.id : '';
            if (!sel && b.className) {
                if (b.className.includes('ui-dialog-titlebar-close')) {
                    sel = 'button.ui-dialog-titlebar-close';
                } else {
                    const firstClass = b.className.trim().split(/\\s+/)[0];
                    if (firstClass) sel = `button.${firstClass}`;
                }
            }
            if (!sel) {
                sel = `button:has-text("${txt}")`;
            }
            results.push({
                type: 'button',
                id: b.id || '',
                text: txt,
                selector: sel
            });
        });

        // 2. Select dropdowns
        taskArea.querySelectorAll('select').forEach((s) => {
            const options = Array.from(s.options).map(o => o.text.trim());
            const sel = s.id ? '#' + s.id : (s.name ? `select[name="${s.name}"]` : 'select');
            results.push({
                type: 'select',
                id: s.id || '',
                selector: sel,
                options: options,
                current_value: s.value
            });
        });

        // 3. Headings / Collapsibles (h3)
        taskArea.querySelectorAll('h3, .ui-accordion-header').forEach((h) => {
            const txt = h.innerText.trim();
            const isExpanded = h.getAttribute('aria-expanded') === 'true' || h.classList.contains('ui-accordion-header-active');
            results.push({
                type: 'collapsible_header',
                text: txt,
                expanded: isExpanded,
                selector: `h3:has-text("${txt}")`
            });
        });

        // 4. Links and link-like spans
        taskArea.querySelectorAll('a, .alink, [role="link"]').forEach((a) => {
            const txt = a.innerText.trim();
            let sel = a.id ? '#' + a.id : '';
            if (!sel) {
                if (a.tagName.toLowerCase() === 'a') {
                    sel = `a:has-text("${txt}")`;
                } else {
                    sel = `.alink:has-text("${txt}")`;
                }
            }
            results.push({
                type: 'link',
                text: txt,
                selector: sel
            });
        });
        
        // 5. Inputs (text, password, radio, checkbox) & textareas
        taskArea.querySelectorAll('input, textarea').forEach((inp) => {
            let label = '';
            if (inp.labels && inp.labels[0]) {
                label = inp.labels[0].innerText.trim();
            } else if (inp.parentElement && inp.parentElement.tagName.toLowerCase() === 'label') {
                label = inp.parentElement.innerText.trim();
            } else if (inp.parentElement) {
                label = inp.parentElement.innerText.trim();
            }
            const isTextarea = inp.tagName.toLowerCase() === 'textarea';
            const inputType = isTextarea ? 'textarea' : (inp.type || 'text');
            const sel = inp.id ? '#' + inp.id : (inp.name ? `${inp.tagName.toLowerCase()}[name="${inp.name}"]` : `${inp.tagName.toLowerCase()}[type="${inputType}"]`);
            results.push({
                type: 'input',
                inputType: inputType,
                id: inp.id || '',
                value: inp.value || '',
                checked: inp.checked || false,
                label: label,
                selector: sel
            });
        });
        
        // 6. Check if canvas exists
        const canvases = taskArea.querySelectorAll('canvas');
        if (canvases.length > 0) {
            results.push({
                type: 'canvas',
                selector: 'canvas',
                count: canvases.length
            });
        }

        return results;
    }""")
    return elements

def format_elements(elements):
    elem_desc = []
    for el in elements:
        if el['type'] == 'button':
            elem_desc.append(f"- Button: text='{el['text']}', selector=`{el['selector']}`")
        elif el['type'] == 'select':
            opts = ", ".join([f"'{o}'" for o in el['options'][:8]])
            elem_desc.append(f"- Dropdown Select: options=[{opts}], selector=`{el['selector']}`")
        elif el['type'] == 'collapsible_header':
            exp = f", expanded={el['expanded']}" if 'expanded' in el else ""
            elem_desc.append(f"- Accordion / Header: text='{el['text']}'{exp}, selector=`{el['selector']}`")
        elif el['type'] == 'link':
            elem_desc.append(f"- Link: text='{el['text']}', selector=`{el['selector']}`")
        elif el['type'] == 'canvas':
            elem_desc.append(f"- Canvas (2D graphics / drawing element): selector=`canvas`")
        elif el['type'] == 'input':
            t = el['inputType']
            lbl = f", label='{el['label']}'" if el['label'] else ""
            if t in ('radio', 'checkbox'):
                chk = f", checked={el['checked']}"
                elem_desc.append(f"- Input ({t}): id='{el['id']}'{lbl}{chk}, selector=`{el['selector']}`")
            else:
                val = f", current_value='{el['value']}'"
                elem_desc.append(f"- Input ({t}): id='{el['id']}'{lbl}{val}, selector=`{el['selector']}`")
    return "\n".join(elem_desc)

def run_task(page, task_name, task_num, total_tasks):
    url = f"http://127.0.0.1:8000/miniwob/{task_name}.html"
    try:
        page.goto(url, timeout=10000)
        page.wait_for_load_state("domcontentloaded", timeout=5000)
        # Start episode
        page.evaluate("() => { if (typeof core !== 'undefined') core.startEpisodeReal(); }")
        time.sleep(0.3)
    except Exception as e:
        print(f"Error loading {task_name}: {e}")
        return {"task": task_name, "goal": "Error loading", "steps": 0, "reward": 0.0, "passed": False}

    goal = ""
    try:
        goal = page.locator('#query').inner_text(timeout=2000).strip()
    except Exception:
        goal = task_name

    print(f"\n" + "="*60)
    print(f"[{task_num}/{total_tasks}] 🎯 Task: {task_name}")
    print(f"📋 Goal: {goal}")
    print("="*60)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    max_steps = 6
    task_history = []
    for step in range(1, max_steps + 1):
        elements = extract_dom_summary(page)
        
        # If no actionable elements found, or only canvas
        actionable = [el for el in elements if el['type'] != 'canvas']
        if not actionable and any(el['type'] == 'canvas' for el in elements):
            print(f"  [Step {step}] ℹ️ Canvas-only task detected (requires coordinate interaction).")
            # Try a default click or conclude
            try:
                page.locator('canvas').first.click(timeout=1000)
            except Exception:
                pass
            break
            
        dom_text = format_elements(elements)
        user_prompt = f"Goal: {goal}\n\nCurrent Web Elements:\n{dom_text}\n\nWhat is your next action?"
        messages.append({"role": "user", "content": user_prompt})
        
        print(f"  [Step {step}] 🤖 Querying model (RPS rate-limited)...")
        try:
            reasoning, content, latency = query_model(messages)
            print(f"  [Step {step}] ⏱ Latency: {latency:.2f}s | RPS status: OK")
        except Exception as e:
            print(f"  [Step {step}] ❌ API Query Error: {e}")
            break
            
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
            print(f"  🏁 Task Outcome: {status} (Reward: {reward:.4f}, Steps: {step})")
            return {
                "task": task_name,
                "goal": goal,
                "steps": step,
                "reward": reward,
                "passed": reward > 0,
                "history": task_history
            }
            
        messages.append({"role": "assistant", "content": f"Action: {action}"})
            
    reward = page.evaluate("() => typeof WOB_REWARD_GLOBAL !== 'undefined' ? WOB_REWARD_GLOBAL : 0")
    status = "PASSED" if reward > 0 else "FAILED"
    print(f"  🏁 Task Outcome: {status} (Reward: {reward:.4f}, Steps: {max_steps})")
    return {
        "task": task_name,
        "goal": goal,
        "steps": max_steps,
        "reward": reward,
        "passed": reward > 0,
        "history": task_history
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, choices=[1, 2, 3], required=True, help="Batch number: 1, 2, or 3")
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
    print(f"🌐 RUNNING MINIWOB++ BATCH {batch_num} ({len(batch_tasks)} TASKS)")
    print(f"Target API: {API_URL}")
    print(f"Rate Limiter: MIN_INTERVAL = 1.0s (Target: RPS < 2)")
    print("="*60)
    
    task_results = []
    output_file = HERE + f"/results/miniwob_results_batch_{batch_num}.json"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        for idx, task in enumerate(batch_tasks, 1):
            res = run_task(page, task, idx, len(batch_tasks))
            task_results.append(res)
            # Incrementally write results
            with open(output_file, "w") as f:
                json.dump({
                    "batch": batch_num,
                    "count": len(task_results),
                    "results": task_results
                }, f, indent=2)
            
        browser.close()
        
    rate_stats = rate_limiter.get_stats()
    passed_count = sum(1 for r in task_results if r["passed"])
    acc = (passed_count / len(task_results)) * 100 if task_results else 0.0
    
    print("\n" + "="*70)
    print(f"🏆 BATCH {batch_num} RESULTS SUMMARY")
    print("="*70)
    print(f"🎯 Total Passed: {passed_count}/{len(task_results)} ({acc:.1f}%)")
    print(f"📊 Rate Limiting Stats:")
    print(f"   • Total API Requests: {rate_stats['total_calls']}")
    print(f"   • Peak Observed RPS:  {rate_stats['peak_rps']:.2f} (Strictly < 2.0 RPS)")
    print(f"   • Average RPS:        {rate_stats['avg_rps']:.2f}")
    print("="*70)

if __name__ == "__main__":
    main()
