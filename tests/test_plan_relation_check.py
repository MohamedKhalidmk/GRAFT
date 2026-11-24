"""scripts/plan_relation_check.py: classifying LongMemEval misses by planned against stored relations. Offline."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("prc", Path(__file__).resolve().parent.parent / "scripts" / "plan_relation_check.py")
prc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prc)


def test_misses_are_classed_by_planned_against_stored_relation():
    """Checks that a miss is a relation-name mismatch only when no gold fact's mapped relation is one the plan wanted.
    Guards against: counting a miss as a naming problem when the names matched and the plan failed for another reason."""
    plan = {"edges": [["user", "employer", "?A"]], "want": ["employer"]}
    assert prc.classify(plan, [("works at", "employer")]) == "relation matches"
    assert prc.classify(plan, [("job title", "position held"), ("based in", None)]) == "relation-name mismatch"
    assert prc.classify({"reason": "no parse"}, [("works at", "employer")]) == "no plan"


def test_gold_found_in_facts_by_words():
    """Checks that the gold string is found in a fact's subject, relation, object or sentence, golds up to 40 characters.
    Guards against: a gold fact in the graph being missed because of case or punctuation, or long golds matched loosely."""
    facts = [{"subject": "user", "relation": "works at", "object": "Acme, Inc.", "provenance": {"span": "I work at Acme."}},
             {"subject": "user", "relation": "likes", "object": "tea"}]
    assert prc.gold_facts(facts, prc.short_gold("acme")) == facts[:1]
    assert prc.short_gold("x" * 41) is None
