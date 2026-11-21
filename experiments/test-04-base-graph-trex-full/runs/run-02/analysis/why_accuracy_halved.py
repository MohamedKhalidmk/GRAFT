import json, re, sys
D = sys.argv[1]; A = sys.argv[2]
def load(p): return {json.loads(l)["q_index"]: json.loads(l) for l in open(p)}
g, a = load(f"{D}/goat0/scored.jsonl"), load(A)
t = json.load(open(f"{D}/goat0/task.json"))
qtext = {q["q_index"]: q["query"].split("Question:")[-1].strip()[:200] for q in t["questions"]}
def mems(txt):
    out = []
    for m in re.split(r"\nMemory \d+:\n|^Memory \d+:\n", txt or ""):
        m = m.strip()
        if not m: continue
        src = re.search(r"\(source: chunk (-?\d+)\)", m)
        out.append(("trex" if src and src.group(1) == "-1" else "doc", m))
    return out
right = lambda r: r["substring_exact_match"] > 0
tot = {"trex": 0, "doc": 0}; n = 0
for q, r in g.items():
    if not right(r):
        for s, _ in mems(r["retrieved_text"]): tot[s] += 1
        n += 1
print("all failed GOAt questions:", n, "mean facts trex/doc:", round(tot["trex"]/n, 1), round(tot["doc"]/n, 1))
tot = {"trex": 0, "doc": 0}; k = 0
for q, r in g.items():
    if right(r):
        for s, _ in mems(r["retrieved_text"]): tot[s] += 1
        k += 1
print("right GOAt questions:", k, "mean facts trex/doc:", round(tot["trex"]/k, 1), round(tot["doc"]/k, 1))
pick = [q for q in sorted(g) if not right(g[q]) and right(a[q])]
print("wrong on T-REx but right on empty-start (repeat 0):", len(pick), pick)
out = []
for q in pick[:10]:
    r, ra = g[q], a[q]
    mg, ma = mems(r["retrieved_text"]), mems(ra["retrieved_text"])
    docg = {m for s, m in mg if s == "doc"}
    missing = [m for s, m in ma if s == "doc" and m not in docg]
    out.append({"q": q, "question": qtext[q], "gold": r["answers"], "pred_trex": r["prediction"].split("Answer:")[-1].strip()[:150],
                "pred_empty": ra["prediction"].split("Answer:")[-1].strip()[:150],
                "gold_in_trex_pool": r["answer_in_retrieved"], "gold_in_empty_pool": ra["answer_in_retrieved"],
                "n_trex": sum(s == "trex" for s, _ in mg), "n_doc": len(docg), "n_doc_empty": sum(s == "doc" for s, _ in ma),
                "doc_facts_lost": [m[:160] for m in missing],
                "trex_facts": [m[:260] for s, m in mg if s == "trex"],
                "doc_facts": [m[:160] for s, m in mg if s == "doc"],
                "chars_trex": sum(len(m) for s, m in mg if s == "trex"), "chars_doc": sum(len(m) for s, m in mg if s == "doc")})
json.dump(out, open(f"{D}/ten.json", "w"), indent=1)

# all 83 failed: wrong answer found in a T-REx fact but in no document fact; duplicate T-REx sentences
from_trex = only_doc = neither = dups = slots = 0
for q, r in g.items():
    if right(r): continue
    p = r["prediction"].split("Answer:")[-1].strip().strip(".").strip()
    ms = mems(r["retrieved_text"])
    tx = [re.sub(r"^arrival \d+\. ", "", m) for s, m in ms if s == "trex"]
    dups += len(tx) - len(set(tx)); slots += len(ms)
    if not p or len(p) > 60: neither += 1; continue
    in_t = any(p.lower() in m.lower() for m in tx); in_d = any(p.lower() in m.lower() for s, m in ms if s == "doc")
    if in_t and not in_d: from_trex += 1
    elif in_d: only_doc += 1
    else: neither += 1
print("failed 83: wrong answer only in T-REx facts", from_trex, "| in a document fact", only_doc, "| in neither (refusal / prior)", neither)
print("duplicate T-REx sentences:", dups, "of", slots, "slots")
