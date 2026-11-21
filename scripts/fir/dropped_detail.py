"""Every base entity the cleaning dropped (and the generic words it kept), with all their facts. Free.

    python scripts/fir/dropped_detail.py BASE.json CLEAN_REPORT.json OUT.json"""
import json, sys
from my_method.graph_store import GraphStore

base_path, report_path, out_path = sys.argv[1:4]
rep = json.load(open(report_path))
store = GraphStore.load(base_path)
by_name = {}
for e in store.entities():
    by_name.setdefault(store.fact(e)["name"], []).append(e)

def facts(e, limit=None):
    out = []
    for f in store.facts_of_entity(e)[:limit]:
        d = store.fact(f)
        out.append({"subject": d["subject"], "relation": d["relation"], "object": d["object"],
                    "source_title": d.get("source_title", ""), "sentence": d["provenance"]["span"][:400]})
    return out

dropped_names = {n for n, _, _ in rep["base"]["all_dropped"]}
dropped = []
for name, cat, n in rep["base"]["all_dropped"]:
    for e in by_name.get(name, []):
        fs = facts(e)
        dropped.append({"name": name, "category": cat, "node": e, "facts": fs})
# orphans: base entities whose only facts went with a dropped entity
orph = []
for d in dropped:
    for f in d["facts"]:
        for other in (f["subject"], f["object"]):
            if other == d["name"] or other in dropped_names:
                continue
            ids = by_name.get(other, [])
            if ids and all(set(store.facts_of_entity(i)) <= {x for x in store.facts_of_entity(d["node"])} for i in ids):
                orph.append(other)
generic = [{"name": n, "facts": c, "sample": facts(by_name[n][0], 3) if n in by_name else []}
           for n, c in rep["base"]["generic_reported_not_dropped"]]
json.dump({"dropped": dropped, "orphans": sorted(set(orph)), "generic": generic,
           "summary_base": {k: v for k, v in rep["base"].items() if k not in ("all_dropped", "top_by_facts", "generic_reported_not_dropped")},
           "summary_shared": {k: v for k, v in rep["shared"].items() if k not in ("all_dropped", "top_by_facts", "generic_reported_not_dropped")},
           "document_links_to_junk": rep.get("document_links_to_junk")}, open(out_path, "w"), indent=1, ensure_ascii=False)
print(len(dropped), sum(len(d["facts"]) for d in dropped), len(set(orph)), len(generic))
