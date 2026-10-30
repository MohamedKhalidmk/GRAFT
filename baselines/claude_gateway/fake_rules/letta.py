"""Letta (MemGPT) agent loop: every step must be a tool call, ending with `send_message`.

For a question, the first step searches archival memory once (so that path runs), then the next
step answers with `send_message`. Arguments are filled from each tool's JSON schema, which covers
the kwargs Letta injects (`inner_thoughts`, `request_heartbeat`) in both Letta versions.
"""

from baselines.claude_gateway.fake import FakeReply, FakeRequest
from baselines.claude_gateway.fake_rules.fc_answer import FAKE_ANSWER

PRIORITY = 50

SEARCH_TOOL = "archival_memory_search"
SUMMARY_MARKER = "summarize a history of previous messages"
FAKE_SUMMARY = "FAKE SUMMARY: the user shared facts that were stored in archival memory."


def rule(request: FakeRequest) -> FakeReply | None:
    if "send_message" not in request.tool_names:
        return FakeReply(FAKE_SUMMARY) if SUMMARY_MARKER in request.system else None
    if SEARCH_TOOL in request.tool_names and not _searched(request):
        query = request.last_user_text.strip().splitlines()[-1][:200]
        return FakeReply(tool_calls=[(SEARCH_TOOL, _arguments(request, SEARCH_TOOL, query=query))])
    return FakeReply(tool_calls=[("send_message", _arguments(request, "send_message", message=FAKE_ANSWER))])


def _searched(request: FakeRequest) -> bool:
    """True once the current turn already called archival_memory_search."""
    for message in reversed(request.messages):
        blocks = message["content"] if isinstance(message["content"], list) else []
        if message["role"] == "assistant":
            return any(b.get("type") == "tool_use" and b["name"] == SEARCH_TOOL for b in blocks)
        if not any(b.get("type") == "tool_result" for b in blocks):
            return False  # a plain user message starts a new turn
    return False


def _arguments(request: FakeRequest, tool: str, **given) -> dict:
    """Fill every schema property: given values first, then Letta's injected kwargs, then type defaults."""
    schema = next(t["input_schema"] for t in request.tools if t["name"] == tool)
    defaults = {"inner_thoughts": "Using my memory to answer.", "thinking": "Using my memory to answer.",
                "request_heartbeat": tool != "send_message", "page": 0}
    by_type = {"string": "", "integer": 0, "number": 0, "boolean": False, "array": [], "object": {}}
    args = {}
    for name, prop in (schema.get("properties") or {}).items():
        if name in given:
            args[name] = given[name]
        elif name in defaults:
            args[name] = defaults[name]
        elif name in schema.get("required", []):
            args[name] = by_type.get(prop.get("type"), "")
    return args
