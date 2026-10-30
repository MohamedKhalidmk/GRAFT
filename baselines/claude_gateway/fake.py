"""Fake Claude backend for offline tests: same response shape as the real API, no API calls.

Replies come from rules in `fake_rules/`. Each module there defines
    PRIORITY: int                                  (lower runs first)
    def rule(request: FakeRequest) -> FakeReply | None
The first rule that returns a reply wins; if none does, the reply is the text "FAKE".
Rules recognise a prompt family (e.g. Mem0's fact extraction) and return output in the shape
that family's caller parses, so each system's own code runs end to end.
"""

import importlib
import pkgutil
import uuid
from dataclasses import dataclass, field

from baselines.claude_gateway import fake_rules


@dataclass
class FakeRequest:
    system: str
    messages: list[dict]  # Claude-format messages
    tools: list[dict] = field(default_factory=list)

    @property
    def last_user_text(self) -> str:
        for message in reversed(self.messages):
            if message["role"] == "user":
                return _blocks_text(message["content"])
        return ""

    @property
    def all_text(self) -> str:
        return self.system + "\n" + "\n".join(_blocks_text(m["content"]) for m in self.messages)

    @property
    def tool_names(self) -> list[str]:
        return [t["name"] for t in self.tools]


@dataclass
class FakeReply:
    text: str = ""
    tool_calls: list[tuple[str, dict]] = field(default_factory=list)  # (tool name, input)


def _blocks_text(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if block.get("type") == "text":
            parts.append(block["text"])
        elif block.get("type") == "tool_result":
            parts.append(_blocks_text(block["content"]) if not isinstance(block["content"], str) else block["content"])
    return "\n".join(parts)


def _load_rules() -> list:
    modules = [importlib.import_module(f"{fake_rules.__name__}.{m.name}")
               for m in pkgutil.iter_modules(fake_rules.__path__)]
    return [m.rule for m in sorted(modules, key=lambda m: m.PRIORITY)]


class FakeBackend:
    def __init__(self):
        self.rules = _load_rules()

    def create(self, params: dict) -> dict:
        request = FakeRequest(system=_system_text(params.get("system")), messages=params["messages"],
                              tools=params.get("tools") or [])
        reply = next((r for r in (rule(request) for rule in self.rules) if r is not None), FakeReply("FAKE"))
        content: list[dict] = [{"type": "text", "text": reply.text}] if reply.text else []
        content += [{"type": "tool_use", "id": "toolu_" + uuid.uuid4().hex[:20], "name": name, "input": args}
                    for name, args in reply.tool_calls]
        output_tokens = max(1, len(reply.text) // 4 + 20 * len(reply.tool_calls))
        capped = output_tokens > params["max_tokens"]  # report it, as the real API would
        output_tokens = min(output_tokens, params["max_tokens"])
        stop_reason = "max_tokens" if capped else "tool_use" if reply.tool_calls else "end_turn"
        return {
            "id": "msg_fake_" + uuid.uuid4().hex[:20], "type": "message", "role": "assistant",
            "model": params["model"], "content": content,
            "stop_reason": stop_reason, "stop_sequence": None,
            # rough token counts (~4 characters per token) so cost accounting is exercised
            "usage": {"input_tokens": max(1, len(request.all_text) // 4), "output_tokens": output_tokens,
                      "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
        }


def _system_text(system) -> str:
    if system is None:
        return ""
    if isinstance(system, str):
        return system
    return "".join(block.get("text", "") for block in system)
