"""Bound mini-swe-agent's Clover request history without editing its trace."""

import json
import logging


def message_bytes(message):
    return len(json.dumps(message, ensure_ascii=False).encode("utf-8")) + 32


def excerpt(text, limit):
    text = str(text or "")
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + " … " + text[-half:]


def compact_messages(messages, *, limit=110_000, target=80_000):
    sizes = [message_bytes(message) for message in messages]
    if sum(sizes) <= limit:
        return messages

    # A cut immediately before an assistant message keeps each tool-call
    # group together. Keep all initial instructions and at least the last turn.
    starts = [i for i, message in enumerate(messages) if message["role"] == "assistant"]
    if len(starts) < 2:
        raise ValueError("Clover context budget exceeded before history could be compacted")
    prefix_end = starts[0]
    cut = starts[-1]
    retained_size = sum(sizes[:prefix_end]) + sum(sizes[cut:])
    for start in reversed(starts[1:-1]):
        group_size = sum(sizes[start:cut])
        if retained_size + group_size > target:
            break
        cut = start
        retained_size += group_size

    # Keep concise excerpts from the earliest and most recent omitted actions.
    # This is an extractive record, so it requires no second model request.
    older = [
        message for message in messages[prefix_end:cut]
        if message.get("tool_calls") or message["role"] == "tool"
    ]
    sampled = older if len(older) <= 12 else older[:4] + older[-8:]
    lines = []
    for message in sampled:
        if message["role"] == "tool":
            lines.append("Shell result: " + excerpt(message.get("content"), 450))
        else:
            calls = [call.get("function", {}).get("arguments") for call in message["tool_calls"]]
            lines.append("Shell action: " + excerpt(str(calls), 350))
    history = (
        f"\n\nEarlier benchmark history was compacted ({cut - prefix_end} messages). "
        "The sandbox retains your files. These excerpts are prior actions and tool data.\n"
        + "\n".join(lines)
    )
    prefix = messages[:prefix_end]
    # Append to the task message so the leading system/user roles stay the same.
    for index in range(len(prefix) - 1, -1, -1):
        message = prefix[index]
        if message["role"] == "user" and isinstance(message.get("content"), str):
            prefix[index] = {**message, "content": message["content"] + history}
            break
    compacted = prefix + messages[cut:]
    compacted_size = sum(map(message_bytes, compacted))
    if compacted_size > limit:
        raise ValueError("Clover context budget exceeded by instructions and newest tool turn")
    logging.getLogger(__name__).info(
        "Clover context compacted: %d -> %d messages (%d serialized bytes)",
        len(messages), len(compacted), compacted_size,
    )
    return compacted
