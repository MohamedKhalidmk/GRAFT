"""T-REx structure guide (my_method/guide.py) on a toy graph: relation mapping adds missed revisions, same-entity merges
need agreeing types, and planning follows the chain (bridging a hop the documents spell differently)."""
import json

from baselines.claude_gateway.embeddings import HashEmbedder
from my_method.gnn.features import TextEmbedder
from my_method.graph_store import GraphStore, Provenance, entity_id
from my_method.guide import Guide

CIT, CONT, POS, SPORT = "country of citizenship", "continent", "position played on team / speciality", "sport"
LABELS = {"is a citizen of": CIT, "citizenship": CIT, "is located in the continent of": CONT,
          "plays the position of": POS, "is associated with the sport of": SPORT}


def guide(tmp_path):
    g = {"chains": {CIT: [[CONT, 50]], CONT: [], POS: [[SPORT, 80]], SPORT: []},
         "functional": {CIT: 0.9, CONT: 0.95, POS: 0.7, SPORT: 0.8},
         "signature": {CIT: {"subject": [["human", 9]], "object": [["country", 9]]},
                       CONT: {"subject": [["country", 9]], "object": [["continent", 9]]},
                       POS: {"subject": [["human", 9]], "object": [["position", 9]]},
                       SPORT: {"subject": [["position", 9]], "object": [["sport", 9]]}},
         "name_types": {"Beatles": ["band"], "The Beatles": ["band"], "Mercury": ["planet"], "The Mercury": ["newspaper"]},
         "doc_relations": {lab: {"relation": r, "cosine": 0.95, "facts": 1} for lab, r in LABELS.items()}}
    p = tmp_path / "guide.json"
    p.write_text(json.dumps(g))
    return Guide(p, TextEmbedder(HashEmbedder()))


def add(s, h, r, o, serial):
    return s.add_fact(h, r, o, Provenance(0, s.take_arrival(), serial, f"{serial}. {h} {r} {o}."))


def test_link_pass(tmp_path):
    """Checks that the guide's link pass adds a revision missed across relation spellings and merges same-entity names only when their types agree.
    Guards against: an old citizenship shown as current because two spellings of one relation hid the revision, or a planet merged with a newspaper."""
    s = GraphStore()
    old = add(s, "Ann", "is a citizen of", "Peru", 5)
    new = add(s, "Ann", "citizenship", "Chile", 9)
    add(s, "The Beatles", "genre", "rock", 1)
    add(s, "Beatles", "genre", "pop", 2)
    add(s, "Mercury", "orbits", "Sun", 3)
    add(s, "The Mercury", "publisher", "Fairfax", 4)
    log = guide(tmp_path).link_pass(s)
    assert s.current(old) == new and log["revisions_added"] == 1
    assert log["entities_merged"] == 1 and (entity_id("Beatles") in s.g) != (entity_id("The Beatles") in s.g)
    assert log["merges_refused_count"] == 1  # planet vs newspaper


def test_plan_direct_and_bridged(tmp_path):
    """Checks that planning follows a chain of direct facts, and bridges a hop through the document relation when no fact has the planned one.
    Guards against: a multi-hop question failing because the documents spell a relation differently from the planned T-REx relation."""
    s = GraphStore()
    f1 = add(s, "Ann", "is a citizen of", "Finland", 3)
    f2 = add(s, "Finland", "is located in the continent of", "Asia", 4)
    g1 = add(s, "Bob", "plays the position of", "cornerback", 5)
    g2 = add(s, "cornerback", "is associated with the sport of", "hockey", 6)
    gd = guide(tmp_path)
    chain, log = gd.plan(s, [("Ann", CIT, "?A"), ("?A", CONT, "?B")], [])
    assert chain == [f1, f2] and [x["how"] for x in log["steps"]] == ["direct", "direct"]
    chain, log = gd.plan(s, [("Bob", SPORT, "?A")], [])
    assert chain == [g1, g2] and log["steps"][0]["how"] == "bridged"
