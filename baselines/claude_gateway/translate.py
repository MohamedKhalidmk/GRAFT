"""Translate OpenAI chat-completions requests to Claude Messages requests, and responses back.

Mem0, Letta and HippoRAG were written against OpenAI's API. Pointing them at the gateway with
an OpenAI client keeps their own code paths untouched; this module is the only place where the
request shape changes. Every dropped OpenAI parameter is reported so it can be logged.
"""

import json
import time
import uuid

# OpenAI parameters with no Claude equivalent, or that current Claude models reject (sampling).
DROPPED_PARAMS = ("temperature", "top_p", "n", "seed", "frequency_penalty", "presence_penalty",
                  "logprobs", "top_logprobs", "logit_bias", "user", "parallel_tool_calls",
                  "stream_options", "service_tier", "store", "metadata", "reasoning_effort")
DEFAULT_MAX_TOKENS = 4096  # OpenAI makes max_tokens optional; Claude requires it

STOP_REASON_TO_FINISH = {"end_turn": "stop", "stop_sequence": "stop", "max_tokens": "length",
                         "tool_use": "tool_calls", "refusal": "content_filter"}


def openai_to_anthropic(body: dict, model: str) -> tuple[dict, list[str]]:
    """Return (Claude request params, names of OpenAI params that were dropped)."""
    dropped = [k for k in DROPPED_PARAMS if k in body]
    if body.get("stream"):
        raise ValueError("streaming chat completions are not supported by the gateway")

    system_parts: list[str] = []
    messages: list[dict] = []
    for m in body["messages"]:
        role, content = m["role"], m.get("content")
        if role in ("system", "developer"):
            system_parts.append(_text(content))
        elif role == "user":
            _append(messages, "user", [{"type": "text", "text": _text(content)}])
        elif role == "assistant":
            blocks = [{"type": "text", "text": _text(content)}] if _text(content) else []
            for call in m.get("tool_calls") or []:
                blocks.append({"type": "tool_use", "id": call["id"], "name": call["function"]["name"],
                               "input": json.loads(call["function"]["arguments"] or "{}")})
            _append(messages, "assistant", blocks or [{"type": "text", "text": ""}])
        elif role in ("tool", "function"):
            _append(messages, "user", [{"type": "tool_result", "tool_use_id": m.get("tool_call_id", ""),
                                        "content": _text(content)}])
        else:
            raise ValueError(f"unsupported message role: {role}")

    response_format = body.get("response_format") or {}
    if response_format.get("type") == "json_object":
        system_parts.append("Respond with a single valid JSON object and nothing else.")
    elif response_format.get("type") == "json_schema":
        schema = response_format.get("json_schema", {}).get("schema", {})
        system_parts.append("Respond with a single valid JSON object that follows this JSON schema, "
                            f"and nothing else:\n{json.dumps(schema)}")

    params: dict = {
        "model": model,
        "max_tokens": body.get("max_completion_tokens") or body.get("max_tokens") or DEFAULT_MAX_TOKENS,
        "messages": messages,
        "thinking": {"type": "disabled"},
    }
    if system_parts:
        params["system"] = "\n\n".join(p for p in system_parts if p)
    if body.get("stop"):
        stop = body["stop"]
        params["stop_sequences"] = [stop] if isinstance(stop, str) else list(stop)
    if body.get("tools"):
        params["tools"] = [{"name": t["function"]["name"],
                            "description": t["function"].get("description", ""),
                            "input_schema": t["function"].get("parameters") or {"type": "object", "properties": {}}}
                           for t in body["tools"] if t.get("type", "function") == "function"]
        choice = _tool_choice(body.get("tool_choice"))
        if choice:
            params["tool_choice"] = choice
    return params, dropped


def anthropic_to_openai(message: dict, requested_model: str) -> dict:
    """Convert a Claude Messages response (as a dict) to an OpenAI chat.completion dict."""
    text = "".join(b["text"] for b in message["content"] if b["type"] == "text")
    tool_calls = [{"id": b["id"], "type": "function",
                   "function": {"name": b["name"], "arguments": json.dumps(b["input"])}}
                  for b in message["content"] if b["type"] == "tool_use"]
    usage = message["usage"]
    prompt_tokens = (usage["input_tokens"] + (usage.get("cache_read_input_tokens") or 0)
                     + (usage.get("cache_creation_input_tokens") or 0))
    reply: dict = {"role": "assistant", "content": text or (None if tool_calls else "")}
    if tool_calls:
        reply["tool_calls"] = tool_calls
    return {
        "id": "chatcmpl-" + uuid.uuid4().hex,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": requested_model,
        "choices": [{"index": 0, "message": reply, "logprobs": None,
                     "finish_reason": STOP_REASON_TO_FINISH.get(message.get("stop_reason"), "stop")}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": usage["output_tokens"],
                  "total_tokens": prompt_tokens + usage["output_tokens"]},
    }


def _text(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content if isinstance(part, dict))


def _append(messages: list[dict], role: str, blocks: list[dict]) -> None:
    """Claude needs alternating roles, so consecutive same-role messages are merged."""
    if messages and messages[-1]["role"] == role:
        messages[-1]["content"].extend(blocks)
    else:
        messages.append({"role": role, "content": blocks})


def _tool_choice(choice) -> dict | None:
    if choice in (None, "auto"):
        return {"type": "auto"} if choice else None
    if choice == "required":
        return {"type": "any"}
    if choice == "none":
        return {"type": "none"}
    if isinstance(choice, dict) and choice.get("type") == "function":
        return {"type": "tool", "name": choice["function"]["name"]}
    raise ValueError(f"unsupported tool_choice: {choice}")
