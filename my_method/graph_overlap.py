"""How much a base graph and a document graph share (exact entity ids), as JSON.

    python -m my_method.graph_overlap --base results/checkpoints/base_graphs/rog_base.json \
        --docs results/checkpoints/shared_graphs/real_mh_262k_empty_start.json --out overlap.json
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from my_method.graph_store import GraphStore, entity_id


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--docs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    b, d = GraphStore.load(a.base), GraphStore.load(a.docs)
    be, de = set(b.entities()), set(d.entities())
    sh = be & de
    touch = sum(1 for f in b.facts() if entity_id(b.fact(f)["subject"]) in sh or entity_id(b.fact(f)["object"]) in sh)
    deg = Counter({e: len(b.facts_of_entity(e)) for e in sh})
    out = {"base": a.base, "docs": a.docs, "base_facts": len(b.facts()), "base_entities": len(be),
           "base_relations": len({b.fact(f)["relation"] for f in b.facts()}), "doc_entities": len(de),
           "shared_entities_exact": len(sh), "doc_entities_shared_share": round(len(sh) / len(de), 4),
           "base_facts_touching_shared": touch, "top_shared_by_base_degree": deg.most_common(12),
           "top_base_relations": Counter(b.fact(f)["relation"] for f in b.facts()).most_common(10)}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if not k.startswith("top")}))


if __name__ == "__main__":
    main()
