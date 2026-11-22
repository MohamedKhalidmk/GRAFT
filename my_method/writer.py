"""GRAFT write phase: read a chunk, extract facts, decide ADD / MERGE / SUPERSEDE / IGNORE for each.

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
from my_method.graph_store import GraphStore, Provenance, entity_id, is_stopword_name, norm
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
    salvaged: int = 0  # failed parses whose complete facts were kept (salvage_facts)
    llm_calls: int = 0
    linking: Counter = field(default_factory=Counter)  # entity linking outcomes (EntityLinker)

    def as_dict(self) -> dict:
        return {"ops": dict(self.ops), "rejected": dict(self.rejected), "parse_failures": self.parse_failures, "salvaged": self.salvaged,
                "writer_llm_calls": self.llm_calls, "linking": dict(self.linking)}


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

{pattern}For each fact give subject, relation and object, the serial number the text gives the fact \
(null if it has none), and span: the exact sentence the fact comes from.
Return JSON only: {{"facts": [{{"subject": "...", "relation": "...", "object": "...", "serial": 12, "span": "..."}}]}}"""

# Writer prompt v2 for chat histories (G41/G42, docs/design/graft_longmemeval_plan_design.md): added after the schema.
CHAT_RULES = """
This text is one session of a chat between a user and an assistant; its first line gives the session's date.
- The user is the entity named "user". Extract the user's own details first: what they did, own, plan, prefer, like or
  dislike, their numbers and amounts, people and pets they mention, and changes ("I switched to ...").
- Keep exact numbers, amounts, durations, counts, prices, titles and links (URLs) in the object, word for word.
- Dates: when the text says when something happened, put the date in the fact. Resolve relative dates ("yesterday",
  "last week", "two days ago") against the session date and write the absolute date (e.g. "2023/05/20").
- Also extract what the assistant said that the user may ask about later: recommendations, named items, list entries
  (with their position, e.g. relation "list item 7" for the 7th item), and answers to the user's questions.

"""

# Experiment D ("extend" mode): the writer starts from a ready-made graph and must follow its pattern.
PATTERN_BLOCK = """The memory graph already exists; you only extend it. Follow its pattern: when a fact fits one \
of the graph's relation labels below, use that label exactly, word for word. Name a new relation only \
when none fits.
Relation labels in the graph: {labels}
Example facts already stored:
{examples}

"""


def graph_pattern(store: GraphStore, n_examples: int = 6, max_labels: int | None = None) -> str:
    """The ready-made graph's relation vocabulary (its most common max_labels) and a few stored facts, for the
    extraction prompt."""
    labels = Counter(store.fact(f)["relation"] for f in store.facts())
    examples = sorted(store.facts(), key=lambda f: store.fact(f)["provenance"]["arrival"])[:n_examples]
    lines = "\n".join(f"- {store.fact(f)['subject']} | {store.fact(f)['relation']} | {store.fact(f)['object']}" for f in examples)
    return PATTERN_BLOCK.format(labels=", ".join(label for label, _ in labels.most_common(max_labels)), examples=lines)

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


def _list_first(text: str) -> bool:
    """True if the reply's JSON starts with a list: a bare list of facts, [{...}, ...], instead of {"facts": [...]}."""
    i, j = text.find("["), text.find("{")
    return i >= 0 and (j < 0 or i < j)


def salvage_facts(text: str) -> dict | None:
    """From an extraction reply cut off at the token cap (or otherwise broken), every complete fact object of its
    "facts" list, or of a bare list of facts: {"facts": [...]} with those, or None if there is none."""
    text = text or ""
    i = text.find('"facts"')
    if i < 0 and not _list_first(text):
        return None
    dec, facts, pos = json.JSONDecoder(), [], text.find("[", max(i, 0)) + 1
    if pos <= 0:
        return None
    while True:
        j = text.find("{", pos)
        if j < 0:
            break
        try:
            obj, end = dec.raw_decode(text, j)
        except json.JSONDecodeError:
            break
        if isinstance(obj, dict):
            facts.append(obj)
        pos = end
    return {"facts": facts} if facts else None


