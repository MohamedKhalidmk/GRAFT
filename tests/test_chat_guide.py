"""Chat guide input (G44): Dialogue NLI triples -> facts for scripts/trex_guide.py --triples. Offline, toy data."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_dnli_triples_keeps_clean_sentences_and_types(tmp_path):
    d = tmp_path / "dnli"
    (d / "dialogue_nli").mkdir(parents=True)
    (d / "dialogue_nli_extra").mkdir()
    schema = {"relation_types": [{"hierarchy_type": "Possessions", "display": "Possessions",
                                  "types": [{"type": "have_pet", "display": "Has Pet"}]},
                                 {"hierarchy_type": "Location", "display": "Location",
                                  "types": [{"type": "nationality", "display": "Nationality"}]}],
              "e2_constraints": {"nationality": ["country"], "have_pet": ["animal", "other"]}}
    (d / "dialogue_nli_extra" / "schema.json").write_text(json.dumps(schema))
    rows = [{"sentence1": "i have a dog .", "sentence2": "my dad is from france .", "triple1": ["i", "have_pet", "dog"],
             "triple2": ["my father", "nationality", "France"], "label": "neutral"},
            {"sentence1": "leaky sentence .", "sentence2": "x .", "triple1": ["i", "have_pet", "cat"], "triple2": ["i", "<none>", "x"]}]
    for split in ("train", "dev", "test", "verified_test"):
        (d / "dialogue_nli" / f"dialogue_nli_{split}.jsonl").write_text(json.dumps(rows if split == "train" else []))
    clean = tmp_path / "clean.jsonl"
    clean.write_text("\n".join(json.dumps({"task": s}) for s in ("i have a dog .", "my dad is from france .", "x .")) + "\n")
    out = tmp_path / "t.jsonl"
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "dnli_triples.py"), "--dnli", str(d), "--clean", str(clean),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    lines = [tuple(json.loads(l)) for l in open(out)]
    assert ("user", "has pet", "dog") in lines and ("my father", "nationality", "france") in lines
    assert ("user", "has pet", "cat") not in lines                       # its sentence failed the leakage check
    assert ("france", "instance of", "country") in lines and ("dog", "instance of", "possessions") in lines
    assert ("user", "instance of", "person") in lines and ("my father", "instance of", "family member") in lines
    s = json.loads(r.stdout.strip().splitlines()[-1])
    assert s["dropped_by_leakage"] == 1 and s["triples"] == 2
