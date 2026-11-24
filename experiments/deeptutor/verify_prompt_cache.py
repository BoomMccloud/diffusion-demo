"""Run serial, matched prompt-cache probes through the two Spark SSH tunnels."""
import argparse
import json
import urllib.request

source = "\n".join(f"Lesson {i}: count the blue circles." for i in range(700))
question = "Reply with just the number of sides of a triangle."
messages = [{"role": "system", "content": source}, {"role": "user", "content": question}]
parser = argparse.ArgumentParser()
parser.add_argument("--source-in-user", action="store_true")
args = parser.parse_args()
if args.source_in_user:
    messages = [{"role": "system", "content": "Read the notes."}, {"role": "user", "content": source + "\n" + question}]
common = dict(model="clover", temperature=0, max_tokens=1, chat_template_kwargs={"enable_thinking": False})
history_prefix = source + "\n" if args.source_in_user else ""
for mode, port in [("AR", 18183), ("self", 18182)]:
    for label, history, cache in [
        ("cold control", messages, False),
        ("exact replay", messages, True),
        ("exact replay again", messages, True),
        ("changed user question", [messages[0], {"role": "user", "content": history_prefix + "How many sides on a square?"}], True),
        ("cold control again", messages, False),
    ]:
        body = dict(common, messages=history, cache_prompt=cache)
        req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                     data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as response:
            answer = json.load(response)
        t = answer["timings"]
        print(json.dumps(dict(mode=mode, case=label, total=answer["usage"]["prompt_tokens"],
                              cached=t["cache_n"], evaluated=t["prompt_n"], prefill_ms=t["prompt_ms"])), flush=True)
