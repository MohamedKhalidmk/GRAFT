"""test-07 table and figure, from the runs only: runs/run-01 holds the 2026-11-13 mode C run (38), the same commit
rerun on 2026-11-21 and the replay of the 2026-11-13 facts; today's code is test 05 arm A (the 2026-11-21 rerun)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "docs" / "design" / "theme"))
import theme as T  # noqa: E402

RUNS = HERE / "runs" / "run-01"
ARMS = [("2026-11-13", "2026-11-13 run (mode C)", RUNS, "exp_c_real_mh_262k_ans256_2026*", T.STONE),
        ("2026-11-21", "The 2026-11-13 commit, today", RUNS, "exp_c_real_mh_262k_ans256_rerun28d4fd5_2*", T.NAVY),
        ("2026-11-21", "Today's code (test 05 arm A)", HERE.parent / "test-05-working-memory" / "runs" / "run-02",
         "exp_real_wm_empty_a_modec_rerun1121_2*", T.NAVY),
        ("2026-11-21", "Replay of the 2026-11-13 facts, today", RUNS, "exp_real_replay38_2*", T.NAVY)]
rows, bars = [], []
for day, what, base, pat, colour in ARMS:
    R = T.latest(base, pat)
    if not R:
        continue
    reps = T.score_runs([R])
    s = T.summarise(reps)
    rows.append({"date": day, "run": what, "repeats": s["repeats"], "accuracy_mean": s["accuracy_mean"],
                 "accuracy_sd": s["accuracy_sd"], "per_repeat": s["per_repeat"], "gold_in_final_facts": s["gold_in_final_facts"],
                 "mean_output_tokens": round(sum(r["out_tok"] for r in reps) / sum(r["n"] for r in reps), 1),
                 "cost_per_100_questions_usd": s["cost_per_100_questions_usd"], "folder": T.rel(R, HERE)})
    bars.append(T.bar(T.tag(what, R), [r["acc"] for r in reps], colour))

T.write_tables(HERE, rows)
T.bar_chart(HERE / "figure.png", "Test 07 · Haiku drift",
            "Mode C, 100 multi-hop questions · Claude Haiku 5.5 · % right",
            [{"title": None, "rows": bars}],
            legend=[(T.STONE, "2026-11-13"), (T.NAVY, "2026-11-21")], label_in=3.6,
            footnote="Identical prompts score about 34 today: only Haiku's answers changed. Compare methods within one day.")
