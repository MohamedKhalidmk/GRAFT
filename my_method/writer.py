"""SGAR write phase: read a chunk, extract facts, decide ADD / MERGE / SUPERSEDE / IGNORE for each.

Two writers share one decision-applying step:
- LLMWriter (the method): Claude extracts facts (constrained by the schema, or free-form for the
  ablation), then Claude picks one operation per fact against the existing graph. Facts with no
  stored candidate are ADDed without asking Claude.
- RuleWriter (ablation and offline test helper): regexes built from FactConsolidation's 37 relation
  templates extract facts; the newest fact for a (subject, relation) key supersedes the older one.
  It knows the benchmark's sentence templates, so it is an upper-bound style reference, not a method.

With revisions off, SUPERSEDE is not offered and facts are only ever appended.
"""

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from baselines.claude_llm import ClaudeLLM
from my_method.graph_store import GraphStore, Provenance, entity_id, norm
from my_method.schema import Schema

FC_RELATIONS = Path(__file__).resolve().parent / "fc_relations.json"
MAX_CANDIDATES = 10  # stored facts shown to Claude per new fact
OPS_REVISIONS = ("ADD", "MERGE", "SUPERSEDE", "IGNORE")
OPS_APPEND_ONLY = ("ADD", "MERGE", "IGNORE")


@dataclass
class NewFact:
    subject: str
    relation: str
    object: str
    serial: int | None
    span: str


@dataclass
class Decision:
    op: str
    target: str | None = None  # stored fact id ("f:12") or earlier new fact in this chunk ("n3")


@dataclass
class WriterStats:
    ops: Counter = field(default_factory=Counter)
    rejected: Counter = field(default_factory=Counter)  # facts dropped by schema validation, by reason
    parse_failures: int = 0
    llm_calls: int = 0

    def as_dict(self) -> dict:
        return {"ops": dict(self.ops), "rejected": dict(self.rejected), "parse_failures": self.parse_failures,
                "writer_llm_calls": self.llm_calls}


# ---------------------------------------------------------------------------- shared

def candidates_for(store: GraphStore, fact: NewFact) -> list[str]:
    """Current stored facts about the same subject (any relation), newest first."""
    subject = entity_id(fact.subject)
    if subject not in store.g:
        return []
    found = {store.current(f) for f in store.facts_of_entity(subject, "subject_of")}
    return sorted(found, key=lambda f: -store.fact(f)["provenance"]["arrival"])[:MAX_CANDIDATES]


def apply_decisions(store: GraphStore, chunk_id: int, facts: list[NewFact], decisions: list[Decision],
                    stats: WriterStats) -> None:
    stored: dict[str, str] = {}  # "n3" -> stored fact id, for in-chunk targets
    for i, (fact, decision) in enumerate(zip(facts, decisions)):
        target = stored.get(decision.target, decision.target) if decision.target else None
        if target is not None and target not in store.g:
            target = None
        op = decision.op if target or decision.op in ("ADD", "IGNORE") else "ADD"
        stats.ops[op] += 1
        if op == "IGNORE":
            continue
        prov = Provenance(chunk_id=chunk_id, arrival=store.take_arrival(), serial=fact.serial, span=fact.span)
        if op == "MERGE":
            store.merge(target, prov)
            stored[f"n{i}"] = target
            continue
        node = store.add_fact(fact.subject, fact.relation, fact.object, prov)
        stored[f"n{i}"] = node
        if op == "SUPERSEDE":
            store.supersede(node, store.current(target))


# ---------------------------------------------------------------------------- rule writer

def load_fc_patterns() -> list[tuple[str, re.Pattern]]:
    """(relation label, regex) for each FactConsolidation template, most specific first."""
    relations = json.loads(FC_RELATIONS.read_text())
    patterns = []
    for r in sorted(relations, key=lambda r: -len(r["template"].replace("{}", ""))):
        before, after = r["template"].split("{}")
        regex = "^" + re.escape(before) + r"(?P<s>.+?)" + re.escape(after) + r" (?P<o>.+)$"
        patterns.append((r["label"], re.compile(regex)))
    return patterns


FACT_SPLIT = re.compile(r"(?:^|\s)(\d+)\.(?:\s+|$)")


