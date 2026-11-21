"""Test 06 arm B dry check (free, no LLM): the guide's linking pass and chain planning on the real document graph,
using the question parses test 05 arm B already logged. Reports what linking changed and, per question, whether the
planned chain's facts contain the gold answer (compared with the gold-in-final-facts rate of mode C).

    python scripts/guide_check.py --guide results/checkpoints/trex_guide.json \
        --graph results/checkpoints/shared_graphs/real_mh_262k_empty_start.json --run <exp_wm_empty_b_qlayer run dir>
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from baselines.claude_gateway.embeddings import load_embedder
from my_method.gnn.features import TextEmbedder
from my_method.graph_store import GraphStore
from my_method.guide import Guide


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guide", required=True)
    ap.add_argument("--graph", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    store = GraphStore.load(a.graph)
    before = store.stats()
    g = Guide(a.guide, TextEmbedder(load_embedder("BAAI/bge-small-en-v1.5")))
    link = g.link_pass(store)
    after = store.stats()
    preds = [json.loads(l) for l in open(Path(a.run) / "repeat_0" / "predictions.jsonl")]
    scored = {json.loads(l)["q_index"]: json.loads(l) for l in open(Path(a.run) / "repeat_0" / "scored.jsonl")}
    rows, how = [], Counter()
    for p in preds:
        qg = p.get("query_graph") or {}
        edges = [tuple(e) for e in qg.get("edges", [])]
        chain, log = g.plan(store, edges, qg.get("matched", []))
        text = " ".join(store.fact(f)["provenance"]["span"] or "" for f in chain).lower()
        gold = scored[p["q_index"]]["answers"]
        hit = any(x.lower() in text for x in gold)
        for st in log.get("steps", []):
            how[st.get("how") or "not found"] += 1
        rows.append({"q": p["q_index"], "edges": edges, "gold": gold, "plan_facts": len(chain), "gold_in_plan": hit,
                     "gold_in_mode_c": bool(scored[p["q_index"]]["answer_in_retrieved"]),
                     "right_in_b": scored[p["q_index"]]["substring_exact_match"] > 0, "log": log,
                     "chain": [store.fact(f)["provenance"]["span"] for f in chain]})
    n = len(rows)
    summary = {"linking": {k: v for k, v in link.items() if not k.endswith("examples") and k != "merges_refused"},
               "graph_before": before, "graph_after": after,
               "questions": n, "with_plan_facts": sum(r["plan_facts"] > 0 for r in rows),
               "gold_in_plan": sum(r["gold_in_plan"] for r in rows),
               "gold_in_mode_c_facts": sum(r["gold_in_mode_c"] for r in rows),
               "gold_in_plan_not_in_mode_c": sum(r["gold_in_plan"] and not r["gold_in_mode_c"] for r in rows),
               "gold_in_plan_and_b_wrong": sum(r["gold_in_plan"] and not r["right_in_b"] for r in rows),
               "steps": dict(how)}
    Path(a.out).write_text(json.dumps({"summary": summary, "linking": link, "questions": rows}, ensure_ascii=False, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
