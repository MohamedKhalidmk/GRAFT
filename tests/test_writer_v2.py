"""Writer v2 (G41/G42, docs/design/graft_longmemeval_plan_design.md): reply log, salvage of cut-off replies, the chat
prompt, and the gateway's thinking switch. Offline."""
import json
from pathlib import Path
from types import SimpleNamespace as NS

from my_method.graph_store import GraphStore
from my_method.schema import Schema
from my_method.writer import CHAT_RULES, LLMWriter, parse_facts, salvage_facts

REPO = Path(__file__).resolve().parent.parent


def test_salvage_keeps_complete_facts_before_the_cut():
    """Checks that salvage_facts recovers every complete fact before the cut in a truncated reply, and returns None when there is none.
    Guards against: a writer reply cut off at the token cap losing every fact it already listed."""
    cut = '{"facts": [{"subject": "user", "relation": "owns", "object": "3 cucumber plants", "serial": null, ' \
          '"span": "I have 3 plants"}, {"subject": "user", "relation": "bought", "object": "a b'
    assert salvage_facts(cut) == {"facts": [{"subject": "user", "relation": "owns", "object": "3 cucumber plants",
                                             "serial": None, "span": "I have 3 plants"}]}
    assert salvage_facts("no json here") is None and salvage_facts('{"facts": [') is None


class FakeLLM:
    def __init__(self, replies):
        self.replies, self.systems = list(replies), []

    def complete(self, system, user, max_tokens):
        self.systems.append(system)
        text, stop = self.replies.pop(0)
        return NS(text=text, stop_reason=stop)


def _writer(llm, tmp_path, prompt="default"):
    schema = Schema.load(REPO / "my_method" / "schema.yaml")
    return LLMWriter(llm, schema, "fixed", True, 8192, prompt=prompt, reply_log=tmp_path / "replies.jsonl")


def test_reply_log_retry_and_salvage(tmp_path):
    """Checks that the writer retries an unparseable reply, salvages a cut-off one on the first try, and logs every attempt with its outcome.
    Guards against: failed or truncated writer replies vanishing without a trace in the reply log or the writer stats."""
    good = '{"facts": [{"subject": "user", "relation": "owns", "object": "Luna", "serial": null, "span": "my cat Luna"}]}'
    cut = '{"facts": [{"subject": "user", "relation": "visited", "object": "Science Museum", "serial": null, "span": "x"}, {"subj'
    w = _writer(FakeLLM([("oops, not json", "end_turn"), (good, "end_turn"), (cut, "max_tokens"), ("still bad", "end_turn")]), tmp_path)
    w._chunk = 3
    assert [f.object for f in w.extract("text")] == ["Luna"]           # retry after a failed parse
    w._chunk = 4
    assert [f.object for f in w.extract("text")] == ["Science Museum"]  # cut-off reply salvaged on the first try
    rows = [json.loads(l) for l in open(tmp_path / "replies.jsonl")]
    assert [(r["chunk_id"], r["attempt"], r["result"]) for r in rows] == [(3, 0, "failed"), (3, 1, "parsed"), (4, 0, "salvaged")]
    assert rows[2]["stop_reason"] == "max_tokens" and rows[0]["reply"] == "oops, not json"
    assert w.stats.parse_failures == 2 and w.stats.salvaged == 1 and w.stats.as_dict()["salvaged"] == 1


def test_chat_prompt_only_when_asked(tmp_path):
    """Checks that the chat writer rules go into the system prompt, before the JSON instruction, only for the chat_v2 prompt.
    Guards against: the chat rules leaking into the default writer prompt and changing results on the other benchmarks."""
    reply = ('{"facts": []}', "end_turn")
    plain, chat = FakeLLM([reply]), FakeLLM([reply])
    _writer(plain, tmp_path, "default").extract("t")
    _writer(chat, tmp_path, "chat_v2").extract("t")
    assert CHAT_RULES.strip() not in plain.systems[0]
    assert CHAT_RULES.strip() in chat.systems[0] and chat.systems[0].index(CHAT_RULES.strip()) < chat.systems[0].index("Return JSON only")
    assert "Resolve relative dates" in CHAT_RULES and "URLs" in CHAT_RULES and "assistant" in CHAT_RULES


def test_gateway_thinking_switch(monkeypatch):
    """Checks that the local OpenAI backend sends enable_thinking false by default and true only when thinking is switched on.
    Guards against: Qwen thinking by default as the writer and spending its token cap on reasoning instead of facts."""
    import sys
    sent = []

    class Client:
        def __init__(self, **kw):
            self.chat = NS(completions=NS(create=self.create))

        def create(self, **kw):
            sent.append(kw)
            return NS(id="r", choices=[NS(message=NS(content="{}"), finish_reason="stop")],
                      usage=NS(prompt_tokens=1, completion_tokens=1))
    monkeypatch.setitem(sys.modules, "openai", NS(OpenAI=Client))
    from baselines.claude_gateway.server import OpenAIBackend
    params = {"max_tokens": 10, "messages": [{"role": "user", "content": "hi"}]}
    OpenAIBackend("http://x", "qwen").create(params)
    OpenAIBackend("http://x", "qwen", thinking=True).create(params)
    assert [s["extra_body"]["chat_template_kwargs"]["enable_thinking"] for s in sent] == [False, True]


def test_bare_list_of_facts_is_read(tmp_path):
    """Checks that an extraction reply given as a bare JSON list of facts, whole or cut off, is read as the facts list.
    Guards against: a session's facts thrown away because Qwen answered [...] instead of {"facts": [...]}."""
    fact = {"subject": "user", "relation": "place of residence", "object": "Canada", "serial": None, "span": "I live in Canada now."}
    two = json.dumps([fact, {**fact, "relation": "preferred currency", "object": "Canadian dollars"}], indent=2)
    assert parse_facts(two)["facts"][1]["object"] == "Canadian dollars"
    assert parse_facts("```json\n" + json.dumps([fact]) + "\n```") == {"facts": [fact]}   # one fact, fenced
    assert parse_facts(json.dumps({"facts": [fact]})) == {"facts": [fact]}                 # the asked shape still works
    assert salvage_facts(two[:two.rfind("Canadian")]) == {"facts": [fact]}                 # a cut-off bare list
    w = _writer(FakeLLM([(two, "end_turn")]), tmp_path, prompt="chat_v2")
    w._chunk = 0
    assert [f.object for f in w.extract("I live in Canada now, prices in Canadian dollars please.")] == ["Canada", "Canadian dollars"]
    log = [json.loads(l) for l in open(tmp_path / "replies.jsonl")]
    assert [r["result"] for r in log] == ["parsed"]
