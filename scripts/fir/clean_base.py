"""Drop junk-named entities from the T-REx base graph and from the graph built on it. Free, no API.

    python scripts/fir/clean_base.py BASE.json SHARED.json OUT_SUFFIX [--generic-df 0.01]
An entity is junk when its name is ONE word (or no word) and that word is:
  stopword  an English stopword, article or question word (graph_store.STOPWORDS, NLTK's list)
  number    digits only ("1990", "2") or a number word (one ... twenty, hundred, thousand, million, first ... tenth)
  punct     no letter or digit at all ("-", "&")
  generic   a word written in lower case in at least --generic-df of the base's own Wikipedia sentences (the T-REx
            provenance spans). REPORTED ONLY, never dropped: on T-REx these are Wikidata concepts that are real
            answers (footballer, politician, village, jazz: occupation, position, genre), 130K facts.
Not junk either: ALL-CAPS names (abbreviations: OR, IN, CAN) and NLTK's contraction fragments (Ain, Don, ...),
which are real places and names.
Multi-word names ("The Who", "Take That") are never junk. Only base entities are candidates; one that document facts
use is kept and reported (dropping it would change the documents). For each dropped entity its base facts go too
(a fact without its subject or object means nothing), with every edge touching them. Writes BASE<suffix>.json,
SHARED<suffix>.json and SHARED<suffix>.json.clean_report.json; the inputs are not changed."""
import argparse, json, re
from collections import Counter
from pathlib import Path
from my_method.graph_store import STOPWORDS, GraphStore

FRAGMENTS = set("s t d ll m o re ve y ain don ma".split())  # NLTK's contraction pieces: "Ain", "Don" are real names
NUMBER_WORDS = set("""zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen
seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million billion
first second third fourth fifth sixth seventh eighth ninth tenth""".split())

ap = argparse.ArgumentParser()
ap.add_argument("base"); ap.add_argument("shared"); ap.add_argument("suffix"); ap.add_argument("--generic-df", type=float, default=0.01)
a = ap.parse_args()
base = GraphStore.load(a.base)
facts = [f for f in base.facts()]
df = Counter()
for f in facts:
    df.update(set(re.findall(r"(?<![A-Za-z0-9])[a-z][a-z0-9]*", base.fact(f)["provenance"]["span"])))
n_sent = len(facts)

def category(name):
    w = re.findall(r"[a-z0-9]+", name.lower())
    if not w:
        return "punct"
    if len(w) > 1:
        return None
    w = w[0]
    letters = re.sub(r"[^A-Za-z]", "", name)
    if w in STOPWORDS and w not in FRAGMENTS and not (letters.isupper() and len(letters) > 1):
        return "stopword"
    if w.isdigit() or w in NUMBER_WORDS:
        return "number"
    if df[w] >= a.generic_df * n_sent:
        return "generic"
    return None

def drop_plan(store):
    junk, kept_doc, generic = {}, {}, {}
    for e in store.entities():
        d = store.fact(e)
        if d.get("layer") != "base":
            continue
        c = category(d["name"])
        if not c:
            continue
        if c == "generic":  # reported, not dropped
            generic[e] = (c, d["name"], len(store.facts_of_entity(e)), 0)
            continue
        fs = store.facts_of_entity(e)
        doc = [f for f in fs if store.fact(f).get("layer") != "base"]
        (kept_doc if doc else junk)[e] = (c, d["name"], len(fs), len(doc))
    gone_facts = {f for e in junk for f in store.facts_of_entity(e) if store.fact(f).get("layer") == "base"}
    return junk, kept_doc, gone_facts, generic

def apply(store, junk, gone_facts):
    nodes = set(junk) | gone_facts
    edges = sum(1 for _ in store.g.in_edges(nodes)) + sum(1 for _ in store.g.out_edges(nodes))
    sup = sum(1 for n in gone_facts for _, _, d in list(store.g.in_edges(n, data=True)) + list(store.g.out_edges(n, data=True)) if d["type"] == "SUPERSEDES")
    before = (store.g.number_of_nodes(), store.g.number_of_edges(), len(store.facts()))
    store.g.remove_nodes_from(nodes)
    store._simple = None
    orphans = [e for e in store.entities() if store.fact(e).get("layer") == "base" and store.g.degree(e) == 0]
    store.g.remove_nodes_from(orphans)  # base entities whose only facts went with a junk entity
    after = (store.g.number_of_nodes(), store.g.number_of_edges(), len(store.facts()))
    return {"nodes_before": before[0], "nodes_after": after[0], "edges_before": before[1], "edges_after": after[1],
            "facts_before": before[2], "facts_after": after[2], "junk_entities_removed": len(junk),
            "base_facts_removed": len(gone_facts), "orphan_base_entities_removed": len(orphans),
            "edges_touching_removed_nodes": edges, "supersedes_edges_removed": sup}

report = {"rule": {"generic_df": a.generic_df, "sentences": n_sent}}
for label, path in (("base", a.base), ("shared", a.shared)):
    store = base if label == "base" else GraphStore.load(path)
    junk, kept_doc, gone, generic = drop_plan(store)
    top = sorted(junk.items(), key=lambda kv: -kv[1][2])
    report[label] = {"by_category": dict(Counter(v[0] for v in junk.values())),
                     "facts_by_category": dict(sum((Counter({v[0]: v[2]}) for v in junk.values()), Counter())),
                     "top_by_facts": [(v[1], v[0], v[2]) for _, v in top[:60]],
                     "all_dropped": sorted((v[1], v[0], v[2]) for v in junk.values()),
                     "generic_reported_not_dropped": sorted(((v[1], v[2]) for v in generic.values()), key=lambda x: -x[1]),
                     "kept_because_documents_use_them": [(v[1], v[0], v[2], v[3]) for v in kept_doc.values()],
                     **apply(store, junk, gone)}
    out = Path(path).with_name(Path(path).stem + a.suffix + ".json")
    store.save(out)
    report[label]["written"] = str(out)
    print(json.dumps({label: {k: v for k, v in report[label].items() if k != "top_by_facts"}}), flush=True)
    if label == "shared":
        links = [json.loads(l) for l in open(path + ".linking.jsonl")]
        names = {v[1].lower() for v in junk.values()} | {v[1].lower() for v in kept_doc.values()}
        hit = [(r["name"], r["matched"], r["from"][:90]) for r in links if r.get("matched") and r["matched"].lower() in names]
        report["document_links_to_junk"] = {"count": len(hit), "examples": hit[:20]}
for i, x in enumerate(report["base"]["top_by_facts"]):
    print("top", i + 1, x)
print("document links to junk:", json.dumps(report.get("document_links_to_junk")))
Path(str(Path(a.shared).with_name(Path(a.shared).stem + a.suffix + ".json")) + ".clean_report.json").write_text(json.dumps(report, indent=1))
