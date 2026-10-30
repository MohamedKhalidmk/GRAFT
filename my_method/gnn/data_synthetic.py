"""Synthetic GNN training data: made-up worlds with revisions, no overlap with the benchmark.

Each world is a stream of numbered fact sentences about invented entities (random syllable names,
so no real entity from MQuAKE / FactConsolidation can appear), using the 37 relation templates.
A share of facts are later revised: a newer sentence gives the same subject and relation a new
object. The stream is written into a GraphStore with the rule writer (revisions on), exactly the
structure SGAR builds, and questions are asked about the *current* state:
    single-hop: "<template filled with the subject> ___?"           answer: newest object
    multi-hop:  "Starting from S, follow: rel1, then rel2. Which entity?"  answer: end of the chain
Only relation templates are shared with the benchmark; facts, entities and question wording are not.
"""

import json
import random
from dataclasses import dataclass

from my_method.graph_store import GraphStore, entity_id, norm
from my_method.writer import FC_RELATIONS, RuleWriter

SYLLABLES = ("ka ro mi zan tel vor qui lan dre sto pha nix bel gor uva fen sil mar dok tri "
             "ash pel run vex ola ith sar ben cor dim").split()


@dataclass
class Example:
    store: GraphStore
    question: str
    question_entities: list[str]  # entity node ids
    answer_entities: list[str]
    hops: int


def fake_name(rng: random.Random) -> str:
    def word() -> str:
        return "".join(rng.choice(SYLLABLES) for _ in range(rng.randint(2, 3))).capitalize()
    return f"{word()} {word()}"


def build_world(rng: random.Random, n_entities: int, n_facts: int, p_revision: float) -> GraphStore:
    relations = json.loads(FC_RELATIONS.read_text())
    entities = list({fake_name(rng) for _ in range(n_entities)})
    sentences, keys = [], []
    for serial in range(n_facts):
        if keys and rng.random() < p_revision:
            subject, relation = rng.choice(keys)  # revise an existing fact
        else:
            subject, relation = rng.choice(entities), rng.choice(relations)
            keys.append((subject, relation))
        obj = rng.choice([e for e in entities if e != subject])
        sentences.append(f"{serial}. {relation['template'].format(subject)} {obj}.")
    store, writer = GraphStore(), RuleWriter(revisions=True)
    for chunk_id, start in enumerate(range(0, len(sentences), 20)):
        writer.write_chunk(chunk_id, " ".join(sentences[start:start + 20]), store)
    return store


def _current_out(store: GraphStore, entity: str) -> list[str]:
    return [f for f in store.facts_of_entity(entity, "subject_of") if not store.is_superseded(f)]


def make_questions(store: GraphStore, rng: random.Random, n: int, p_multi_hop: float) -> list[Example]:
    templates = {norm(r["label"]): r["template"] for r in json.loads(FC_RELATIONS.read_text())}
    revised = [f for f in store.facts() if store.superseded_by(f) == [] and
               any(d["type"] == "SUPERSEDES" for _, _, d in store.g.out_edges(f, data=True))]
    current = [f for f in store.facts() if not store.is_superseded(f)]
    examples = []
    for _ in range(n * 3):  # some chain attempts fail; stop once n questions exist
        if len(examples) >= n:
            break
        start = rng.choice(revised if revised and rng.random() < 0.6 else current)
        d = store.fact(start)
        subject = entity_id(d["subject"])
        if rng.random() >= p_multi_hop:
            q = templates[d["relation"]].format(d["subject"]) + " ___?"
            examples.append(Example(store, q, [subject], [entity_id(d["object"])], 1))
            continue
        chain, node = [d["relation"]], entity_id(d["object"])
        for _ in range(rng.randint(1, 2)):
            nxt = _current_out(store, node)
            if not nxt:
                break
            step = store.fact(rng.choice(nxt))
            chain.append(step["relation"])
            node = entity_id(step["object"])
        if len(chain) > 1:
            q = f"Starting from {d['subject']}, follow: {', then '.join(chain)}. Which entity is it?"
            examples.append(Example(store, q, [subject], [node], len(chain)))
    return examples


def synthetic_examples(seed: int, n_worlds: int, questions_per_world: int, n_entities: int = 150,
                       n_facts: int = 400, p_revision: float = 0.35, p_multi_hop: float = 0.5) -> list[list[Example]]:
    """One list of examples per world (split train/val by world, never within one)."""
    rng = random.Random(seed)
    worlds = []
    for _ in range(n_worlds):
        store = build_world(rng, n_entities, n_facts, p_revision)
        worlds.append(make_questions(store, rng, questions_per_world, p_multi_hop))
    return worlds
