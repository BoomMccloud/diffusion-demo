"""Run WebArena through AgentLab's GenericAgent against the hosted diffusion model.

Runs inside the webarena-agent container on diffuspace (see run.sh). The agent
uses AgentLab's GPT-4o flags unchanged so results line up with published
GenericAgent numbers; only the chat model differs.
"""

import argparse
import inspect
import json
import logging
import os
import re
import signal
import socket
import time
import types
import typing
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import browsergym.core.action.functions as bgym_functions
from agentlab.agents.generic_agent.agent_configs import FLAGS_GPT_4o
from agentlab.agents.generic_agent.generic_agent import GenericAgentArgs
from agentlab.analyze import inspect_results
from agentlab.experiments.study import Study, make_study
from agentlab.llm.base_api import BaseModelArgs
from agentlab.llm.chat_api import ChatModel
from browsergym.experiments.benchmark.base import HighLevelActionSetArgs
MODEL_NAME = "qwen36-iter22000-blk16-arverify-best"
# --model choices. "diffusion" is the hosted model every earlier run used.
# "qwen-flash" is the autoregressive comparison arm, Qwen 3.6 Flash on
# Alibaba's OpenAI-compatible endpoint (the same one bench/miniwob uses), with
# thinking turned on explicitly so both arms reason.
MODELS = {
    "diffusion": dict(model_name=MODEL_NAME, base_url_env="DIFFUSION_BASE_URL", key_env=None,
                      extra_body=None),
    "qwen-flash": dict(model_name="qwen3.6-flash",
                       base_url="https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
                       key_env="DASHSCOPE_API_KEY", extra_body={"enable_thinking": True}),
}
SMOKE_SITES = ("shopping", "shopping_admin", "reddit", "gitlab", "map", "wikipedia map")
JSON_TYPES = {str: "string", float: "number", int: "integer", bool: "boolean"}


def json_schema(hint):
    origin, args = typing.get_origin(hint), typing.get_args(hint)
    if hint in JSON_TYPES:
        return {"type": JSON_TYPES[hint]}
    if origin is typing.Literal:
        return {"type": "string", "enum": list(args)}
    if origin is list:
        return {"type": "array", "items": json_schema(args[0])}
    if origin in (typing.Union, types.UnionType):
        return {"anyOf": [json_schema(a) for a in args]}
    raise TypeError(f"no JSON schema for {hint}")


def action_tools():
    """The WebArena action set GenericAgent uses, as OpenAI tool definitions.

    The model is tuned for native tool calls and ignores GenericAgent's
    <action> format about a quarter of the time, so each request also offers
    these tools and the tool call is turned back into the action string.
    """
    action_set = HighLevelActionSetArgs(subsets=("webarena",)).make_action_set()
    tools = []
    for name, action in action_set.action_set.items():
        fn = getattr(bgym_functions, name)
        hints = typing.get_type_hints(fn)
        props, required = {}, []
        for p in inspect.signature(fn).parameters.values():
            props[p.name] = json_schema(hints[p.name])
            if p.default is inspect.Parameter.empty:
                required.append(p.name)
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": action.description,
                "parameters": {"type": "object", "properties": props, "required": required},
            },
        })
    return tools


def list_params(tools):
    """(function, parameter) pairs whose schema accepts a list."""
    def takes_list(schema):
        return schema.get("type") == "array" or any(takes_list(s) for s in schema.get("anyOf", []))

    return {
        (t["function"]["name"], p)
        for t in tools
        for p, s in t["function"]["parameters"]["properties"].items()
        if takes_list(s)
    }


def decode_list(value):
    """The model often sends a list as its JSON text, '["Foot (OSRM)"]'.
    Passed through as a string, select_option looked for an option with that
    literal label and selected nothing (156 of 198 calls in the first run)."""
    if isinstance(value, str) and value.strip().startswith("["):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return value
        if isinstance(decoded, list):
            return decoded
    return value


