import json
import urllib.request
import re
import time
import subprocess
import ast
import sys
from playwright.sync_api import sync_playwright

API_URL = "http://43.107.54.53:31003/v1/chat/completions"

SYSTEM_PROMPT = """You are an autonomous web agent solving MiniWoB++ benchmark tasks.
You receive:
1. The Task Goal.
2. The interactive elements on the page with their current values, checked states, and CSS selectors.

Available Actions:
- click(selector): click an element by selector
- fill(selector, text): type text into an input element

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
        
        # Calculate intervals
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
    call_start = rate_limiter.acquire()
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
            page.locator(sel).first.click()
            return True
        elif func_name == "fill":
            sel, val = args[0], str(args[1])
            page.locator(sel).first.fill(val)
            return True
    except Exception:
        pass
    
    # Fallback string parsing for unquoted or complex selectors
    try:
        if action_str.startswith("click(") and action_str.endswith(")"):
            inner = action_str[len("click("):-1].strip()
            if (inner.startswith('"') and inner.endswith('"')) or (inner.startswith("'") and inner.endswith("'")):
                inner = inner[1:-1]
            page.locator(inner).first.click()
            return True
        elif action_str.startswith("fill(") and action_str.endswith(")"):
            inner = action_str[len("fill("):-1].strip()
            # Split by first comma
            parts = inner.split(",", 1)
            sel = parts[0].strip(" '\"")
            val = parts[1].strip(" '\"")
            page.locator(sel).first.fill(val)
            return True
    except Exception as e:
        print(f"  [Execution error for {action_str}: {e}]")
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
                // e.g. ui-dialog-titlebar-close
                if (b.className.includes('ui-dialog-titlebar-close')) {
                    sel = 'button.ui-dialog-titlebar-close';
                } else {
                    const firstClass = b.className.trim().split(/\\s+/)[0];
                    sel = `button.${firstClass}`;
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

        // 2. Headings / Collapsibles (h3)
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

        // 3. Links and link-like spans
        taskArea.querySelectorAll('a, .alink').forEach((a) => {
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
        
        // 4. Inputs (text, password, radio, checkbox)
        taskArea.querySelectorAll('input').forEach((inp) => {
            let label = '';
            if (inp.labels && inp.labels[0]) {
                label = inp.labels[0].innerText.trim();
            } else if (inp.parentElement && inp.parentElement.tagName.toLowerCase() === 'label') {
                label = inp.parentElement.innerText.trim();
            } else if (inp.parentElement) {
                label = inp.parentElement.innerText.trim();
            }
            const sel = inp.id ? '#' + inp.id : (inp.name ? `input[name="${inp.name}"]` : `input[type="${inp.type}"]`);
            results.push({
                type: 'input',
                inputType: inp.type,
                id: inp.id || '',
                value: inp.value || '',
                checked: inp.checked,
                label: label,
                selector: sel
            });
        });
        
        return results;
    }""")
    return elements

def format_elements(elements):
    elem_desc = []
    for el in elements:
        if el['type'] == 'button':
            elem_desc.append(f"- Button: text='{el['text']}', selector=`{el['selector']}`")
        elif el['type'] == 'collapsible_header':
            exp = f", expanded={el['expanded']}" if 'expanded' in el else ""
            elem_desc.append(f"- Accordion / Header: text='{el['text']}'{exp}, selector=`{el['selector']}`")
        elif el['type'] == 'link':
            elem_desc.append(f"- Link: text='{el['text']}', selector=`{el['selector']}`")
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
    page.goto(url)
    
    # Start episode
    page.evaluate("() => core.startEpisodeReal()")
    page.wait_for_function("() => typeof WOB_TASK_READY !== 'undefined' && WOB_TASK_READY")
    
    goal = page.locator('#query').inner_text().strip()
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
        dom_text = format_elements(elements)
        
        user_prompt = f"Goal: {goal}\n\nCurrent Web Elements:\n{dom_text}\n\nWhat is your next action?"
        messages.append({"role": "user", "content": user_prompt})
        
        print(f"\n  [Step {step}] 🤖 Querying model (RPS rate-limited)...")
        reasoning, content, latency = query_model(messages)
        print(f"  [Step {step}] ⏱ Latency: {latency:.2f}s | RPS status: OK")
        
        first_reasoning = reasoning.strip().splitlines()[0] if reasoning else ""
        if first_reasoning:
            print(f"  [Step {step}] 💭 Reason: {first_reasoning[:90]}...")
            
        action = parse_action(content, reasoning)
        if not action:
            print(f"  [Step {step}] ❌ Could not parse action from: {content}")
            break
            
        print(f"  [Step {step}] ⚡ Action: {action}")
        task_history.append(action)
        execute_action(page, action)
            
        time.sleep(0.4)
        
        reward = page.evaluate("() => WOB_REWARD_GLOBAL")
        done = page.evaluate("() => WOB_DONE_GLOBAL")
        
        if done:
            status = "PASSED" if reward > 0 else "FAILED"
            print(f"\n  🏁 Task Outcome: {status} (Reward: {reward:.4f}, Steps: {step})")
            return {
                "task": task_name,
                "goal": goal,
                "steps": step,
                "reward": reward,
                "passed": reward > 0,
                "history": task_history
            }
            
        messages.append({"role": "assistant", "content": f"Action: {action}"})
            
    reward = page.evaluate("() => WOB_REWARD_GLOBAL")
    return {
        "task": task_name,
        "goal": goal,
        "steps": max_steps,
        "reward": reward,
        "passed": reward > 0,
        "history": task_history
    }

def main():
    test_suite = [
        "click-button",
        "enter-text",
        "login-user",
        "enter-password",
        "click-link",
        "click-dialog",
        "click-tab",
        "click-option",
        "click-checkboxes",
        "click-collapsible"
    ]
    
    print("="*60)
    print("🌐 STARTING MINIWOB++ 10-TASK BENCHMARK SUITE")
    print(f"Target API: {API_URL}")
    print(f"Rate Limiter: MIN_INTERVAL = 1.0s (Target: RPS < 2)")
    print(f"Tasks: {len(test_suite)}")
    print("="*60)
    
    task_results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        for idx, task in enumerate(test_suite, 1):
            res = run_task(page, task, idx, len(test_suite))
            task_results.append(res)
            
        browser.close()
        
    rate_stats = rate_limiter.get_stats()
    
    print("\n" + "="*70)
    print("🏆 FINAL BENCHMARK RESULTS SUMMARY")
    print("="*70)
    print(f"{'#':<3} {'Task':<20} {'Status':<10} {'Reward':<10} {'Steps':<6} {'Goal'}")
    print("-" * 70)
    passed_count = 0
    for i, r in enumerate(task_results, 1):
        status_str = "PASS ✅" if r["passed"] else "FAIL ❌"
        if r["passed"]:
            passed_count += 1
        print(f"{i:<3} {r['task']:<20} {status_str:<10} {r['reward']:<10.4f} {r['steps']:<6} {r['goal'][:35]}")
    print("-" * 70)
    acc = (passed_count / len(task_results)) * 100
    print(f"🎯 Total Success Rate: {passed_count}/{len(task_results)} ({acc:.1f}%)")
    print(f"📊 Rate Limiting Stats:")
    print(f"   • Total API Requests: {rate_stats['total_calls']}")
    print(f"   • Peak Observed RPS:  {rate_stats['peak_rps']:.2f} (Strictly < 2.0 RPS)")
    print(f"   • Average RPS:        {rate_stats['avg_rps']:.2f}")
    print("="*70)

if __name__ == "__main__":
    main()
