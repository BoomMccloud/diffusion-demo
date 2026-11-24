"""Sequential local Clover task panel. Run inside a resource-limited container."""
import ast
import collections
import datetime
import json
import pathlib
import re
import time
import urllib.request


TASKS = [
    dict(id="arithmetic", kind="json", prompt='Compute 137*249 and 9991-6789. Return only a JSON object with keys product and difference.', expected={"product":34113,"difference":3202}),
    dict(id="inventory_math", kind="json", prompt='A warehouse starts with 840 units, receives 175, ships 368, and scraps 27. Each remaining unit is worth 12 dollars. Return only JSON with keys units and value.', expected={"units":620,"value":7440}),
    dict(id="extract_orders", kind="json", prompt='Extract paid orders only, in source order. Text: Order A17: customer Mira, $42, paid. Order B09: customer Leon, $18, cancelled. Order C22: customer Ana, $75, paid. Return only a JSON array of objects with keys id and amount.', expected=[{"id":"A17","amount":42},{"id":"C22","amount":75}]),
    dict(id="extract_events", kind="json", prompt='Extract dates and events in chronological order: On 2026-05-12 the launch was postponed. A prototype passed review on 2026-04-03. On 2026-05-20 the product shipped. Return only a JSON array with keys date and event. Use event values review, postponed, shipped.', expected=[{"date":"2026-04-03","event":"review"},{"date":"2026-05-12","event":"postponed"},{"date":"2026-05-20","event":"shipped"}]),
    dict(id="edit_function",kind="code",prompt='Edit this Python function: rename add_tax to price_with_tax; change rate default from 0.05 to 0.08; round the result to two decimal places. Return only the updated function.\ndef add_tax(price, rate=0.05):\n    return price * (1 + rate)',expected='def price_with_tax(price, rate=0.08):\n    return round(price * (1 + rate), 2)'),
    dict(id="edit_validation",kind="code",prompt='Apply only these edits to the Python function: rename normalize to normalize_name; return an empty string if text is None; keep the existing behavior otherwise. Return only the updated function.\ndef normalize(text):\n    return text.strip().lower()',expected='def normalize_name(text):\n    if text is None:\n        return ""\n    return text.strip().lower()'),
    dict(id="explain_index",kind="prose",prompt='Explain database indexes to a junior engineer in about 1200 words. Develop distinct sections on B-trees, selectivity, composite indexes, write overhead, query plans, and a worked example. Avoid repeating paragraphs.'),
    dict(id="explain_planets",kind="prose",prompt='Explain how astronomers detect exoplanets in about 1200 words. Cover transits, radial velocity, direct imaging, false positives, selection bias, and how methods complement each other. Include a quantitative example. Avoid repeating sections.'),
    dict(id="fiction_station",kind="prose",prompt='Write a complete original story of about 1200 words about a weather-station technician and an island ferry captain facing contradictory storm forecasts. Include distinct scenes, dialogue, a concrete clue, a difficult decision, and a resolved ending. Avoid repeated scenes.'),
    dict(id="fiction_archive",kind="prose",prompt='Write a complete original story of about 1200 words about two estranged siblings cataloguing a family archive. An unsigned letter changes their understanding of an old dispute. Use distinct voices, a surprising but fair revelation, and a resolved ending. Avoid repeated dialogue.'),
    dict(id="tool_weather",kind="json",prompt='Select the function call needed to answer: What is the weather in Taipei? Available functions: get_weather(city: string), search_files(query: string). Do not answer the weather question. Return only JSON with keys name and arguments.',expected={"name":"get_weather","arguments":{"city":"Taipei"}}),
    dict(id="tool_result",kind="json",prompt='A tool returned {"order_id":"A17","status":"shipped","tracking":"ZX42","delivery_date":"2026-11-23"}. The user asks for status and tracking only. Return only JSON with keys status and tracking; omit other fields.',expected={"status":"shipped","tracking":"ZX42"}),
]