def tool_call_action(tool_calls, list_args=frozenset()):
    call = tool_calls[0].function
    args = json.loads(call.arguments or "{}")
    args = {k: decode_list(v) if (call.name, k) in list_args else v for k, v in args.items()}
    rendered = ", ".join(f"{k}={v!r}" for k, v in args.items())
    return f"<action>\n{call.name}({rendered})\n</action>"


def as_think(reasoning):
    """The model's reasoning as GenericAgent's <think> tag, so think history has
    something to carry. Tags inside it are defanged so they can't be parsed as
    the reply's own <action> or <think>."""
    text = re.sub(r"</?(action|think)>", lambda m: m.group(0).replace("<", "[").replace(">", "]"), reasoning or "")
    return f"<think>\n{text.strip()}\n</think>\n" if text.strip() else ""


CALL_TAG = re.compile(r"<function>\s*(\w+\(.*?\))\s*</function>", re.S)
XML_CALL = re.compile(r"<function=(\w+)>(.*?)</function>", re.S)
XML_PARAM = re.compile(r"<parameter=(\w+)>\s*(.*?)\s*</parameter>", re.S)


def as_action(text):
    """Rewrite the model's tool-call output as GenericAgent's <action> tag.

    The model is tuned for Qwen tool calls and often answers with
    <function>click('12')</function> or <function=click><parameter=bid>12...
    instead of the prompt's <action>click('12')</action>. Returns None when
    the text holds no call. Only the first call is kept (multiaction is off).
    """
    calls = [(m.start(), m.group(1)) for m in CALL_TAG.finditer(text)]
    for m in XML_CALL.finditer(text):
        args = []
        for name, value in XML_PARAM.findall(m.group(2)):
            is_num = name != "bid" and re.fullmatch(r"-?\d+(\.\d+)?", value)
            args.append(value if is_num else repr(value))
        calls.append((m.start(), f"{m.group(1)}({', '.join(args)})"))
    if not calls:
        return None
    return f"<action>\n{min(calls)[1]}\n</action>"


OPEN_ACTION = re.compile(r"<action>\s*(\w+\(.*?\))\s*(?:</action>|</function>|</tool_call>|$)", re.S)


def adapt_reply(content, reasoning):
    if content and re.search(r"<action>.*?</action>", content, re.S):
        return content
    # With think history on, the model copies the text format from its past
    # replies but closes the tag like a tool call: <action>click('1')</function>.
    m = OPEN_ACTION.search(content or "")
    if m:
        return f"<action>\n{m.group(1)}\n</action>"
    for text in (content, reasoning):
        action = as_action(text or "")
        if action:
            return action
    return content


WATCHDOG_S = 20 * 60
# AgentLab's ray layer cancels a task after max_steps * avg_step_timeout s
# (default 60, so 30 min), and a cancelled task fails every task downstream of
# it. When the endpoint slowed to minutes per call on 2026-10-14, that wiped
# out the think-history run and 41 tasks of the corrected run. Allow 2.5 hours;
# the watchdog above still catches tasks that stop making progress.
AVG_STEP_TIMEOUT = 300
CLEANUP_S = 3 * 60


def task_running():
    """AgentLab attaches an experiment.log handler for exactly one task's duration."""
    return any(
        isinstance(h, logging.FileHandler) and h.baseFilename.endswith("experiment.log")
        for h in logging.getLogger().handlers
    )


def on_watchdog(signum, frame):
    if not task_running():
        return  # an idle ray worker between tasks
    signal.alarm(CLEANUP_S)  # also bound a hung env.close() after this
    raise TimeoutError(f"watchdog: no progress for {WATCHDOG_S} s")


def install_watchdog():
    """Turn a hung browser step into an ordinary task error.

    On 2026-10-13 one task hung in the browser for 5.5 hours. AgentLab's ray
    timeout then cancelled it, and ray failed all 274 tasks that depended on
    it without running them. An exception raised inside the task is instead
    recorded as that task's error, and its dependents still run. The alarm is
    re-armed around every model call and when each task's model is built.
    """
    try:
        signal.signal(signal.SIGALRM, on_watchdog)
    except ValueError:  # not the main thread
        logging.getLogger(__name__).warning("watchdog not installed: not in main thread")
        return
    signal.alarm(WATCHDOG_S)


