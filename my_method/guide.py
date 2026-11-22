# Sources: t-rex, bge-small (docs/reference/REFERENCES.md)
"""T-REx as a structure guide (test 06 arm B; design docs/design/graft_trex_structure_guide_design.md).

The guide file (scripts/trex_guide.py) holds only relation labels, coarse entity types, type signatures, relation chain
counts and name types: no (subject, object) pair from T-REx. Nothing from it is added to the graph or to the answering
prompt. It is used for two things:

  linking   link_pass(store): after the document graph is loaded, (1) every document relation label is mapped to one
            T-REx relation (embedding match, kept only at cosine >= MAP_MIN); facts about the same subject whose labels
            map to the same single-valued relation are versions of one fact, so the newer (larger serial) supersedes the
            older where the writer missed it; (2) document entities whose names differ only by case, punctuation or a
            leading article are merged, but only when their types agree.
  planning  plan(question, edges, entities): the question parser's relation chain is mapped to T-REx relations, then
            followed through the document graph from the question entity, taking the newest fact at each hop. When the
            entity has no fact with the planned relation, the hop is bridged through the document relation that T-REx
            chains most often lead from into the planned one (one extra hop). The facts found go first in the answer's
            fact list (at most PLAN_MAX); mode C fills the rest.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

from my_method.graph_store import GraphStore, entity_id, is_stopword_name, norm

MAP_MIN = 0.8  # cosine needed to map a relation label to a T-REx relation (planning)
STRICT_MIN = 0.92  # cosine needed before facts with different labels count as versions of one fact (revisions);
#                    the dry check showed 0.91 joining "founded by" with "founded in city" (location of formation)
FUNCTIONAL_MIN = 0.5  # a relation counts as single-valued when at least this share of its subjects has one object
PLAN_MAX = 10


def _key(name: str) -> str:
    """Name key for same-entity merges: case, punctuation and a leading article ignored."""
    w = re.findall(r"[a-z0-9]+", name.lower())
    if w and w[0] in ("the", "a", "an"):
        w = w[1:]
    return " ".join(w)


class Guide:
    def __init__(self, path: str | Path, texts):
        g = json.loads(Path(path).read_text())
        self.texts = texts
        self.chains = {r: dict(v) for r, v in g["chains"].items()}
        self.functional = g["functional"]
        self.signature = g["signature"]
        self.name_types = g["name_types"]
        self.rels = [r for r in g["chains"]]
        self.label_map = {lab: (v["relation"], v["cosine"]) for lab, v in g["doc_relations"].items()}
        self._rel_vecs = None
        self.log: dict = {}

    # ---- relations and types ----

    def canon(self, label: str) -> str | None:
        """The T-REx relation a label maps to, or None below MAP_MIN."""
        label = norm(label)
        if label not in self.label_map:
            if self._rel_vecs is None:
                v = self.texts.embed_texts(self.rels)
                self._rel_vecs = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-8)
            q = self.texts.embed_texts([label])[0]
            q = q / (np.linalg.norm(q) + 1e-8)
            sims = self._rel_vecs @ q
            i = int(np.argmax(sims))
            self.label_map[label] = (self.rels[i], float(sims[i]))
        rel, cos = self.label_map[label]
        return rel if cos >= MAP_MIN else None

    def types(self, store: GraphStore, entity: str) -> set[str]:
        """Coarse types: the T-REx name lookup, else what the entity's document relations imply (signatures)."""
        name = store.fact(entity)["name"]
        if name in self.name_types:
            return set(self.name_types[name]) - {"other"}
        out = set()
        for f in store.facts_of_entity(entity):
            d = store.fact(f)
            r = self.canon(d["relation"])
            if not r or r not in self.signature:
                continue
            side = "subject" if entity_id(d["subject"]) == entity else "object"
            top = self.signature[r][side][:1]
            if top and top[0][0] not in ("other", "untyped"):
                out.add(top[0][0])
        return out

    # ---- linking ----

    def link_pass(self, store: GraphStore) -> dict:
        doc_facts = [f for f in store.facts() if store.fact(f).get("layer") != "base" and not store.fact(f).get("query")]
        mapped = 0
        for f in doc_facts:
            r = self.canon(store.fact(f)["relation"])
            if r:
                store.g.nodes[f]["canon"] = r
                mapped += 1
        # revisions the writer missed: current facts of one subject whose labels map to the same single-valued relation
        groups = defaultdict(list)
        for f in doc_facts:
            d = store.fact(f)
            r = d.get("canon")
            if r and self.functional.get(r, 0) >= FUNCTIONAL_MIN and not store.is_superseded(f):
                strict = self.label_map.get(norm(d["relation"]), (None, 0.0))[1] >= STRICT_MIN
                groups[(entity_id(d["subject"]), r if strict else "label:" + norm(d["relation"]))].append(f)
        added = []
        order = lambda f: (store.fact(f)["provenance"]["serial"] if store.fact(f)["provenance"]["serial"] is not None
                           else -1, store.fact(f)["provenance"]["arrival"])
        for (_, r), fs in groups.items():
            if len(fs) < 2:
                continue
            fs = sorted(fs, key=order)
            for older, newer in zip(fs, fs[1:]):
                store.supersede(newer, older)
                added.append([store.fact(older)["relation"], store.fact(newer)["relation"], r])
        # same-entity merges: names equal up to case, punctuation and a leading article, with agreeing types
        by_key = defaultdict(list)
        for e in store.entities():
            d = store.fact(e)
            if d.get("layer") == "base" or d.get("query") or is_stopword_name(d["name"]):
                continue
            k = _key(d["name"])
            if k:
                by_key[k].append(e)
        merged, refused = [], []
        for k, es in by_key.items():
            if len(es) < 2:
                continue
            keep = max(es, key=lambda e: len(store.facts_of_entity(e)))
            tk = self.types(store, keep)
            for e in es:
                if e == keep:
                    continue
                te = self.types(store, e)
                if tk and te and not (tk & te):
                    refused.append([store.fact(keep)["name"], store.fact(e)["name"], sorted(tk), sorted(te)])
                    continue
                for _, v, d in list(store.g.out_edges(e, data=True)):
                    store.g.add_edge(keep, v, **d)
                for u, _, d in list(store.g.in_edges(e, data=True)):
                    store.g.add_edge(u, keep, **d)
                name = store.fact(keep)["name"]
                for _, v, d in list(store.g.out_edges(keep, data=True)):
                    if d["type"] in ("subject_of", "object_of") and store.fact(v)["type"] == "Fact":
                        role = "subject" if d["type"] == "subject_of" else "object"
                        if entity_id(store.fact(v)[role]) == e:
                            store.g.nodes[v][role] = name
                store.g.remove_node(e)
                merged.append([name, k])
        store._simple = None
        self.log = {"doc_facts": len(doc_facts), "relations_mapped": mapped,
                    "labels_mapped": sum(1 for lab, (_, c) in self.label_map.items() if c >= MAP_MIN),
                    "labels": len(self.label_map), "revisions_added": len(added), "revision_examples": added[:30],
                    "entities_merged": len(merged), "merge_examples": merged[:30], "merges_refused": refused[:30],
                    "merges_refused_count": len(refused)}
        return self.log

    # ---- planning ----

    def _facts_from(self, store: GraphStore, entity: str) -> list[str]:
        """Current document facts with this entity as subject."""
        if entity not in store.g:
            return []
        out = []
        for f in store.facts_of_entity(entity, "subject_of"):
            d = store.fact(f)
            if d.get("layer") == "base" or d.get("query"):
                continue
            cur = store.current(f)
            if cur not in out:
                out.append(cur)
        return out

    def _rel(self, store: GraphStore, f: str) -> str:
        d = store.fact(f)
        return d.get("canon") or self.canon(d["relation"]) or norm(d["relation"])

    def plan(self, store: GraphStore, edges: list[tuple[str, str, str]], entities: list[str]) -> tuple[list[str], dict]:
        """Follow the parsed chain through the document graph. Returns (facts in chain order, a log record)."""
        if not edges:
            return [], {"reason": "no parse"}
        start = None
        s0 = edges[0][0]
        if not s0.startswith("?") and entity_id(s0) in store.g:
            start = entity_id(s0)
        elif entities:
            start = entities[0]
        if not start:
            return [], {"reason": "no start entity"}
        want = [self.canon(r) or norm(r) for _, r, _ in edges]
        raw = [norm(r) for _, r, _ in edges]
        cur, chain, steps = start, [], []
        for r, label in zip(want, raw):
            fs = self._facts_from(store, cur)
            hit = [f for f in fs if self._rel(store, f) == r]
            same = [f for f in hit if norm(store.fact(f)["relation"]) == label]  # the question's own wording first
            exact = [f for f in hit if self.label_map.get(norm(store.fact(f)["relation"]), (None, 0.0))[1] >= STRICT_MIN]
            hit = same or exact or hit
            how = "direct"
            if not hit:  # bridge: a document relation that T-REx chains often lead from into r
                best, score = None, 0
                for f in fs:
                    n = self.chains.get(self._rel(store, f), {}).get(r, 0)
                    if n > score:
                        nxt = [g for g in self._facts_from(store, entity_id(store.fact(f)["object"])) if self._rel(store, g) == r]
                        if nxt:
                            best, score = (f, nxt[0]), n
                if best:
                    hit, how = list(best), "bridged"
            if not hit:
                steps.append({"want": r, "found": None})
                break
            if how == "direct":
                hit = [max(hit, key=lambda f: store.fact(f)["provenance"]["arrival"])]
            chain += [f for f in hit if f not in chain]
            steps.append({"want": r, "found": [store.fact(f)["relation"] for f in hit], "how": how})
            cur = entity_id(store.fact(hit[-1])["object"])
        return chain[:PLAN_MAX], {"start": store.fact(start)["name"], "want": want, "steps": steps, "facts": len(chain)}
