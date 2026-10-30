"""HippoRAG-v2's prompt families: NER, triple extraction, the recognition-memory fact filter, QA.

Families are recognised by the system prompts in hipporag/prompts (identical in the benchmark's
bundled copy and in hipporag 2.0.0a4). NER and triples come from FactConsolidation's numbered
fact sentences ("0. Thomas Kyd was born in the city of London.") with simple heuristics, so the
knowledge graph, synonymy edges and PPR all run on real structure.
"""

import json
import re

from baselines.claude_gateway.fake import FakeReply, FakeRequest
from baselines.claude_gateway.fake_rules.fc_answer import FAKE_ANSWER

PRIORITY = 50  # before fc_answer: HippoRAG's QA prompt embeds the benchmark's answer prompt

NER_SYSTEM = "Your task is to extract named entities from the given paragraph."
QUERY_NER_SYSTEM = "You're a very effective entity extraction system."
TRIPLES_SYSTEM = "Your task is to construct an RDF (Resource Description Framework) graph"
FILTER_SYSTEM = "`fact_before_filter` (str): Candidate facts to be filtered"
QA_SYSTEM = "As an advanced reading comprehension assistant"

FACT = re.compile(r"(?<!\S)\d+\.\s+(.+?)(?=\s+\d+\.\s|\s*\n|$)")
ATTRIBUTE = re.compile(r"^The (?P<p>.+?) of (?P<s>.+?) is (?P<o>.+)$")
CONNECTOR = re.compile(r" (?:of|in|to|by|as|at|for|with|is|was) ")
SUBJECT_WORD = re.compile(r"^(?:[A-Z0-9][\w.'\-,]*|of|de|da|the|and|von|van|del|la|le|al)$")
STOPWORDS = {"based", "on", "the", "provided", "knowledge", "pool", "what", "which", "who", "is", "of",
             "in", "a", "an", "to", "name", "where", "was", "with", "answer", "by", "as", "at"}


def rule(request: FakeRequest) -> FakeReply | None:
    system, text = request.system, request.last_user_text
    if system.startswith((NER_SYSTEM, QUERY_NER_SYSTEM)):
        return FakeReply(json.dumps({"named_entities": entities(text)}))
    if system.startswith(TRIPLES_SYSTEM):
        match = re.search(r"Paragraph:\n```\n(.*?)\n```", text, re.DOTALL)
        return FakeReply(json.dumps({"triples": triples(match.group(1) if match else text)}))
    if FILTER_SYSTEM in system:
        return FakeReply(filter_reply(text))
    if system.startswith(QA_SYSTEM):
        return FakeReply(f"The passages contain the relevant facts.\nAnswer: {FAKE_ANSWER}")
    return None


def triples(passage: str) -> list[list[str]]:
    found = [split_fact(m.group(1).rstrip(".").strip()) for m in FACT.finditer(passage)]
    return [t for t in found if t is not None]


def entities(passage: str) -> list[str]:
    names = [name for s, _, o in triples(passage) for name in (s, o)]
    return list(dict.fromkeys(names))


def split_fact(sentence: str) -> list[str] | None:
    """(subject, predicate, object) from 'The P of S is O' or 'S <predicate> <connector> O'."""
    match = ATTRIBUTE.match(sentence)
    if match:
        return [match["s"], match["p"], match["o"]]
    words = sentence.split()
    n_subject = next((i for i, w in enumerate(words) if not SUBJECT_WORD.match(w)), len(words))
    subject, rest = " ".join(words[:n_subject]), " ".join(words[n_subject:])
    padded = " " + rest + " "
    connectors = list(CONNECTOR.finditer(padded))
    if not subject or not connectors:
        return None
    # the object is the first name-like phrase after a connector, else whatever follows the last one
    cut = next((c for c in connectors if padded[c.end():c.end() + 1].isupper()), connectors[-1])
    predicate = padded[:cut.start()].strip() or cut.group().strip()
    obj = padded[cut.end():].strip()
    return [subject, predicate, obj] if obj else None


def filter_reply(text: str) -> str:
    """Keep up to 4 candidate facts whose subject or object shares a word with the question."""
    question = re.search(r"\[\[ ## question ## \]\]\n(.*?)\n\n\[\[ ## fact_before_filter", text, re.DOTALL)
    candidates = re.search(r"\[\[ ## fact_before_filter ## \]\]\n(.*?)\n\nRespond with", text, re.DOTALL)
    facts = json.loads(candidates.group(1))["fact"] if candidates else []
    keywords = set(re.findall(r"\w+", question.group(1).lower())) - STOPWORDS if question else set()
    kept = [f for f in facts if keywords & set(re.findall(r"\w+", f"{f[0]} {f[2]}".lower()))][:4]
    return f"[[ ## fact_after_filter ## ]]\n{json.dumps({'fact': kept})}\n\n[[ ## completed ## ]]"
