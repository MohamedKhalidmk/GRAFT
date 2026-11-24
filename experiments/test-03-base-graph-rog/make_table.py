"""test-03 table and figure, from the runs only: runs/run-01 holds the paid run (Haiku links the documents onto the
20,000-fact RoG base, then one answer pass, 256 tokens) and its free check (same graph, fake answerer).
Reference: mode C on the empty-start graph, test 01 run-02 (2026-11-13), as in the README."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "docs" / "design" / "theme"))
import theme as T  # noqa: E402

RUNS = HERE / "runs" / "run-01"
ARMS = [("reference", "Mode C, empty-start graph (test 01, 2026-11-13)", HERE.parent / "test-01-read-order" / "runs" / "run-02",
         "exp_c_real_mh_262k_ans256_2*", T.NAVY),
        ("paid", "Mode C (EiG) + RoG base, Haiku linking", RUNS, "exp_c_real_mh_262k_ans256_rog_link_build_eig_2*", T.STONE),
        ("free check", "Same graph, fake answerer", RUNS, "exp_c_fake_mh_262k_rog_link_eig_2*", T.STONE)]
rows, acc, gold = [], [], []
for kind, what, base, pat, colour in ARMS:
    R = T.latest(base, pat)
    if not R:
        continue
    reps = T.score_runs([R])
    s = T.summarise(reps)
    fake = json.load(open(Path(R) / "summary.json"))["llm_mode"] == "fake"
    rows.append({"kind": kind, "variant": what, "repeats": s["repeats"], "accuracy_mean": "" if fake else s["accuracy_mean"],
                 "per_repeat": "" if fake else s["per_repeat"], "gold_in_final_facts": s["gold_in_final_facts"],
                 "cost_per_100_questions_usd": s["cost_per_100_questions_usd"], "run": T.rel(R, HERE)})
    if not fake:
        acc.append(T.bar(T.tag(what, R), [r["acc"] for r in reps], colour))
    gold.append(T.bar(T.tag(what, R), [r["gold"] for r in reps], colour))

T.write_tables(HERE, rows)
T.bar_chart(HERE / "figure.png", "Test 03 · Base graph from RoG (Freebase)",
            "Claude Haiku 5.5 · 100 multi-hop questions · 256-token answers",
            [{"title": "% right", "rows": acc}, {"title": "% of questions whose gold fact reached the model", "rows": gold}],
            legend=[T.NAVY, T.STONE], label_in=3.6,
            footnote="Not adopted: the small off-domain base mostly adds hub noise to PageRank. The RoG run cost $1.65 with the write phase.")
