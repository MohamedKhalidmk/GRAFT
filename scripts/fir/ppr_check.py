"""Free check of the PageRank stop rule on the real full T-REx graph (no API calls).

    python scripts/fir/ppr_check.py GRAPH.json PREDICTIONS.jsonl [--n 20]
For the first n questions with linked entities (from an earlier run's predictions), select the 400-node
subgraph twice: with NetworkX's default stop rule (as before the fix) and with features.pagerank (the fix).
Prints facts in each subgraph, PageRank steps and time, and the linked entities."""
import argparse, json, time
import networkx as nx
from my_method.graph_store import GraphStore
from my_method.gnn import features

ap = argparse.ArgumentParser()
ap.add_argument("graph"); ap.add_argument("predictions"); ap.add_argument("--n", type=int, default=20)
a = ap.parse_args()
t = time.time(); store = GraphStore.load(a.graph); g = store.simple_graph()
N = g.number_of_nodes()
print(json.dumps({"nodes": N, "edges": g.number_of_edges(), "load_s": round(time.time() - t),
                  "nx_stop_L1": N * 1e-6, "fixed_stop_L1": min(N * 1e-6, features.PPR_MAX_L1)}), flush=True)
rows = [json.loads(l) for l in open(a.predictions)]
rows = [r for r in rows if (r.get("linked_entities") or (r.get("meta") or {}).get("linked_entities"))][: a.n]
def facts_in(nodes): return sum(store.fact(n)["type"] == "Fact" for n in nodes)
def select(seeds, rank):
    rest = sorted((n for n in rank if n not in seeds), key=lambda n: -rank[n]); return (seeds + rest)[:400]
for r in rows:
    linked = r.get("linked_entities") or r["meta"]["linked_entities"]
    seeds = [s for s in linked if s in g]
    p = {s: 1.0 for s in seeds}
    t = time.time(); old = nx.pagerank(g, personalization=p); t_old = time.time() - t
    t = time.time(); new = features.pagerank(g, p); t_new = time.time() - t
    print(json.dumps({"q": r.get("q_index"), "linked": len(linked), "linked_sample": linked[:8],
                      "facts_old": facts_in(select(seeds, old)), "facts_new": facts_in(select(seeds, new)),
                      "s_old": round(t_old, 1), "s_new": round(t_new, 1)}), flush=True)
