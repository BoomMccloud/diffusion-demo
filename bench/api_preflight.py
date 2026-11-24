"""Exercise an OpenAI-compatible API with a small tool round trip."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def route():
    names = ("BENCH_API_BASE_URL", "BENCH_API_KEY", "BENCH_API_MODEL")
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise ValueError(f"Set {', '.join(missing)} before running the benchmark.")
    base_url, key, model = (os.environ[name] for name in names)
    base_url = base_url.rstrip("/").removesuffix("/chat/completions")
    if not base_url.startswith(("https://", "http://")):
        raise ValueError("BENCH_API_BASE_URL must be an HTTP(S) API base URL.")
    return base_url, key, model


def probe(base_url, key, model):
    def request(messages, **options):
        payload = {"model": model, "messages": messages, **options}
        req = Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        return urlopen(req, timeout=90)

    function = {
        "name": "read_marker",
        "description": "Return the marker for this benchmark setup check.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    }
    tools = [{"type": "function", "function": function}]
    messages = [{"role": "user", "content": "Call read_marker, then reply with only its result."}]
    with request(messages, tools=tools, tool_choice="auto") as response:
        message = json.load(response)["choices"][0]["message"]
    calls = message.get("tool_calls") or []
    if len(calls) != 1 or calls[0]["function"]["name"] != function["name"]:
        raise ValueError("The model did not return the expected tool call.")
    marker = "BENCH-APRICOT"
    messages.extend((
        {name: value for name, value in message.items()
         if name in {"role", "content", "tool_calls", "reasoning_content", "reasoning_details", "reasoning"}},
        {"role": "tool", "tool_call_id": calls[0]["id"], "content": marker},
    ))
    content = []
    with request(messages, tools=tools, stream=True) as response:
        for line in response:
            if not line.startswith(b"data:"):
                continue
            data = line[5:].strip()
            if data == b"[DONE]":
                break
            for choice in json.loads(data).get("choices", []):
                content.append(choice.get("delta", {}).get("content") or "")
    if "".join(content).strip() != marker:
        raise ValueError("The streamed response did not match the tool result.")


if __name__ == "__main__":
    try:
        probe(*route())
    except HTTPError as exc:
        raise SystemExit(f"Benchmark API preflight failed: HTTP {exc.code}.") from None
    except (URLError, TimeoutError):
        raise SystemExit("Benchmark API preflight could not reach the endpoint.") from None
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        raise SystemExit("Benchmark API preflight received an unexpected response.") from None
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print("API preflight passed: tool call and streamed tool result.")
