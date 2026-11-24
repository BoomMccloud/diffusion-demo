"""Model endpoints. Both run with thinking off through the OpenAI-compatible chat API."""
import hashlib, json, os, urllib.request

from openai import AsyncOpenAI

ARMS = {
    "dllm": {
        "model": "qwen36-iter22000-blk16-arverify-best",
        "base": lambda: os.environ["DIFFUSION_BASE_URL"].removesuffix("/chat/completions"),
        "key": lambda: "none",
        "extra": {"chat_template_kwargs": {"enable_thinking": False}},
    },
    "qwen": {
        "model": "qwen/qwen3.6-35b-a3b",
        "base": lambda: "https://openrouter.ai/api/v1",
        "key": lambda: os.environ["OPENROUTER_API_KEY"],
        "extra": {"reasoning": {"enabled": False}},
    },
}


def client(arm):
    a = ARMS[arm]
    return AsyncOpenAI(base_url=a["base"](), api_key=a["key"](), timeout=600, max_retries=2)


def fingerprint():
    """Identifies what was served: the dLLM's launch config and weights path, hashed."""
    out = {arm: {"model": a["model"]} for arm, a in ARMS.items()}
    try:
        base = os.environ["DIFFUSION_BASE_URL"].removesuffix("/chat/completions").removesuffix("/v1")
        info = json.load(urllib.request.urlopen(f"{base}/get_server_info", timeout=30))
        out["dllm"]["model_path"] = info.get("model_path")
        # internal_states changes on every call, so it's left out of the hash.
        stable = {k: v for k, v in info.items() if k != "internal_states"}
        out["dllm"]["server_config_sha256"] = hashlib.sha256(
            json.dumps(stable, sort_keys=True, default=str).encode()).hexdigest()
        out["dllm"]["speculative_algorithm"] = info.get("speculative_algorithm")
        out["dllm"]["dllm_block_size"] = info.get("dllm_block_size")
    except Exception as e:
        out["dllm"]["fingerprint_error"] = repr(e)[:200]
    return out
