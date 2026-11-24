# Sources: longmemeval, t-rex (docs/reference/REFERENCES.md)
"""LongMemEval misses where the gold fact is in the graph: do the question's planned relations match the relation the
writer stored? (user, 2026-11-22). Read-only; run where the graphs are, with GRAFT's env.

    python scripts/plan_relation_check.py --items ITEMS.jsonl --cache CACHE [--verdicts V.jsonl --route ROUTE]

CACHE is a Flotilla memory_route prepare cache (graphs/, retrieval/); its retrieval records must carry the guide's plan
(Flotilla's bridge saves it from 2026-11-22). A miss is a wrong judge verdict for ROUTE when --verdicts is given, else
the gold string missing from the facts shown. The gold fact is in the graph when some fact's subject, relation,
object or source sentence contains the gold string (golds of at most 40 characters, as in the 2026-11-22 diagnosis).
Each such miss is put in one class:
  no plan                  the question was not parsed, or no start entity was found
  relation-name mismatch   none of the gold facts' relations maps to a T-REx relation the plan wanted (the guide maps
                           both sides by embedding, my_method/guide.py canon; a label below MAP_MIN maps to nothing)
  relation matches         a gold fact's relation maps to a wanted relation; the miss is elsewhere (start entity,
                           the fact not reached from it, an earlier step failing, or the answer)
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def norm(s) -> list[str]:
    return re.sub(r"[^a-z0-9$%. ]", " ", str(s).lower()).split()


def short_gold(gold) -> str | None:
    g = " ".join(norm(gold))
    return g if g and len(g) <= 40 else None


def fact_text(f: dict) -> str:
    p = f.get("provenance") or {}
    return " ".join(norm(" ".join(str(x) for x in (f.get("subject"), f.get("relation"), f.get("object"),
                                                     f.get("span") or p.get("span")))))


def gold_facts(facts: list[dict], gold: str) -> list[dict]:
    return [f for f in facts if gold in fact_text(f)]


def classify(plan: dict, gold_rels: list[tuple[str, str | None]]) -> str:
    """plan: the retrieval record's guide plan; gold_rels: (stored relation, its mapped T-REx relation or None)."""
    want = set(plan.get("want") or [])
    if not plan or not want:
        return "no plan"
    return "relation matches" if any(c in want for _, c in gold_rels if c) else "relation-name mismatch"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--verdicts")
    ap.add_argument("--route")
    ap.add_argument("--guide", default="results/checkpoints/trex_guide.json")
    ap.add_argument("--examples", type=int, default=8)
    ap.add_argument("--out")
    a = ap.parse_args()
    sys.path.insert(0, str(REPO))
    from baselines.claude_gateway.embeddings import load_embedder
    from my_method.gnn.features import TextEmbedder
    from my_method.graph_store import GraphStore
    from my_method.guide import Guide
    guide = Guide(REPO / a.guide, TextEmbedder(load_embedder("BAAI/bge-small-en-v1.5")))
    cache = Path(a.cache)
    verdicts = {}
    if a.verdicts:
        for line in open(a.verdicts):
            v = json.loads(line)
            if v["route"] == a.route:
                verdicts[v["item_id"]] = bool(v["correct"])
    rows, counts = [], collections.Counter()
    for line in open(a.items):
        it = json.loads(line)
        gold = short_gold(it.get("answer"))
        graphs = [p for p in (cache / "graphs").glob(f"{it['item_id']}.*.json") if not p.name.endswith(".build.json")]
        recs = [json.loads(p.read_text()) for p in (cache / "retrieval").glob(f"{it['item_id']}.*.json")]
        recs = sorted(recs, key=lambda r: (r.get("graft") or {}).get("max_facts") != 50)  # prefer the 50-fact record
        if not gold or not graphs or not recs or str(it.get("abstention")) == "True":
            counts["skipped (long gold, abstention, or not built)"] += 1
            continue
        ret = recs[0]["retrieval"]
        if "plan" not in ret:
            sys.exit(f"{it['item_id']}: retrieval record has no plan; rerun retrieval with the current bridge")
        missed = (not verdicts[it["item_id"]]) if a.verdicts and it["item_id"] in verdicts else \
            not any(gold in fact_text(f) for f in ret.get("facts") or [])
        if not missed:
            counts["not a miss"] += 1
            continue
        store = GraphStore.load(graphs[0])
        guide.link_pass(store)  # as retrieval does before planning
        facts = [{**store.fact(f), "id": f} for f in store.facts()]
        gf = gold_facts(facts, gold)
        if not gf:
            counts["miss, gold not in graph"] += 1
            continue
        rels = [(f["relation"], f.get("canon") or guide.canon(f["relation"])) for f in gf]  # None: maps to nothing
        cls = classify(ret["plan"], rels)
        counts[f"miss, gold in graph: {cls}"] += 1
        rows.append({"item_id": it["item_id"], "question_type": it.get("question_type"), "question": it["question"],
                     "gold": it["answer"], "class": cls, "plan_edges": ret["plan"].get("edges"),
                     "plan_want": ret["plan"].get("want"), "plan_reason": ret["plan"].get("reason"),
                     "plan_steps": ret["plan"].get("steps"), "gold_facts": [
                         {"fact": f"{f['subject']} | {f['relation']} | {f['object']}", "maps_to": c}
                         for f, (_, c) in list(zip(gf, rels))[:4]]})
    for k, v in sorted(counts.items()):
        print(f"{v:4d}  {k}")
    by_type = collections.Counter((r["question_type"], r["class"]) for r in rows)
    print("per question type:", dict(by_type))
    for r in [r for r in rows if r["class"] == "relation-name mismatch"][:a.examples]:
        print(f"\n{r['item_id']} [{r['question_type']}] {r['question']}  (gold: {r['gold']})")
        print(f"  plan: {[e[1] for e in r['plan_edges'] or []]} -> wants {r['plan_want']}")
        for g in r["gold_facts"]:
            print(f"  gold fact: {g['fact']} -> maps to {g['maps_to']}")
    if a.out:
        Path(a.out).write_text(json.dumps({"counts": counts, "rows": rows}, indent=1, default=str))


if __name__ == "__main__":
    main()
