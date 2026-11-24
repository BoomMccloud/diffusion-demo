"""Probe OpenRouter tool calling with synthetic Office-style data."""
import argparse
import json
import shlex
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MODELS = ("deepseek/deepseek-v4.1-flash-1017", "z-ai/glm-5.3-flash")
TOOL = {
    "type": "function",
    "function": {
        "name": "read_weekly_total",
        "description": "Read the ticket total from a synthetic weekly workbook.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
}
EXPECTED = "4826"


def probe(key, model):
    messages = [{"role": "user", "content":
                 "Call read_weekly_total, then reply with only the number it returns."}]
    result = {"requested_model": model, "turns": []}

    def request(stream=False):
        body = {
            "model": model, "messages": messages, "tools": [TOOL],
            "temperature": 0, "max_tokens": 1024, "stream": stream,
            "reasoning": {"enabled": True},
            "provider": {"require_parameters": True},
        }
        req = Request("https://openrouter.ai/api/v1/chat/completions",
                      data=json.dumps(body).encode(),
                      headers={"Authorization": f"Bearer {key}",
                               "Content-Type": "application/json"})
        started = time.monotonic()
        with urlopen(req, timeout=45) as response:
            turn = {"http": response.status, "stream": stream}
            result["turns"].append(turn)
            if stream:
                fragments = []
                done = False
                for raw in response:
                    if not raw.startswith(b"data: "):
                        continue
                    data = raw[6:].strip()
                    if data == b"[DONE]":
                        done = True
                        break
                    event = json.loads(data)
                    turn.update({name: event[name] for name in ("model", "provider", "usage")
                                 if event.get(name) is not None})
                    if event.get("error"):
                        raise ValueError("OpenRouter returned an in-stream error")
                    for choice in event.get("choices", []):
                        fragments.append(choice.get("delta", {}).get("content") or "")
                        if choice.get("finish_reason"):
                            turn["finish_reason"] = choice["finish_reason"]
                if not done:
                    raise ValueError("OpenRouter stream ended before [DONE]")
                message = {"content": "".join(fragments)}
            else:
                payload = json.load(response)
                if payload.get("error"):
                    raise ValueError("OpenRouter returned an error in the response")
                turn.update({name: payload.get(name) for name in ("model", "provider", "usage")})
                choice = payload["choices"][0]
                turn["finish_reason"] = choice["finish_reason"]
                message = choice["message"]
            turn["seconds"] = round(time.monotonic() - started, 3)
        return message

    try:
        assistant = request()
        calls = assistant.get("tool_calls") or []
        if len(calls) != 1 or calls[0]["function"]["name"] != "read_weekly_total":
            raise ValueError("Expected one read_weekly_total tool call")
        call = calls[0]
        if json.loads(call["function"]["arguments"]) != {}:
            raise ValueError("Expected empty tool arguments")
        result["reasoning_details_count"] = len(assistant.get("reasoning_details") or [])
        messages.extend([
            {name: assistant[name] for name in ("role", "content", "tool_calls",
                                                "reasoning", "reasoning_details")
             if name in assistant},
            {"role": "tool", "tool_call_id": call["id"], "content": EXPECTED},
        ])
        if (request(stream=True)["content"] or "").strip() != EXPECTED:
            raise ValueError("Expected the streamed final answer to match the tool result")
        result["passed"] = True
    except HTTPError as exc:
        result["error"] = f"HTTP {exc.code}"
        try:
            error = json.load(exc).get("error", {})
            result["error_message"] = str(error.get("message", ""))[:500].replace(key, "[redacted]")
        except (ValueError, AttributeError):
            pass
    except URLError as exc:
        result["error"] = str(exc.reason).replace(key, "[redacted]")
    except (ValueError, KeyError, IndexError, TimeoutError) as exc:
        result["error"] = str(exc).replace(key, "[redacted]")
    result.setdefault("passed", False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("env_file", type=Path)
    args = parser.parse_args()
    for line in args.env_file.read_text().splitlines():
        name, separator, value = line.strip().removeprefix("export ").partition("=")
        if separator and name.strip() == "OPENROUTER_API_KEY":
            values = shlex.split(value, comments=True)
            if len(values) == 1:
                key = values[0]
                break
    else:
        parser.error("OPENROUTER_API_KEY is missing or invalid")
    results = [probe(key, model) for model in MODELS]
    print(json.dumps(results, indent=2))
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