def parse_facts(text: str) -> dict:
    """An extraction reply: {"facts": [...]} as asked, or a bare list of facts [{...}, ...] (Qwen sometimes answers
    that way; 209 of G41's first 212 failed extractions did), returned as {"facts": [...]}. Raises like parse_json."""
    if _list_first(text):
        start, end = text.find("["), text.rfind("]")
        if end < start:
            raise ValueError("unclosed JSON list in reply")
        items = json.loads(text[start:end + 1])
        if not isinstance(items, list):
            raise ValueError("no JSON list in reply")
        return {"facts": [f for f in items if isinstance(f, dict)]}
    return parse_json(text)


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


LINK_PROMPT = """GRAFT-LINK
You link names found in a document to the entities of an existing knowledge graph. For each NAME you see the
fact it comes from and up to 10 CANDIDATE graph entities, each with one stored fact about it. Choose the candidate
that is the same real-world thing as the name, or "new" if none is. Same spelling is not enough (two people can
share a name); a different spelling can still be the same thing (e.g. "USA" and "United States of America").
Return JSON only: {"links": [{"name": "N1", "match": "c3"}, {"name": "N2", "match": "new"}]}"""


class EntityLinker:
    """Links each new document name to a base-graph entity (Haiku picks among the k nearest by name embedding) or
    marks it new. One call per chunk for all its undecided names; decisions are cached per name and logged."""

    def __init__(self, llm: ClaudeLLM, store: GraphStore, texts, stats: "WriterStats", k: int = 10, max_tokens: int = 2048):
        import numpy as np
        self.llm, self.texts, self.stats, self.k, self.max_tokens = llm, texts, stats, k, max_tokens
        self.base = [e for e in store.entities() if store.fact(e).get("layer") == "base"
                     and not is_stopword_name(store.fact(e)["name"])]  # never a link target: "The", "Who"
        vecs = texts.embed_texts([store.fact(e)["name"] for e in self.base]) if self.base else np.zeros((0, texts.dim))
        self.vecs = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-8)
        self.cache: dict[str, str | None] = {}  # norm(name) -> base entity name to use, or None (new)
        self.log: list[dict] = []

    def _describe(self, store: GraphStore, e: str) -> str:
        fs = store.facts_of_entity(e)
        if not fs:
            return store.fact(e)["name"]
        d = store.fact(fs[0])
        return f"{store.fact(e)['name']}  (e.g. {d['subject']} | {d['relation']} | {d['object']})"

    def link(self, chunk_id: int, facts: list["NewFact"], store: GraphStore) -> list["NewFact"]:
        import numpy as np
        context: dict[str, str] = {}
        for f in facts:
            for name in (f.subject, f.object):
                key = norm(name)
                if key in self.cache or key in context:
                    continue
                if is_stopword_name(name):  # a bare "The" is not a name: never linked to the base
                    self.cache[key] = None
                    self.stats.linking["stopword_not_linked"] += 1
                    continue
                node = entity_id(name)
                if node in store.g and store.fact(node).get("layer") != "base":  # an entity earlier documents created
                    self.cache[key] = None
                    self.stats.linking["reused_document_entity"] += 1
                    continue
                context[key] = f"{name}   [from: {f.subject} | {f.relation} | {f.object}]"
        pending = list(context)
        if pending and len(self.base):
            qv = self.texts.embed_texts([context[k].split("   [from:")[0] for k in pending])
            qv = qv / (np.linalg.norm(qv, axis=1, keepdims=True) + 1e-8)
            top = np.argsort(-(qv @ self.vecs.T), axis=1)[:, : self.k]
            lines, cands = [], {}
            for i, key in enumerate(pending):
                cands[f"N{i + 1}"] = [self.base[j] for j in top[i]]
                lines.append(f"N{i + 1}: {context[key]}")
                lines += [f"    c{c + 1}: {self._describe(store, e)}" for c, e in enumerate(cands[f'N{i + 1}'])]
            reply = None
            for _ in range(2):
                self.stats.llm_calls += 1
                self.stats.linking["calls"] += 1
                try:
                    reply = parse_json(self.llm.complete(LINK_PROMPT, "\n".join(lines), self.max_tokens).text)
                    break
                except (ValueError, json.JSONDecodeError):
                    self.stats.parse_failures += 1
            chosen = {str(x.get("name")): str(x.get("match", "new")) for x in (reply or {}).get("links", []) if isinstance(x, dict)}
            for i, key in enumerate(pending):
                tag = f"N{i + 1}"
                m = chosen.get(tag, "new")
                pick = None
                if m.startswith("c") and m[1:].isdigit() and 1 <= int(m[1:]) <= len(cands[tag]):
                    pick = cands[tag][int(m[1:]) - 1]
                self.cache[key] = store.fact(pick)["name"] if pick else None
                self.stats.linking["matched_base" if pick else ("new" if reply else "new_no_reply")] += 1
                self.log.append({"chunk": chunk_id, "name": context[key].split("   [from:")[0], "from": context[key],
                                 "candidates": [store.fact(e)["name"] for e in cands[tag]], "choice": m,
                                 "matched": store.fact(pick)["name"] if pick else None,
                                 "exact_name_was_candidate": entity_id(context[key].split("   [from:")[0]) in cands[tag]})
        elif pending:
            for key in pending:
                self.cache[key] = None
                self.stats.linking["new_no_base"] += 1
        out = []
        for f in facts:
            s = self.cache.get(norm(f.subject)) or f.subject
            o = self.cache.get(norm(f.object)) or f.object
            out.append(NewFact(s, f.relation, o, f.serial, f.span))
        return out