class ReasoningChatModel(ChatModel):
    """ChatModel that logs each call's reasoning text, usage, and latency.

    AgentLab messages reject extra keys, so rows go to
    $AGENTLAB_EXP_ROOT/llm_calls/<pid>.jsonl instead.
    """

    def __init__(self, *args, think_in_reply=False, extra_body=None, **kwargs):
        super().__init__(*args, **kwargs)
        create = self.client.chat.completions.create
        log_dir = Path(os.environ.get("AGENTLAB_EXP_ROOT", ".")) / "llm_calls"
        log_dir.mkdir(parents=True, exist_ok=True)
        # Containers all run as PID 1 in sequential mode, so add the hostname.
        log_path = log_dir / f"{socket.gethostname()}-{os.getpid()}.jsonl"

        tools = action_tools()
        list_args = list_params(tools)
        install_watchdog()

        request = {k: v for k, v in dict(model=self.model_name, temperature=self.temperature,
                                             max_completion_tokens=self.max_tokens,
                                             extra_body=extra_body, n_tools=len(tools)).items()
                   if v is not None}

        def log(row):
            with log_path.open("a") as f:
                f.write(json.dumps(row) + "\n")

        def recording_create(*a, **kw):
            signal.alarm(WATCHDOG_S)
            start = time.time()
            if extra_body:
                kw["extra_body"] = extra_body
            try:
                out = create(*a, tools=tools, tool_choice="auto", **kw)
            except Exception as e:
                # AgentLab retries API errors; keep each failed attempt on record.
                log({"time": start, "latency_s": time.time() - start, "error": repr(e), "request": request})
                raise
            signal.alarm(WATCHDOG_S)
            msg = out.choices[0].message
            reasoning = getattr(msg, "reasoning_content", None)
            raw = msg.content
            if msg.tool_calls:
                msg.content = tool_call_action(msg.tool_calls, list_args)
            else:
                msg.content = adapt_reply(raw, reasoning)
            if think_in_reply and msg.content and "<think>" not in msg.content:
                msg.content = as_think(reasoning) + msg.content
            row = {
                "time": start,
                "latency_s": time.time() - start,
                "finish_reason": out.choices[0].finish_reason,
                "usage": out.usage.model_dump(),
                "content": raw,
                "tool_calls": [c.model_dump() for c in msg.tool_calls or []],
                "adapted": msg.content if msg.content != raw else None,
                "reasoning": reasoning,
                "request": request,
            }
            log(row)
            return out

        self.client.chat.completions.create = recording_create


@dataclass
class DiffusionModelArgs(BaseModelArgs):
    base_url: str = None
    think_in_reply: bool = False
    key_env: str = None
    extra_body: dict = None

    def make_model(self):
        return ReasoningChatModel(
            model_name=self.model_name,
            api_key=os.environ[self.key_env] if self.key_env else "none",
            temperature=self.temperature,
            max_tokens=self.max_new_tokens,
            max_retry=4,
            min_retry_wait_time=30,
            client_args={"base_url": self.base_url, "timeout": 600},
            think_in_reply=self.think_in_reply,
            extra_body=self.extra_body,
        )


def smoke_tasks(metadata, per_site):
    """First read-only tasks per site: answers graded by string_match alone."""
    picked = {site: [] for site in SMOKE_SITES}
    for _, row in metadata.iterrows():
        site = row["sites"]
        if site in picked and len(picked[site]) < per_site:
            if str(row["eval_types"]).strip() == "string_match":
                picked[site].append(row["task_name"])
    return [t for tasks in picked.values() for t in tasks]


