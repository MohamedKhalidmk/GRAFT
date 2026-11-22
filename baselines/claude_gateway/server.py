# Sources: anthropic-sdk, claude-haiku (docs/reference/REFERENCES.md)
"""The Claude gateway: one local HTTP server every method talks to.

Endpoints
    POST /v1/messages          Claude Messages API (used by our own code via the Anthropic SDK)
    POST /v1/chat/completions  OpenAI-style chat, translated to Claude (Mem0, Letta, HippoRAG)
    POST /v1/embeddings        OpenAI-style embeddings from the run's shared embedding model
    GET  /v1/models            minimal model list (some clients check it)
    POST /control/phase        the method process reports "build" / "query" (+ q_index) / "done"

Whatever model a client asks for, the gateway answers with the configured Claude model, with
thinking disabled and no sampling parameters. Every call is appended to a usage log with its
phase, tokens and cost. With --fake, replies come from baselines/claude_gateway/fake.py and the
Anthropic API is never contacted.

    python -m baselines.claude_gateway.server --port 8765 --model claude-haiku-5-5 \
        --embedding-model hash:384 --usage-log usage.jsonl --fake
"""

import argparse
import base64
import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from baselines.claude_gateway.embeddings import load_embedder
from baselines.claude_gateway.fake import FakeBackend
from baselines.claude_gateway.translate import anthropic_to_openai, openai_to_anthropic
from eval.cost import token_cost

# Request fields the Anthropic SDK may send that the gateway must not forward to the model.
SAMPLING_PARAMS = ("temperature", "top_p", "top_k")


class RealBackend:
    def __init__(self):
        import anthropic  # only the real backend needs the SDK and the API key
        self.client = anthropic.Anthropic(base_url="https://api.anthropic.com", max_retries=5)

    def create(self, params: dict) -> dict:
        # the raw response gives the API's request-id header, logged per call so server-side changes can be traced
        raw = self.client.messages.with_raw_response.create(**params)
        message = raw.parse().model_dump(mode="json")
        message["_request_id"] = raw.headers.get("request-id")
        return message


