"""test-04 table and figure, from the runs only. run-01: first answer passes, all 0.0 (PageRank stopped after one step:
not results, listed so the table matches the folder). run-02: fixed PageRank, original graph, Haiku, mode C, 256 tokens.
Reference: test 05 arm A (mode C, empty-start graph, run-01), as in the README."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "docs" / "design" / "theme"))
import theme as T  # noqa: E402

R1, R2 = HERE / "runs" / "run-01", HERE / "runs" / "run-02"
ARMS = [("run-02", "EiG", "Mode C, EiG", R2, "exp_c_real_mh_262k_ans256_trexfull_eig_pprfix_2*", T.STONE),
        ("run-02", "GOAt", "Mode C, GOAt (2 of 3 repeats: job time limit)", R2, "exp_c_real_mh_262k_ans256_trexfull_goat_pprfix_2*", T.STONE),
        ("run-02", "Question layer + EiG", "Question layer + EiG", R2, "exp_c_real_mh_262k_ans256_trexfull_qgraph_eig_pprfix_2*", T.STONE),
        ("reference", "Empty start (test 05 arm A)", "Mode C, GOAt, empty-start graph (test 05 arm A)",
         HERE.parent / "test-05-working-memory" / "runs" / "run-01", "exp_wm_empty_a_modec_2*", T.NAVY),
        ("run-01", "EiG (with build)", "PageRank bug: not results", R1, "exp_c_real_mh_262k_ans256_trexfull_link_build_eig_2*", T.RED),
        ("run-01", "GOAt", "PageRank bug: not results", R1, "exp_c_real_mh_262k_ans256_trexfull_goat_2*", T.RED),
        ("run-01", "Question layer + EiG", "PageRank bug: not results", R1, "exp_c_real_mh_262k_ans256_trexfull_qgraph_eig_2*", T.RED)]
rows, acc, gold = [], [], []
for run, name, what, base, pat, colour in ARMS:
    R = T.latest(base, pat)
    if not R:
        continue
    reps = T.score_runs([R])
    s = T.summarise(reps)
    rows.append({"run": run, "pass": name, "what": what, "repeats": s["repeats"], "accuracy_mean": s["accuracy_mean"],
                 "accuracy_sd": s["accuracy_sd"], "per_repeat": s["per_repeat"], "gold_in_final_facts": s["gold_in_final_facts"],
                 "cost_per_100_questions_usd": s["cost_per_100_questions_usd"], "folder": T.rel(R, HERE)})
    if run == "run-01":
        continue
    label = what if run == "reference" else f"T-REx base · {what}"
    acc.append(T.bar(label, [r["acc"] for r in reps], colour))
    gold.append(T.bar(label, [r["gold"] for r in reps], colour))

T.write_tables(HERE, rows)
T.bar_chart(HERE / "figure.png", "Test 04 · Base graph from full T-REx (Wikidata)",
            "Claude Haiku 5.5 · 100 multi-hop questions · 1.2M-fact base under the documents (run-02)",
            [{"title": "% right", "rows": acc}, {"title": "% of questions whose gold fact reached the model", "rows": gold}],
            legend=[T.NAVY, T.STONE], label_in=4.3,
            footnote="Not adopted: the base halves accuracy. run-01 (all 0.0, a PageRank bug) is in table.csv only.")
