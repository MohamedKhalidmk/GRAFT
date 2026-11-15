"""GRAFT writer prompts (my_method/writer.py): extraction and ADD/MERGE/SUPERSEDE/IGNORE decisions.

Extraction replies come from the rule writer's FactConsolidation template parser, so the offline
graph has realistic structure. Decisions: same subject and relation as a stored or earlier fact ->
MERGE if the object matches, else SUPERSEDE (ADD when SUPERSEDE is not offered); otherwise ADD.
"""

import json
import re

from baselines.claude_gateway.fake import FakeReply, FakeRequest
from my_method.graph_store import norm
from my_method.writer import load_fc_patterns, rule_extract

PRIORITY = 10

PATTERNS = load_fc_patterns()
NEW = re.compile(r"^NEW (n\d+): \[serial [^\]]*\] (.*?) \| (.*?) \| (.*?)$")
STORED = re.compile(r"^\s+stored (f:\d+): \[serial [^\]]*\] (.*?) \| (.*?) \| (.*?)$")
EARLIER = re.compile(r"^\s+earlier new (n\d+)$")


def rule(request: FakeRequest) -> FakeReply | None:
    if request.system.startswith("SGAR-EXTRACT fixed"):
        facts = [f.__dict__ for f in rule_extract(request.last_user_text, PATTERNS)]
        return FakeReply(json.dumps({"facts": facts}))
    if request.system.startswith("SGAR-EXTRACT free"):
        facts = rule_extract(request.last_user_text, PATTERNS)
        names = list(dict.fromkeys(n for f in facts for n in (f.subject, f.object)))
        ids = {n: f"n{i}" for i, n in enumerate(names)}
        return FakeReply(json.dumps({
            "nodes": [{"id": ids[n], "type": "Thing", "name": n} for n in names],
            "edges": [{"source": ids[f.subject], "label": f.relation, "target": ids[f.object],
                       "serial": f.serial, "span": f.span} for f in facts]}))
    if request.system.startswith("SGAR-OPS"):
        return FakeReply(json.dumps({"decisions": _decide(request.last_user_text, "SUPERSEDE" in request.system)}))
    return None


def _decide(text: str, supersede: bool) -> list[dict]:
    new: dict[str, tuple[str, str, str]] = {}
    decisions = []
    current = None
    for line in text.splitlines():
        if m := NEW.match(line):
            current = m.group(1)
            new[current] = (norm(m.group(2)), norm(m.group(3)), norm(m.group(4)))
            decisions.append({"new": int(current[1:]), "op": "ADD", "target": None})
            continue
        if current is None:
            continue
        if m := STORED.match(line):
            other, ref = (norm(m.group(2)), norm(m.group(3)), norm(m.group(4))), m.group(1)
        elif m := EARLIER.match(line):
            other, ref = new[m.group(1)], m.group(1)
        else:
            continue
        subject, relation, obj = new[current]
        if other[:2] == (subject, relation):
            op = "MERGE" if other[2] == obj else ("SUPERSEDE" if supersede else "ADD")
            decisions[-1] = {"new": int(current[1:]), "op": op, "target": ref if op != "ADD" else None}
    return decisions
