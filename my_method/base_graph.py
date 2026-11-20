"""GRAFT layer 1: a base graph built beforehand from general outside data, in GRAFT's schema (--source rog: RoG
Freebase triples; --source trex: a general Wikidata slice from T-REx, chosen without the benchmark: most common
relations, most-linked entities, provenance span = the aligned Wikipedia sentence).

    python -m my_method.base_graph --out results/checkpoints/base_graphs/rog_base.json \
        --exclude-task results/runs/<any FactConsolidation run>/repeat_0/task.json \
        --exclude-graph results/checkpoints/shared_graphs/real_mh_262k_empty_start.json --max-facts 20000

Source: the SubgraphRAG training sets used before for the GNN (rmanluo/RoG-webqsp, rmanluo/RoG-cwq): real
Freebase triples about real-world entities. Freebase relation ids become readable labels
("people.person.nationality" -> "nationality"); housekeeping relations (type., common., kg., base., freebase.)
and machine ids (m.0abc) are dropped.

TRIAD-style records (github.com/MohamedKhalidmk/TRIAD): every base fact is an assertion with an author, a source
and an asserted time (arrival order, older than any document fact), verification "unverified"; entities keep a
stable key (identifier system "name", value the normalised name). The data has no dated changes, so the base
holds no supersede chains: updates come from the writer superseding base facts with document facts.

Leakage (no MemoryAgentBench test content): dropped are base facts identical to a fact in the benchmark's
documents (the empty-start graph), base facts about any question's topic entity, and base facts that share a
13-word sequence with, or have bge-small cosine >= 0.95 to, any benchmark question. Counts go to <out>.report.json.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

from my_method.graph_store import GraphStore, Provenance, entity_id, norm

DATASETS = {"webqsp": "rmanluo/RoG-webqsp", "cwq": "rmanluo/RoG-cwq"}
SKIP_PREFIX = ("type.", "common.", "kg.", "base.", "freebase.", "user.", "dataworld.", "imdb.")
MID = re.compile(r"^[mg]\.[0-9a-z_]+$")
AUTHOR = "Freebase via RoG-WebQSP/CWQ (SubgraphRAG)"


def label(relation: str) -> str | None:
    if relation.startswith(SKIP_PREFIX):
        return None
    return relation.rsplit(".", 1)[-1].replace("_", " ").strip() or None


def outside_triples(limit_per_set: int) -> list[tuple[str, str, str]]:
    from datasets import load_dataset
    seen, out = set(), []
    for name, path in DATASETS.items():
        for k, row in enumerate(load_dataset(path, split="train", streaming=True)):
            if k >= limit_per_set:
                break
            for t in row["graph"]:
                if len(t) != 3:
                    continue
                h, r, o = (str(x).strip() for x in t)
                lab = label(r)
                if not lab or not h or not o or MID.match(h) or MID.match(o):
                    continue
                key = (norm(h), norm(lab), norm(o))
                if key not in seen:
                    seen.add(key)
                    out.append((h, lab, o))
    return out


def trex_triples(trex_dir: str, top_relations: int, max_facts: int) -> list[tuple[str, str, str, str, str]]:
    """General Wikidata slice from T-REx's plain-file export (relbert/t_rex parquet: relation, head, tail, title, text),
    chosen without the benchmark: the top_relations most common relations, then the triples whose two entities are
    both among the most-linked entities (by triple count), up to max_facts. Returns (head, relation, tail, title, text)."""
    import glob
    import pyarrow.parquet as pq
    cols = ["relation", "head", "tail", "title", "text"]
    tables = [pq.read_table(f, columns=cols) for f in sorted(glob.glob(f"{trex_dir}/*.parquet"))]
    rows = [r for t in tables for r in zip(*(t.column(c).to_pylist() for c in cols))]
    rel = Counter(r[0] for r in rows)
    keep_rel = {r for r, _ in rel.most_common(top_relations)}
    rows = [r for r in rows if r[0] in keep_rel and r[1] and r[2] and r[1] != r[2]]
    deg = Counter(x for r in rows for x in (r[1], r[2]))
    rank = {e: i for i, (e, _) in enumerate(deg.most_common())}
    rows.sort(key=lambda r: max(rank[r[1]], rank[r[2]]))  # both endpoints among the most-linked
    seen, out = set(), []
    for h, r, t, title, text in rows:
        key = (norm(h), norm(r), norm(t))
        if key in seen:
            continue
        seen.add(key)
        out.append((h, r, t, title or "", text or ""))
        if len(out) >= max_facts * 1.2:  # headroom for the leakage drops
            break
    return out


def ngrams(text: str, n: int = 13) -> set:
    w = re.findall(r"[a-z0-9]+", text.lower())
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--exclude-task", required=True, help="a FactConsolidation run's task.json (chunks and questions)")
    ap.add_argument("--exclude-graph", required=True, help="the empty-start graph built from the benchmark documents")
    ap.add_argument("--max-facts", type=int, default=20000)
    ap.add_argument("--limit-per-set", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=20261120)
    ap.add_argument("--source", choices=["rog", "trex"], default="rog")
    ap.add_argument("--trex-dir", default=None)
    ap.add_argument("--top-relations", type=int, default=50)
    a = ap.parse_args()

    task = json.loads(Path(a.exclude_task).read_text())
    questions = [q["query"].rsplit("Based on the provided Knowledge Pool,", 1)[-1].rsplit("Answer:", 1)[0].strip()
                 for q in task["questions"]]
    docs = GraphStore.load(a.exclude_graph)
    doc_facts = {(norm(d["subject"]), d["relation"], norm(d["object"])) for _, d in docs.g.nodes(data=True) if d["type"] == "Fact"}
    names = [(e, " " + " ".join(re.findall(r"[a-z0-9]+", docs.fact(e)["name"].lower())) + " ") for e in docs.entities()]
    q_words = [" " + " ".join(re.findall(r"[a-z0-9]+", q.lower())) + " " for q in questions]
    topic = {norm(docs.fact(e)["name"]) for e, w in names if len(w.strip()) >= 3 and any(w in q for q in q_words)}
    q_grams = set().union(*(ngrams(q) for q in questions))

    if a.source == "trex":
        triples = trex_triples(a.trex_dir, a.top_relations, a.max_facts)
        author, source = "Wikidata via T-REx (relbert/t_rex, Wikipedia-aligned)", "outside_kg_wikidata"
    else:
        triples = [(h, r, o, "", "") for h, r, o in outside_triples(a.limit_per_set)]
        author, source = AUTHOR, "outside_kg"
    report = Counter(outside=len(triples))
    kept = []
    for h, r, o, title, text in triples:
        if (norm(h), norm(r), norm(o)) in doc_facts:
            report["dropped_same_as_document_fact"] += 1
        elif norm(h) in topic or norm(o) in topic:
            report["dropped_question_topic_entity"] += 1
        elif ngrams(f"{h} {r} {o}") & q_grams or (text and ngrams(text) & q_grams):
            report["dropped_13gram_with_question"] += 1
        else:
            kept.append((h, r, o, title, text))

    rng = np.random.default_rng(a.seed)
    if len(kept) > a.max_facts:
        if a.source == "trex":  # already ordered most-linked first: keep the top, no sampling
            kept = kept[: a.max_facts]
        else:
            kept = [kept[i] for i in sorted(rng.choice(len(kept), a.max_facts, replace=False))]

    from baselines.claude_gateway.embeddings import load_embedder
    emb = load_embedder("BAAI/bge-small-en-v1.5")
    qv = np.asarray(emb.embed(questions))
    fv = np.concatenate([np.asarray(emb.embed([f"{h} {r} {o}" for h, r, o, _, _ in kept[i:i + 512]])) for i in range(0, len(kept), 512)])
    near = (fv @ qv.T).max(1) >= 0.95
    report["dropped_embedding_cosine_0.95"] = int(near.sum())
    kept = [t for t, bad in zip(kept, near) if not bad]

    store = GraphStore()
    for i, (h, r, o, title, text) in enumerate(kept):
        span = (text.strip()[:400] if text else f"{h} {r} {o}.")
        node = store.add_fact(h, r, o, Provenance(chunk_id=-1, arrival=store.take_arrival(), serial=None, span=span),
                              author=author, source=source, source_title=title, asserted_at=i, verification="unverified",
                              layer="base")
        for e in (entity_id(h), entity_id(o)):
            store.g.nodes[e].setdefault("key", {"system": "name", "value": norm(store.g.nodes[e]["name"])})
            store.g.nodes[e].setdefault("layer", "base")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    store.save(a.out)
    report.update(kept=len(kept), relations=len({r for _, r, _ in kept}), **{f"graph_{k}": v for k, v in store.stats().items()},
                  question_topic_entities=len(topic))
    Path(a.out + ".report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
