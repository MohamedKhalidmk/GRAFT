"""Test 06 step 0: extract T-REx as a structure guide (no LLM, CPU job). Only properties, types and counts are kept,
never a (subject, object) pair, so nothing here can reach the answering model as a fact.

    python scripts/trex_guide.py --base results/checkpoints/base_graphs/trex_full_base.json \
        --docs results/checkpoints/shared_graphs/real_mh_262k_empty_start.json \
        --parses <run>/repeat_0/predictions.jsonl --out results/checkpoints/trex_guide.json

Writes:
  relations      the base's relation labels with fact counts
  types          the coarse entity types (the most common "instance of" classes, others rolled up by "subclass of")
  signature      per relation: most common subject and object types
  chains         per relation r1: the relations r2 that most often continue from r1's object (count of middle entities),
                 overall and by the middle entity's type
  functional     per relation: share of subjects with exactly one object
  inverses       relation pairs (r1, r2) where a r1 b often comes with b r2 a
  name_types     entity name -> coarse types (for linking only: what kind of thing a name is)
  doc_relations  each relation label in the document graph -> nearest base relation and its cosine
  coverage       each relation label in the question parses -> nearest base relation and its cosine; share covered
"""
import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

N_TYPES = 40  # coarse types: the most common "instance of" classes


def load_facts(path: str) -> list[tuple[str, str, str]]:
    data = json.loads(Path(path).read_text())
    return [(n["subject"], n["relation"], n["object"]) for n in data["nodes"] if n.get("type") == "Fact"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--docs", required=True)
    ap.add_argument("--parses", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--embedding_model", default="BAAI/bge-small-en-v1.5")
    ap.add_argument("--cover_min", type=float, default=0.8)
    a = ap.parse_args()
    t0 = time.time()
    facts = load_facts(a.base)
    print(f"{len(facts):,} base facts in {time.time() - t0:.0f} s", flush=True)
    rel_count = Counter(r for _, r, _ in facts)

    # coarse types: the most common "instance of" classes; any other class rolled up through "subclass of" when it
    # reaches one of them in at most 3 steps, otherwise "other"
    inst = defaultdict(set)
    sub = defaultdict(set)
    for s, r, o in facts:
        if r == "instance of":
            inst[s].add(o)
        elif r == "subclass of":
            sub[s].add(o)
    top = [c for c, _ in Counter(c for cs in inst.values() for c in cs).most_common(N_TYPES)]
    topset = set(top)

    def coarse(c: str, depth: int = 0) -> str | None:
        if c in topset:
            return c
        if depth >= 3:
            return None
        for p in sub.get(c, ()):
            x = coarse(p, depth + 1)
            if x:
                return x
        return None

    etype = {e: {coarse(c) or "other" for c in cs} for e, cs in inst.items()}

    def types_of(e: str) -> set[str]:
        return etype.get(e, {"untyped"})

    skip = {"instance of", "subclass of"}
    sig_s, sig_o = defaultdict(Counter), defaultdict(Counter)
    out_rels, in_rels = defaultdict(set), defaultdict(set)
    objs = defaultdict(set)
    pair_rels = defaultdict(set)
    for s, r, o in facts:
        if r in skip:
            continue
        for t in types_of(s):
            sig_s[r][t] += 1
        for t in types_of(o):
            sig_o[r][t] += 1
        out_rels[s].add(r)
        in_rels[o].add(r)
        objs[(s, r)].add(o)
        pair_rels[(s, o)].add(r)
    chains, chains_by_type = defaultdict(Counter), defaultdict(Counter)
    for m, rin in in_rels.items():
        rout = out_rels.get(m)
        if not rout:
            continue
        tm = types_of(m)
        for r1 in rin:
            for r2 in rout:
                if r2 != r1:
                    chains[r1][r2] += 1
                    for t in tm:
                        chains_by_type[f"{r1} | {t}"][r2] += 1
    subj_n, subj_one = Counter(), Counter()
    for (s, r), os_ in objs.items():
        subj_n[r] += 1
        subj_one[r] += len(os_) == 1
    inv = Counter()
    for (s, o), rs in pair_rels.items():
        back = pair_rels.get((o, s))
        if back:
            for r1 in rs:
                for r2 in back:
                    inv[(r1, r2)] += 1
    print(f"types, signatures, chains in {time.time() - t0:.0f} s", flush=True)

    name_types = {e: sorted(ts) for e, ts in etype.items()}  # facts name entities by name, so these keys are names

    # relation mapping: document labels and question-parse labels -> nearest base relation by embedding
    from sentence_transformers import SentenceTransformer
    import numpy as np
    emb = SentenceTransformer(a.embedding_model, device="cpu")
    base_rels = [r for r in rel_count if r not in skip]
    bv = emb.encode(base_rels, normalize_embeddings=True, batch_size=256)

    def nearest(labels: list[str]) -> dict:
        if not labels:
            return {}
        v = emb.encode(labels, normalize_embeddings=True, batch_size=256)
        sims = v @ bv.T
        return {lab: {"relation": base_rels[int(i)], "cosine": round(float(sims[k, i]), 3)}
                for k, (lab, i) in enumerate(zip(labels, sims.argmax(1)))}

    doc_facts = load_facts(a.docs)
    doc_labels = Counter(r for _, r, _ in doc_facts)
    doc_map = nearest(sorted(doc_labels))
    q_labels = Counter()
    for line in open(a.parses):
        qg = json.loads(line).get("query_graph") or {}
        for _, r, _ in qg.get("edges", []):
            q_labels[r.strip().lower()] += 1
    q_map = nearest(sorted(q_labels))
    covered = sum(n for lab, n in q_labels.items() if q_map[lab]["cosine"] >= a.cover_min)
    doc_cov = sum(n for lab, n in doc_labels.items() if doc_map[lab]["cosine"] >= a.cover_min)

    out = {
        "relations": dict(rel_count.most_common()),
        "types": top,
        "signature": {r: {"subject": sig_s[r].most_common(5), "object": sig_o[r].most_common(5)} for r in base_rels},
        "chains": {r: chains[r].most_common(15) for r in base_rels},
        "chains_by_type": {k: v.most_common(10) for k, v in chains_by_type.items() if sum(v.values()) >= 20},
        "functional": {r: round(subj_one[r] / subj_n[r], 3) for r in base_rels if subj_n[r]},
        "inverses": [[r1, r2, n] for (r1, r2), n in inv.most_common(40) if r1 != r2],
        "name_types": name_types,
        "doc_relations": {lab: {**doc_map[lab], "facts": doc_labels[lab]} for lab in doc_labels},
        "coverage": {"cover_min": a.cover_min, "question_edges": sum(q_labels.values()), "question_edges_covered": covered,
                     "document_facts": sum(doc_labels.values()), "document_facts_covered": doc_cov,
                     "question_labels": {lab: {**q_map[lab], "edges": q_labels[lab]} for lab in q_labels}},
    }
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    c = out["coverage"]
    print(json.dumps({k: v for k, v in c.items() if k != "question_labels"}))
    low = sorted(((v["cosine"], lab, v["relation"], v["edges"]) for lab, v in c["question_labels"].items()))[:25]
    for x in low:
        print("low match:", x)
    print(f"done in {time.time() - t0:.0f} s -> {a.out}")


if __name__ == "__main__":
    main()