def unfence(text):
    text=text.strip()
    if text.startswith("```"):
        return "\n".join(text.splitlines()[1:-1]).strip()
    return text


def repetition(text):
    words=re.findall(r"[A-Za-z0-9]+",text.lower())
    counts=collections.Counter(tuple(words[i:i+12]) for i in range(max(0,len(words)-11)))
    return dict(words=len(words), repeated_12word_pct=round(100*sum(n-1 for n in counts.values())/max(1,len(words)-11),3), max_count=max(counts.values(),default=0))


def assess(task, result):
    content=result["content"]
    passed=None
    if task["kind"]=="json":
        try: passed=json.loads(unfence(content))==task["expected"]
        except (ValueError,TypeError): passed=False
    elif task["kind"]=="code":
        try: passed=ast.dump(ast.parse(unfence(content)))==ast.dump(ast.parse(task["expected"]))
        except (SyntaxError,ValueError): passed=False
    return dict(task_check=passed, reasoning=repetition(result["reasoning"]), answer=repetition(content))


def main():
    out=pathlib.Path('/work/task-panel-20261120'); out.mkdir(exist_ok=True)
    settings=dict(temperature=0, seed=42,max_tokens=65536,context=131072,cache_prompt=False)
    (out/'manifest.json').write_text(json.dumps(dict(tasks=TASKS,settings=settings),indent=2))
    for index, task in enumerate(TASKS):
        for thinking in [False,True]:
            modes=['self','ar'] if (index+thinking)%2==0 else ['ar','self']
            for mode in modes:
                trial=f'{index:02d}-{task["id"]}-think{int(thinking)}-{mode}'
                target=out/(trial+'.json')
                if target.exists(): continue
                print(json.dumps(dict(started=trial)),flush=True)
                body=dict(model='clover',messages=[dict(role='user',content=task['prompt'])],temperature=0,seed=42,max_tokens=65536,cache_prompt=False,stream=True,stream_options=dict(include_usage=True),chat_template_kwargs=dict(enable_thinking=thinking))
                request=urllib.request.Request(f'http://127.0.0.1:{18082 if mode=="self" else 18083}/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
                start=time.monotonic(); last=start; chunks=0; content=[]; reasoning=[]; finish=None; final=None; error=None
                try:
                    with urllib.request.urlopen(request,timeout=3600) as response:
                        for line in response:
                            if not line.startswith(b'data: '): continue
                            payload=line[6:].strip()
                            if payload==b'[DONE]': break
                            obj=json.loads(payload); choices=obj.get('choices') or []
                            if choices:
                                delta=choices[0].get('delta',{}); content.append(delta.get('content') or ''); reasoning.append(delta.get('reasoning_content') or delta.get('reasoning') or ''); chunks+=1
                                if choices[0].get('finish_reason'): finish=choices[0]['finish_reason']
                            if obj.get('usage') is not None: final=obj
                            if time.monotonic()-last>=30:
                                print(json.dumps(dict(progress=trial,elapsed_s=round(time.monotonic()-start,1),chunks=chunks)),flush=True); last=time.monotonic()
                except Exception as exc: error=repr(exc)
                result=dict(trial=trial,task=task['id'],kind=task['kind'],mode=mode,thinking=thinking,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_s=time.monotonic()-start,finish_reason=finish,final=final,error=error,content=''.join(content),reasoning=''.join(reasoning))
                result['assessment']=assess(task,result)
                target.write_text(json.dumps(result,indent=2))
                summary={k:v for k,v in result.items() if k not in ['content','reasoning','final']}; summary['usage']=(final or {}).get('usage'); summary['timings']=(final or {}).get('timings')
                with (out/'queue.jsonl').open('a') as file: file.write(json.dumps(summary)+'\n')
                print(json.dumps(dict(done=trial,**summary)),flush=True)
                if error or final is None: raise RuntimeError(f'{trial}: infrastructure or incomplete stream, inspect saved result')


if __name__=='__main__': main()