def split_numbered_facts(text: str) -> list[tuple[int | None, str]]:
    """Split a chunk into (serial, sentence). A sentence before the first number (its number was
    cut into the previous chunk by the benchmark's chunker) gets serial None."""
    text = text.replace("Here is a list of facts:", " ")
    parts = FACT_SPLIT.split(text)
    out: list[tuple[int | None, str]] = []
    if parts[0].strip():
        out.append((None, parts[0].strip()))
    for serial, sentence in zip(parts[1::2], parts[2::2]):
        if sentence.strip():
            out.append((int(serial), sentence.strip()))
    return out


def parse_fc_sentence(sentence: str, patterns) -> tuple[str, str, str] | None:
    sentence = sentence[:-1] if sentence.endswith(".") else sentence  # "Washington, D.C.." keeps one dot
    for label, pattern in patterns:
        if m := pattern.match(sentence):
            return m.group("s"), label, m.group("o")
    return None


def rule_extract(text: str, patterns) -> list[NewFact]:
    facts = []
    for serial, sentence in split_numbered_facts(text):
        if parsed := parse_fc_sentence(sentence, patterns):
            facts.append(NewFact(*parsed, serial=serial, span=sentence))
    return facts


class RuleWriter:
    def __init__(self, revisions: bool):
        self.revisions = revisions
        self.patterns = load_fc_patterns()
        self.stats = WriterStats()

    def write_chunk(self, chunk_id: int, text: str, store: GraphStore) -> None:
        facts = rule_extract(text, self.patterns)
        decisions: list[Decision] = []
        latest: dict[tuple[str, str], str] = {}  # key -> id of the newest version seen so far
        for i, fact in enumerate(facts):
            key = (norm(fact.subject), norm(fact.relation))
            versions = [store.current(f) for f in store.facts_with_key(fact.subject, fact.relation)]
            previous = latest.get(key) or (max(versions, key=lambda f: store.fact(f)["provenance"]["arrival"])
                                           if versions else None)
            if previous is None:
                decisions.append(Decision("ADD"))
            elif self._same_object(store, previous, facts, fact):
                decisions.append(Decision("MERGE", previous))
            else:
                decisions.append(Decision("SUPERSEDE", previous) if self.revisions else Decision("ADD"))
            if decisions[-1].op != "MERGE":
                latest[key] = f"n{i}"
        apply_decisions(store, chunk_id, facts, decisions, self.stats)

    @staticmethod
    def _same_object(store: GraphStore, previous: str, facts: list[NewFact], fact: NewFact) -> bool:
        if previous.startswith("n"):
            return norm(facts[int(previous[1:])].object) == norm(fact.object)
        return norm(store.fact(previous)["object"]) == norm(fact.object)


# ---------------------------------------------------------------------------- LLM writer

EXTRACT_FIXED = """SGAR-EXTRACT fixed
You are the memory writer of an agent. Read the text and extract every fact that fits the schema \
below, and nothing that does not fit it.

{schema}

For each fact give subject, relation and object, the serial number the text gives the fact \
(null if it has none), and span: the exact sentence the fact comes from.
Return JSON only: {{"facts": [{{"subject": "...", "relation": "...", "object": "...", "serial": 12, "span": "..."}}]}}"""

EXTRACT_FREE = """SGAR-EXTRACT free
You are the memory writer of an agent. Read the text and store its knowledge as a graph, in \
whatever structure you think best: choose your own node types and edge labels.
For each edge give the serial number the text gives that statement (null if none) and span: the \
exact sentence it comes from.
Return JSON only: {"nodes": [{"id": "n1", "type": "...", "name": "..."}], \
"edges": [{"source": "n1", "label": "...", "target": "n2", "serial": 12, "span": "..."}]}"""

OPS_PROMPT = """SGAR-OPS
You maintain an agent's memory graph. For each NEW fact choose one operation against the stored \
facts listed under it (and earlier NEW facts, ids n0, n1, ...):
- ADD: the fact is new information.
- MERGE: the same fact is already stored; give its id as target.
{supersede}- IGNORE: the fact is not worth storing.
A fact with a larger serial number is newer.
Return JSON only, one decision per NEW fact: \
{{"decisions": [{{"new": 0, "op": "{ops}", "target": "f:12 or n0 or null"}}]}}"""

