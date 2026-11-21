"""Gateway usage log traceability: request hash (same request -> same hash), message and request IDs, reply hash;
the request ID is logged but not returned to the client."""
import json

from baselines.claude_gateway.server import Gateway


class Stub:
    def __init__(self, text):
        self.text = text

    def create(self, params):
        return {"id": "msg_1", "type": "message", "role": "assistant", "content": [{"type": "text", "text": self.text}],
                "stop_reason": "end_turn", "usage": {"input_tokens": 10, "output_tokens": 2}, "_request_id": "req_1"}


def test_trace_fields(tmp_path):
    log = tmp_path / "usage.jsonl"
    body = {"model": "claude-haiku-5-5", "max_tokens": 256, "system": "s", "messages": [{"role": "user", "content": "q"}],
            "temperature": 0.5}
    out = []
    for text in ("Answer: A", "Answer: A", "Answer: B"):
        gw = Gateway("claude-haiku-5-5", Stub(text), None, str(log))
        out.append(gw.messages(dict(body), "anthropic", "claude-haiku-5-5", []))
    rows = [json.loads(l) for l in open(log)]
    assert all("_request_id" not in m for m in out)
    assert rows[0]["request_id"] == "req_1" and rows[0]["message_id"] == "msg_1"
    assert rows[0]["request_hash"] == rows[1]["request_hash"] == rows[2]["request_hash"]  # temperature is dropped
    assert rows[0]["reply_hash"] == rows[1]["reply_hash"] != rows[2]["reply_hash"]
    assert rows[0]["dropped_params"] == ["temperature"]
