# Sources: mquake, wikidata (docs/reference/REFERENCES.md)
"""Build my_method/fc_relations.json: the 37 relation sentence templates FactConsolidation uses.

FactConsolidation's facts are MQuAKE-CF's cloze templates filled with a subject and an object
(e.g. "{} is a citizen of" + "Germany"). This script reads the templates and their Wikidata labels
from MQuAKE-CF so nothing is typed by hand. Only relation *templates* are kept: no facts, entities
or questions, so nothing about the test answers reaches GRAFT.

Used by the rule-based writer (an ablation and the fake-LLM extractor) and the synthetic GNN
training-data generator.

    python -m data.build_fc_relations
"""

import json
import urllib.request
from pathlib import Path

MQUAKE_CF = "https://raw.githubusercontent.com/princeton-nlp/MQuAKE/main/datasets/MQuAKE-CF.json"
OUT = Path(__file__).resolve().parent.parent / "my_method" / "fc_relations.json"


def main() -> None:
    cases = json.loads(urllib.request.urlopen(MQUAKE_CF, timeout=120).read())
    templates: dict[str, str] = {}
    labels: dict[str, str] = {}
    for case in cases:
        for rewrite in case["requested_rewrite"]:
            templates[rewrite["relation_id"]] = rewrite["prompt"]
        for ids, labelled in zip(case["orig"]["triples"], case["orig"]["triples_labeled"]):
            labels[ids[1]] = labelled[1]
    relations = [{"id": rid, "label": labels.get(rid, rid), "template": templates[rid]}
                 for rid in sorted(templates, key=lambda r: int(r[1:]))]
    OUT.write_text(json.dumps(relations, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(relations)} relations to {OUT}")


if __name__ == "__main__":
    main()