class LLMWriter:
    def __init__(self, llm: ClaudeLLM, schema: Schema, mode: str, revisions: bool, max_tokens: int = 8192,
                 pattern: str = "", prompt: str = "default", reply_log: str | Path | None = None):
        """pattern: graph_pattern() of a ready-made starting graph (experiment D), or "" (from scratch).
        prompt: "default", or "chat_v2" (CHAT_RULES added: chat histories, G41/G42). reply_log: a JSONL file that gets
        every raw writer reply (chunk, call, stop reason, parsed or not)."""
        assert mode in ("fixed", "free"), mode
        assert prompt in ("default", "chat_v2"), prompt
        self.llm, self.schema, self.mode, self.revisions = llm, schema, mode, revisions
        self.max_tokens = max_tokens
        self.pattern = pattern
        self.prompt = prompt
        self.reply_log = Path(reply_log) if reply_log else None
        self._chunk = None
        self.stats = WriterStats()

    def write_chunk(self, chunk_id: int, text: str, store: GraphStore) -> None:
        self._chunk = chunk_id
        facts = self.extract(text)
        if getattr(self, "linker", None) is not None:  # Haiku links new names to base-graph entities first
            facts = self.linker.link(chunk_id, facts, store)
        apply_decisions(store, chunk_id, facts, self.decide(facts, store), self.stats)

    def _ask_json(self, system: str, user: str, kind: str = "") -> dict | None:
        for attempt in range(2):  # one retry: replies are not deterministic
            self.stats.llm_calls += 1
            call = self.llm.complete(system, user, self.max_tokens)
            text, stop = call.text, getattr(call, "stop_reason", None)
            try:
                out, how = (parse_facts(text) if kind == "extract" else parse_json(text)), "parsed"
            except (ValueError, json.JSONDecodeError):
                out = salvage_facts(text) if kind == "extract" else None
                how = "salvaged" if out else "failed"
                self.stats.parse_failures += 1
                if out:
                    self.stats.salvaged += 1
            self._log_reply(kind, attempt, text, stop, how)
            if out is not None:
                return out
        return None

    def _log_reply(self, kind: str, attempt: int, text: str, stop, how: str) -> None:
        if self.reply_log is None:
            return
        with open(self.reply_log, "a") as f:
            f.write(json.dumps({"chunk_id": self._chunk, "kind": kind, "attempt": attempt, "stop_reason": stop,
                                "result": how, "chars": len(text or ""), "reply": text}, ensure_ascii=False) + "\n")

    def extract(self, text: str) -> list[NewFact]:
        if self.mode == "fixed":
            system = EXTRACT_FIXED.format(schema=self.schema.describe(), pattern=self.pattern)
            if self.prompt == "chat_v2":
                system = system.replace("Return JSON only:", CHAT_RULES + "Return JSON only:", 1)
            reply = self._ask_json(system, text, "extract") or {}
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