def harden_error_report():
    """AgentLab's error report crashes on tasks with no err_msg (NaN), which
    ended the first full run before its relaunch trials. Skip the report then."""
    original = inspect_results.error_report

    def safe_error_report(*a, **kw):
        try:
            return original(*a, **kw)
        except AttributeError as e:
            return f"error report unavailable: {e}"

    inspect_results.error_report = safe_error_report


def fresh_worker_per_task():
    """Run each task in a new ray worker process.

    When the watchdog interrupts a hung Playwright call, that process's
    Playwright event loop is left broken, and on 2026-10-13 every later task
    in the same worker failed at setup with "no running event loop" (156
    tasks). max_calls=1 retires the worker after each task.
    """
    import ray
    from agentlab.experiments import exp_utils, graph_execution_ray

    graph_execution_ray.run_exp = ray.remote(max_calls=1)(exp_utils.run_exp)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--smoke", type=int, default=0, help="tasks per site; 0 runs all 812")
    p.add_argument("--tasks", nargs="*", help="explicit task names, e.g. webarena.27")
    p.add_argument("--n-jobs", type=int, default=1)
    p.add_argument("--max-new-tokens", type=int, default=16_384)
    p.add_argument("--suffix", default="")
    p.add_argument("--resume", help="study dir: rerun its unfinished and errored tasks")
    p.add_argument("--dry-run", action="store_true", help="with --resume, only count tasks")
    p.add_argument("--think-history", action="store_true",
                   help="not stock: carry the model's reasoning into later steps")
    p.add_argument("--model", choices=sorted(MODELS), default="diffusion")
    p.add_argument("--record-video", action="store_true",
                   help="save Playwright video of each task to <exp_dir>/task_video/")
    args = p.parse_args()
    harden_error_report()
    fresh_worker_per_task()
    run_kwargs = dict(n_jobs=args.n_jobs, parallel_backend="ray" if args.n_jobs > 1 else "sequential")

    if args.resume:
        study = Study.load(Path(args.resume))
        # Without this, run() starts every task again in new folders.
        n_incomplete, n_error = study.find_incomplete(include_errors=True)
        print(f"resuming {n_incomplete} tasks ({n_error} errored)", flush=True)
        if args.dry_run:
            return
        study.avg_step_timeout = AVG_STEP_TIMEOUT
        study.run(**run_kwargs)
        return

    m = MODELS[args.model]
    base_url = m.get("base_url") or os.environ[m["base_url_env"]].removesuffix("/chat/completions")
    chat = DiffusionModelArgs(
        model_name=m["model_name"],
        base_url=base_url,
        key_env=m["key_env"],
        extra_body=m["extra_body"],
        max_total_tokens=131_072,
        max_input_tokens=100_000,
        max_new_tokens=args.max_new_tokens,
        temperature=0.1,
        think_in_reply=args.think_history,
    )
    flags = FLAGS_GPT_4o
    if args.think_history:
        flags = deepcopy(FLAGS_GPT_4o)
        flags.obs.use_think_history = True
    agent = GenericAgentArgs(chat_model_args=chat, flags=flags)
    agent.agent_name = f"GenericAgent-{m['model_name']}" + ("-thinkhist" if args.think_history else "")

    from browsergym.experiments.benchmark import DEFAULT_BENCHMARKS

    benchmark = DEFAULT_BENCHMARKS["webarena"]()
    task_list = args.tasks or (smoke_tasks(benchmark.task_metadata, args.smoke) if args.smoke else None)
    if task_list:
        benchmark = benchmark.subset_from_list(task_list, benchmark_name_suffix="subset")
        print("tasks:", " ".join(task_list))
    if args.record_video:
        for env_args in benchmark.env_args_list:
            env_args.record_video = True

    study = make_study(
        agent_args=[agent],
        benchmark=benchmark,
        logging_level_stdout=logging.INFO,
        suffix=args.suffix,
        ignore_dependencies=bool(task_list),
    )
    study.avg_step_timeout = AVG_STEP_TIMEOUT
    study.run(**run_kwargs)


if __name__ == "__main__":
    main()
