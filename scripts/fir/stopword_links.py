"""Before/after count of links to single-stopword names ("The", "Who"), questions and documents. Free, no API.

    python scripts/fir/stopword_links.py GRAPH.json PREDICTIONS.jsonl [QUERY_LINKING.jsonl]
Graph: every entity whose name is a single stopword, its layer and degree. Questions: the exact-name linker as it
was (every name of 3+ characters) against the fixed one (graph_store.is_stopword_name), per question, with the
changed links; the question layer's Haiku links (query_linking.jsonl) that pick or name a stopword. Documents: the
build's linking decisions (GRAPH.linking.jsonl) whose name or chosen base entity is a single stopword."""
import json, sys
from collections import Counter
from pathlib import Path
from my_method.graph_store import GraphStore, is_stopword_name
from my_method.retrieval import RetrievalConfig, Retriever, _words

graph, pred = sys.argv[1], sys.argv[2]
qlink = sys.argv[3] if len(sys.argv) > 3 else None
store = GraphStore.load(graph)
stop = [(e, store.fact(e)["name"], store.fact(e).get("layer", "document"), store.g.degree(e))
        for e in store.entities() if is_stopword_name(store.fact(e)["name"])]
print(json.dumps({"stopword_entities": len(stop), "by_layer": Counter(x[2] for x in stop),
                  "largest": sorted(stop, key=lambda x: -x[3])[:15]}), flush=True)

new = Retriever(store, RetrievalConfig(mode="ppr"), texts=None)
old = Retriever.__new__(Retriever)
old.__dict__.update(new.__dict__)
names = [(e, _words(store.fact(e)["name"])) for e in store.entities()]
old.names = sorted([(e, w) for e, w in names if len(w.strip()) >= 3], key=lambda p: -len(p[1]))
qs = [json.loads(l) for l in open(pred)]
task = json.load(open(Path(pred).parent / "task.json"))
texts = {q["q_index"]: q["query"] for q in task["questions"]}
from my_method.agent import question_text
hit_old = hit_new = changed = 0
examples = []
for r in qs:
    q = question_text(texts[r["q_index"]])
    a, b = old.link(q), new.link(q)
    so = [e for e in a if is_stopword_name(store.fact(e)["name"])]
    sn = [e for e in b if is_stopword_name(store.fact(e)["name"])]
    hit_old += bool(so); hit_new += bool(sn)
    if a != b:
        changed += 1
        examples.append({"q": r["q_index"], "question": q[:110], "old": a, "new": b})
print(json.dumps({"questions": len(qs), "with_stopword_link_before": hit_old, "after": hit_new,
                  "questions_whose_links_changed": changed,
                  "left_with_no_link_after": sum(not e["new"] for e in examples)}), flush=True)
for e in examples[:25]:
    print(json.dumps(e, ensure_ascii=False))
if qlink and Path(qlink).exists():
    rows = [json.loads(l) for l in open(qlink)]
    bad = [r for r in rows if is_stopword_name(r["name"]) or (r.get("matched") and is_stopword_name(r["matched"]))]
    print(json.dumps({"question_layer_links": len(rows), "touching_stopword_before": len(bad), "after": 0,
                      "examples": [(r["name"], r.get("matched"), r["question"][:80]) for r in bad[:10]]}), flush=True)
docs = [json.loads(l) for l in open(graph + ".linking.jsonl")]
bad = [d for d in docs if is_stopword_name(d["name"]) or (d.get("matched") and is_stopword_name(d["matched"]))]
cand = sum(any(is_stopword_name(c) for c in d["candidates"]) for d in docs)
print(json.dumps({"document_links": len(docs), "touching_stopword_before": len(bad), "after": 0,
                  "decisions_with_a_stopword_candidate_shown": cand,
                  "examples": [(d["name"], d.get("matched"), d["from"][:80]) for d in bad[:10]]}), flush=True)
