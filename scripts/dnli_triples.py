"""Chat guide, step 1 (G44, docs/design/graft_longmemeval_plan_design.md): Dialogue NLI's labelled triples as a
facts file for scripts/trex_guide.py --triples. No LLM, CPU.

    python scripts/dnli_triples.py --dnli RAW/dnli --clean UNITS.clean.jsonl --out dnli_triples.jsonl

Dialogue NLI (Welleck et al., ACL 2019; PersonaChat sentences, each with a human-labelled (subject, relation, object)
triple about a speaker) gives the chat guide what T-REx gives the T-REx guide: relation labels, coarse types, and which
relations connect. Kept: only triples whose sentence passed the leakage check (--clean: units.clean.jsonl from
flotilla.leakage against LongMemEval and every test set). Relations get the schema's display labels ("has pet");
the speaker "i" becomes "user" (the name GRAFT's chat writer gives the person), other subjects ("my father") are typed
"family member"; objects get the schema's entity type for that relation, else the relation's group. Each typing is an
"instance of" line, which trex_guide.py reads as T-REx's.
"""
import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dnli", required=True, help="the unpacked dnli folder (dialogue_nli/, dialogue_nli_extra/schema.json)")
    ap.add_argument("--clean", required=True, help="units.clean.jsonl: sentences that passed the leakage check")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = Path(a.dnli)
    schema = json.loads((d / "dialogue_nli_extra" / "schema.json").read_text())
    label, group = {}, {}
    for h in schema["relation_types"]:
        for t in h["types"]:
            label[t["type"]] = t["display"].lower().replace("/", " or ")
            group[t["type"]] = h["display"].lower()
    e2 = schema.get("e2_constraints", {})
    clean = {json.loads(l)["task"] for l in open(a.clean)}
    triples, typed, dropped, skipped = set(), set(), 0, Counter()
    for split in ("train", "dev", "test", "verified_test"):
        for r in json.loads((d / "dialogue_nli" / f"dialogue_nli_{split}.jsonl").read_text()):
            for sk, tk in (("sentence1", "triple1"), ("sentence2", "triple2")):
                t = r.get(tk)
                if not t or len(t) != 3:
                    continue
                s, rel, o = (str(x).strip() for x in t)
                if rel not in label or not s or not o:
                    skipped[rel] += 1
                    continue
                if r[sk].strip() not in clean:
                    dropped += 1
                    continue
                subj = "user" if s.lower() in ("i", "me", "my") else s.lower()
                triples.add((subj, label[rel], o.lower()))
                typed.add((subj, "person" if subj == "user" else "family member"))
                cons = e2.get(rel) or []
                otype = cons[0] if len(cons) == 1 and cons[0] != "other" else group[rel]
                typed.add((o.lower(), otype))
    with open(a.out, "w") as f:
        for s, r, o in sorted(triples):
            f.write(json.dumps([s, r, o]) + "\n")
        for e, t in sorted(typed):
            f.write(json.dumps([e, "instance of", t]) + "\n")
    print(json.dumps({"triples": len(triples), "typings": len(typed), "relations": len({r for _, r, _ in triples}),
                      "dropped_by_leakage": dropped, "skipped_relations": dict(skipped.most_common(5))}))


if __name__ == "__main__":
    main()
