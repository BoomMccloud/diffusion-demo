import json
import urllib.request
import re
import time
import subprocess
import ast
from playwright.sync_api import sync_playwright
import os

HERE = os.path.dirname(os.path.abspath(__file__))

API_URL = "http://43.107.54.53:31003/v1/chat/completions"

SYSTEM_PROMPT = """You are an autonomous web agent solving MiniWoB++ benchmark tasks.
You receive:
1. The Task Goal.
2. The interactive elements on the page with their current values and CSS selectors.

Available Actions:
- click(selector): click an element by selector
- fill(selector, text): type text into an input element

Guidelines:
1. Read the Goal carefully.
2. Look at what is already filled or selected on the page.
3. Output your reasoning, then output exactly one action line:
Action: <action_call>

Examples:
Action: click("button:has-text('Submit')")
Action: fill("#username", "alice")
"""

def query_model(messages):
    payload = {
        "messages": messages,
        "max_tokens": 512,
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
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        msg = res["choices"][0]["message"]
        return msg.get("reasoning_content", ""), msg.get("content", "")

def parse_action(content):
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("Action:"):
            return line[len("Action:"):].strip()
    m = re.search(r"Action:\s*([a-zA-Z_]+\(.*?\))\s*$", content, re.MULTILINE)
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
            page.locator(sel).first.click()
            return True
        elif func_name == "fill":
            sel, val = args[0], str(args[1])
            page.locator(sel).first.fill(val)
            return True
    except Exception as e:
        print(f"Error executing parsed action {action_str}: {e}")
        if action_str.startswith("click("):
            sel = re.search(r'click\((.*)\)', action_str).group(1).strip(" '\"")
            page.locator(sel).first.click()
            return True
        elif action_str.startswith("fill("):
            m = re.search(r'fill\((.*),\s*(.*)\)', action_str)
            sel = m.group(1).strip(" '\"")
            val = m.group(2).strip(" '\"")
            page.locator(sel).first.fill(val)
            return True
    return False

def extract_dom_summary(page):
    elements = page.evaluate("""() => {
        const results = [];
        const taskArea = document.querySelector('#area') || document.body;
        
        // Find buttons
        taskArea.querySelectorAll('button').forEach((b) => {
            const txt = b.innerText.trim();
            const sel = b.id ? '#' + b.id : `button:has-text("${txt}")`;
            results.push({
                type: 'button',
                id: b.id || '',
                text: txt,
                selector: sel
            });
        });
        
        // Find inputs
        taskArea.querySelectorAll('input').forEach((inp) => {
            const label = inp.labels && inp.labels[0] ? inp.labels[0].innerText.trim() : '';
            const sel = inp.id ? '#' + inp.id : (inp.name ? `input[name="${inp.name}"]` : `input[type="${inp.type}"]`);
            results.push({
                type: 'input',
                inputType: inp.type,
                id: inp.id || '',
                value: inp.value || '',
                label: label,
                selector: sel
            });
        });
        
        return results;
    }""")
    return elements

def run_task(page, task_name):
    url = f"http://127.0.0.1:8000/miniwob/{task_name}.html"
    page.goto(url)
    
    # Start episode
    page.evaluate("() => core.startEpisodeReal()")
    page.wait_for_function("() => typeof WOB_TASK_READY !== 'undefined' && WOB_TASK_READY")
    
    goal = page.locator('#query').inner_text().strip()
    print(f"\n" + "="*50)
    print(f"🎯 MiniWoB Task: {task_name}")
    print(f"📋 Goal: {goal}")
    print("="*50)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    max_steps = 4
    for step in range(1, max_steps + 1):
        elements = extract_dom_summary(page)
        elem_desc = []
        for el in elements:
            if el['type'] == 'button':
                elem_desc.append(f"- Button: text='{el['text']}', selector=`{el['selector']}`")
            elif el['type'] == 'input':
                lbl = f", label='{el['label']}'" if el['label'] else ""
                val = f", current_value='{el['value']}'" if el['value'] else ", current_value=''"
                elem_desc.append(f"- Input ({el['inputType']}): id='{el['id']}'{lbl}{val}, selector=`{el['selector']}`")
                
        user_prompt = f"Goal: {goal}\n\nCurrent Web Elements:\n" + "\n".join(elem_desc) + "\n\nWhat is your next action?"
        messages.append({"role": "user", "content": user_prompt})
        
        print(f"\n🤖 Step {step} | Querying Model...")
        reasoning, content = query_model(messages)
        if reasoning:
            print(f"💭 Reasoning:\n{reasoning.strip()}")
        print(f"💬 Output:\n{content.strip()}")
        
        action = parse_action(content)
        if not action:
            print("❌ Could not parse action!")
            break
            
        print(f"⚡ Executing Action: {action}")
        execute_action(page, action)
            
        time.sleep(0.5)
        
        reward = page.evaluate("() => WOB_REWARD_GLOBAL")
        done = page.evaluate("() => WOB_DONE_GLOBAL")
        
        if done:
            status = "PASSED" if reward > 0 else "FAILED"
            print(f"\n🏁 Task Finished: {status} (Reward: {reward:.3f})")
            return reward > 0
            
        messages.append({"role": "assistant", "content": f"Action: {action}"})
            
    reward = page.evaluate("() => WOB_REWARD_GLOBAL")
    return reward > 0

def main():
    print("🚀 Starting Local MiniWoB++ HTTP Server...")
    server = subprocess.Popen([
        "python3", "-m", "http.server", "8000",
        "--directory", HERE + "/miniwob-plusplus/miniwob/html"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    
    test_suite = [
        "click-button",
        "enter-text",
        "login-user"
    ]
    
    results = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        for task in test_suite:
            passed = run_task(page, task)
            results[task] = "PASSED (1.0)" if passed else "FAILED (0.0)"
            
        browser.close()
        
    server.terminate()
    
    print("\n" + "="*50)
    print("🏆 MINIWOB++ BENCHMARK RESULTS")
    print("="*50)
    for task, res in results.items():
        print(f"  • {task:<15}: {res}")
    print("="*50)

if __name__ == "__main__":
    main()