SUPERSEDE_LINE = ("- SUPERSEDE: the fact is a newer version of a stored fact with the same subject and "
                  "relation and a different object; give that fact's id as target. The old fact is kept "
                  "and marked outdated.\n")


def parse_json(text: str) -> dict:
    """First JSON object in the reply (Claude may wrap it in a code fence)."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in reply")
    return json.loads(text[start:end + 1])


def _serial(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class LLMWriter:
    def __init__(self, llm: ClaudeLLM, schema: Schema, mode: str, revisions: bool, max_tokens: int = 8192):
        assert mode in ("fixed", "free"), mode
        self.llm, self.schema, self.mode, self.revisions = llm, schema, mode, revisions
        self.max_tokens = max_tokens
        self.stats = WriterStats()

    def write_chunk(self, chunk_id: int, text: str, store: GraphStore) -> None:
        facts = self.extract(text)
        apply_decisions(store, chunk_id, facts, self.decide(facts, store), self.stats)

    def _ask_json(self, system: str, user: str) -> dict | None:
        for _ in range(2):  # one retry: replies are not deterministic
            self.stats.llm_calls += 1
            try:
                return parse_json(self.llm.complete(system, user, self.max_tokens).text)
            except (ValueError, json.JSONDecodeError):
                self.stats.parse_failures += 1
        return None

    def extract(self, text: str) -> list[NewFact]:
        if self.mode == "fixed":
            reply = self._ask_json(EXTRACT_FIXED.format(schema=self.schema.describe()), text) or {}
            raw = [f for f in reply.get("facts", []) if isinstance(f, dict)]
        else:
            reply = self._ask_json(EXTRACT_FREE, text) or {}
            names = {n.get("id"): n.get("name", "") for n in reply.get("nodes", []) if isinstance(n, dict)}
            raw = [{"subject": names.get(e.get("source"), ""), "relation": e.get("label", ""),
                    "object": names.get(e.get("target"), ""), "serial": e.get("serial"), "span": e.get("span", "")}
                   for e in reply.get("edges", []) if isinstance(e, dict)]
        facts = []
        for f in raw:
            reason = self.schema.validate_fact(f) if self.mode == "fixed" else (
                None if all(str(f.get(k) or "").strip() for k in ("subject", "relation", "object")) else "empty field")
            if reason:
                self.stats.rejected[reason.split("'")[0].strip()] += 1
                continue
            facts.append(NewFact(f["subject"], f["relation"], f["object"], _serial(f.get("serial")),
                                 str(f.get("span") or "")))
        return facts

    def decide(self, facts: list[NewFact], store: GraphStore) -> list[Decision]:
        candidates = [candidates_for(store, f) for f in facts]
        in_chunk = [[f"n{j}" for j in range(i) if norm(facts[j].subject) == norm(f.subject)]
                    for i, f in enumerate(facts)]
        if not any(candidates) and not any(in_chunk):
            return [Decision("ADD") for _ in facts]  # nothing to compare against: no call needed
        ops = OPS_REVISIONS if self.revisions else OPS_APPEND_ONLY
        system = OPS_PROMPT.format(supersede=SUPERSEDE_LINE if self.revisions else "", ops="|".join(ops))
        lines = []
        for i, f in enumerate(facts):
            lines.append(f"NEW n{i}: [serial {f.serial}] {f.subject} | {f.relation} | {f.object}")
            lines += [f"    stored {c}: [serial {store.fact(c)['provenance']['serial']}] "
                      f"{store.fact(c)['subject']} | {store.fact(c)['relation']} | {store.fact(c)['object']}"
                      for c in candidates[i]]
            lines += [f"    earlier new {n}" for n in in_chunk[i]]
        reply = self._ask_json(system, "\n".join(lines)) or {}
        decisions = [Decision("ADD") for _ in facts]
        for d in reply.get("decisions", []):
            if not isinstance(d, dict) or not isinstance(d.get("new"), int) or not 0 <= d["new"] < len(facts):
                continue
            op = str(d.get("op", "ADD")).upper()
            target = d.get("target")
            valid_target = target in candidates[d["new"]] or target in in_chunk[d["new"]]
            decisions[d["new"]] = Decision(op if op in ops else "ADD", target if valid_target else None)
        return decisions
