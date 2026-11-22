"""test-02 table and figure, from the runs only (runs/run-01, Fir, 2026-11-19/20).

Paid runs (real Haiku answers, 256 tokens): every folder of the same variant counts as one repeat.
Free checks (llm_mode fake: no real answers, so only "gold reached the model" means anything).
Reference rows come from test 01 run-02 (same graph and questions, 2026-11-13)."""
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "docs" / "design" / "theme"))
import theme as T  # noqa: E402

RUNS = HERE / "runs" / "run-01"
T01 = HERE.parent / "test-01-read-order" / "runs" / "run-02"
PAID = [("ref_c", "Mode C with GOAt, 2026-11-13 (test 01)", T01, "exp_c_real_mh_262k_ans256_2*", T.NAVY),
        ("ref_a", "Mode A with GOAt, 2026-11-13 (test 01)", T01, "exp_a_real_mh_262k_ans256_2*", T.STONE),
        ("a_eig", "Mode A, EiG instead of GOAt", RUNS, "exp_a_real_mh_262k_ans256_eig_2*", T.STONE),
        ("hybrid_goat", "50/50 hybrid with embedding search, GOAt", RUNS, "exp_c_real_mh_262k_ans256_hybrid_goat_2*", T.STONE),
        ("hybrid_eig", "50/50 hybrid with embedding search, EiG", RUNS, "exp_c_real_mh_262k_ans256_hybrid_eig_2*", T.STONE),
        ("topk10_eig", "Top-10 hybrid, EiG", RUNS, "exp_c_real_mh_262k_ans256_topk10_eig_2*", T.STONE),
        ("qgraph_eig", "Question graph (Haiku parses the question), EiG", RUNS, "exp_c_real_mh_262k_ans256_qgraph_eig_2*", T.STONE)]
FREE = OrderedDict([
    ("c_fake_mh_262k_base_eig", "Mode C, EiG (free-check baseline)"),
    ("a_fake_mh_262k_eig_check", "Mode A, EiG"),
    ("c_fake_mh_262k_link_eig", "Embedding entity linking (k=5), EiG"),
    ("c_fake_mh_262k_link_goat", "Embedding entity linking (k=5), GOAt"),
    ("c_fake_mh_262k_both_eig", "Linking + hybrid, EiG"),
    ("c_fake_mh_262k_both_goat", "Linking + hybrid, GOAt"),
    ("c_fake_mh_262k_hybrid_eig", "50/50 hybrid, EiG"),
    ("c_fake_mh_262k_hybrid_goat", "50/50 hybrid, GOAt"),
    ("c_fake_mh_262k_hybrid_eig_src", "50/50 hybrid with sources, EiG"),
    ("c_fake_mh_262k_hybrid_goat_src", "50/50 hybrid with sources, GOAt"),
    ("c_fake_mh_262k_hybrid_eig_n400", "50/50 hybrid, 400-node subgraph"),
    ("c_fake_mh_262k_hybrid_eig_n800", "50/50 hybrid, 800-node subgraph"),
    ("c_fake_mh_262k_hybrid_eig_n1600", "50/50 hybrid, 1,600-node subgraph"),
    ("c_fake_mh_262k_topk5_eig", "Top-5 hybrid, EiG"),
    ("c_fake_mh_262k_topk10_eig", "Top-10 hybrid, EiG"),
    ("c_fake_mh_262k_qgraph_eig", "Question graph, EiG"),
    ("c_fake_mh_262k_gnn1600_eig", "Bigger subgraphs, 1,600-node GNN"),
    ("embed_fake_mh_262k", "Embedding search only (no graph)")])


def complete(run_dirs):
    """Drop folders that never finished (no summary.json), e.g. a killed first try."""
    return [r for r in run_dirs if (Path(r) / "summary.json").exists()]


rows, acc_bars, gold_bars = [], [], []
for key, what, base, pat, colour in PAID:
    R = complete(T.all_runs(base, pat))
    if not R:
        continue
    reps = T.score_runs(R)
    s = T.summarise(reps)
    rows.append({"kind": "reference" if key.startswith("ref") else "paid", "variant": what, "repeats": s["repeats"],
                 "accuracy_mean": s["accuracy_mean"], "accuracy_sd": s["accuracy_sd"], "per_repeat": s["per_repeat"],
                 "gold_in_final_facts": s["gold_in_final_facts"], "cost_per_100_questions_usd": s["cost_per_100_questions_usd"],
                 "run": "; ".join(T.rel(r, HERE) for r in R)})
    acc_bars.append(T.bar(T.tag(what, R), [r["acc"] for r in reps], colour))
for key, what in FREE.items():
    R = complete(T.all_runs(RUNS, f"exp_{key}_2*"))
    if not R:
        continue
    assert all(json.load(open(Path(r) / "summary.json"))["llm_mode"] == "fake" for r in R)
    reps = T.score_runs(R)
    gold = [r["gold"] for r in reps]
    rows.append({"kind": "free check", "variant": what, "repeats": len(reps), "accuracy_mean": "", "accuracy_sd": "",
                 "per_repeat": "", "gold_in_final_facts": round(sum(gold) / len(gold), 1), "cost_per_100_questions_usd": 0,
                 "run": "; ".join(T.rel(r, HERE) for r in R)})
    gold_bars.append(T.bar(T.tag(what, R), gold, T.NAVY if "baseline" in what else T.STONE))

T.write_tables(HERE, rows)
T.bar_chart(HERE / "figure.png", "Test 02 · Retrieval variants on mode C",
            "Claude Haiku 5.5 · 100 multi-hop questions · nothing beat mode C with GOAt",
            [{"title": "Paid runs: % right (256-token answers)", "rows": acc_bars},
             {"title": "Free checks: % of questions whose gold fact reached the model", "rows": gold_bars, "one_run_note": False}],
            legend=[T.NAVY, T.STONE], label_in=3.6,
            footnote="Free checks (one run each) use a fake answerer, so only retrieval counts. Each paid hybrid repeat is its own run folder.")