class OpenAIBackend:
    """A local OpenAI-compatible server (vLLM serving Qwen) behind the Claude Messages interface: every GRAFT call
    (writer, linker, question parse, answer) keeps its prompt, only the model changes. Thinking off, greedy."""

    def __init__(self, base_url: str, model: str, thinking: bool = False):
        from openai import OpenAI
        self.client = OpenAI(base_url=base_url, api_key="EMPTY", max_retries=3, timeout=3600)
        self.served, self.thinking = model, thinking  # thinking (G42 writer arm): Qwen reasons first; the reply is
        # only its final text (the server's reasoning parser keeps the reasoning apart), so JSON parsing is unchanged

    @staticmethod
    def _text(content) -> str:
        if isinstance(content, str):
            return content
        return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")

    def create(self, params: dict) -> dict:
        msgs = []
        if params.get("system"):
            msgs.append({"role": "system", "content": self._text(params["system"])})
        msgs += [{"role": m["role"], "content": self._text(m["content"])} for m in params["messages"]]
        r = self.client.chat.completions.create(model=self.served, messages=msgs, max_tokens=params["max_tokens"],
                                                temperature=0.0,
                                                extra_body={"chat_template_kwargs": {"enable_thinking": self.thinking}})
        c = r.choices[0]
        return {"id": r.id, "type": "message", "role": "assistant", "model": self.served,
                "content": [{"type": "text", "text": c.message.content or ""}],
                "stop_reason": "max_tokens" if c.finish_reason == "length" else "end_turn", "stop_sequence": None,
                "usage": {"input_tokens": r.usage.prompt_tokens, "output_tokens": r.usage.completion_tokens,
                          "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}


class Gateway:
    def __init__(self, model: str, backend, embedder, usage_log: str):
        self.model = model
        self.backend = backend
        self.embedder = embedder
        self.usage_log = usage_log
        self.phase = {"phase": "init", "q_index": None}
        self.lock = threading.Lock()

    def messages(self, body: dict, api: str, requested_model: str, dropped: list[str]) -> dict:
        params = {k: v for k, v in body.items() if k not in SAMPLING_PARAMS and k != "stream"}
        dropped = dropped + [k for k in SAMPLING_PARAMS if k in body]
        params["model"] = self.model
        params.setdefault("thinking", {"type": "disabled"})
        start = time.time()
        request_hash = hashlib.sha256(json.dumps(params, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
        message = self.backend.create(params)
        self._log(api, requested_model, message, time.time() - start, dropped, request_hash)
        message.pop("_request_id", None)  # logged, not part of the Messages reply
        return message

    def _log(self, api: str, requested_model: str, message: dict, latency: float, dropped: list[str],
             request_hash: str = "") -> None:
        u = message["usage"]
        read, write = u.get("cache_read_input_tokens") or 0, u.get("cache_creation_input_tokens") or 0
        with self.lock:
            row = {"ts": time.time(), **self.phase, "api": api, "requested_model": requested_model,
                   "model": self.model, "input_tokens": u["input_tokens"], "output_tokens": u["output_tokens"],
                   "cache_read_tokens": read, "cache_write_tokens": write,
                   "cost_usd": token_cost(self.model, u["input_tokens"], u["output_tokens"], read, write),
                   "latency_s": latency, "stop_reason": message.get("stop_reason"), "dropped_params": dropped,
                   # traceability (added 2026-11-21): the same hash means the same request was sent; message and
                   # request IDs identify the call on the API side; the reply hash shows whether the answer changed
                   "request_hash": request_hash, "message_id": message.get("id"),
                   "request_id": message.get("_request_id"),
                   "reply_hash": hashlib.sha256("".join(b.get("text", "") for b in message.get("content", [])
                                                        if isinstance(b, dict)).encode()).hexdigest()[:16]}
            with open(self.usage_log, "a") as f:
                f.write(json.dumps(row) + "\n")


def make_handler(gw: Gateway):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep stdout for the run log, not per-request noise
            pass

        def _reply(self, status: int, payload: dict) -> None:
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self) -> dict:
            return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")

        def do_GET(self):
            path = self.path.split("?")[0].rstrip("/")
            if path in ("/v1/models", "/models"):
                self._reply(200, {"object": "list", "data": [{"id": gw.model, "object": "model", "owned_by": "graft"}]})
            elif path == "/health":
                self._reply(200, {"ok": True})
            else:
                self._reply(404, {"error": {"message": f"unknown path {self.path}"}})

        def do_POST(self):
            path = self.path.split("?")[0].rstrip("/")
            try:
                body = self._body()
                if path == "/control/phase":
                    with gw.lock:
                        gw.phase = {"phase": body["phase"], "q_index": body.get("q_index")}
                    self._reply(200, {"ok": True})
                elif path == "/v1/messages":
                    self._reply(200, gw.messages(body, "anthropic", body.get("model", ""), []))
                elif path in ("/v1/chat/completions", "/chat/completions"):
                    params, dropped = openai_to_anthropic(body, gw.model)
                    message = gw.messages(params, "openai", body.get("model", ""), dropped)
                    self._reply(200, anthropic_to_openai(message, body.get("model", gw.model)))
                elif path in ("/v1/embeddings", "/embeddings"):
                    self._reply(200, embeddings_response(gw.embedder, body))
                else:
                    self._reply(404, {"error": {"message": f"unknown path {self.path}"}})
            except Exception as e:  # report to the client instead of dropping the connection
                status = getattr(e, "status_code", 500)
                print(f"[gateway] {path} failed: {type(e).__name__}: {e}", flush=True)
                self._reply(status if isinstance(status, int) else 500,
                            {"type": "error", "error": {"type": type(e).__name__, "message": str(e)}})

    return Handler


def embeddings_response(embedder, body: dict) -> dict:
    texts = body["input"] if isinstance(body["input"], list) else [body["input"]]
    if texts and not isinstance(texts[0], str):
        raise ValueError("token-id embedding inputs are not supported")
    vectors = embedder.embed(texts)
    as_base64 = body.get("encoding_format") == "base64"
    data = [{"object": "embedding", "index": i,
             "embedding": base64.b64encode(v.tobytes()).decode() if as_base64 else v.tolist()}
            for i, v in enumerate(vectors)]
    return {"object": "list", "data": data, "model": embedder.name,
            "usage": {"prompt_tokens": 0, "total_tokens": 0}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--embedding-model", required=True)
    parser.add_argument("--usage-log", required=True)
    parser.add_argument("--fake", action="store_true", help="never call the Anthropic API")
    parser.add_argument("--thinking", action="store_true", help="local backend: Qwen thinks before replying (off by default)")
    parser.add_argument("--openai-base-url", default=None,
                        help="answer with a local OpenAI-compatible server (vLLM) instead of Claude, e.g. http://127.0.0.1:8000/v1")
    args = parser.parse_args()

    backend = FakeBackend() if args.fake else OpenAIBackend(args.openai_base_url, args.model, args.thinking) if args.openai_base_url \
        else RealBackend()
    gw = Gateway(args.model, backend, load_embedder(args.embedding_model), args.usage_log)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(gw))
    print(f"[gateway] READY on 127.0.0.1:{args.port} model={args.model} "
          f"embeddings={gw.embedder.name} mode={'FAKE' if args.fake else 'LOCAL ' + args.openai_base_url if args.openai_base_url else 'REAL'}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
