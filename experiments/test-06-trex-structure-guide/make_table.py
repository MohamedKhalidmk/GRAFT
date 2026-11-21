"""test-06 table, from the runs only (runs/run-NN/exp_real_tg_<arm>_*/repeat_*/scored.jsonl), with arm A from test 05."""
import csv, glob, json, statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = [("A", "empty start, mode C (test 05, rerun the same day)", HERE.parent / "test-05-working-memory" / "runs" / "run-02", "exp_real_wm_empty_a_modec_rerun1121_2*"),
        ("B", "T-REx as a structure guide (linking + planning)", HERE / "runs" / "run-01", "exp_real_tg_b_guide_2*"),
        ("C", "T-REx as a bridge (walk only, weight 0.2)", HERE / "runs" / "run-01", "exp_real_tg_c_bridge_2*"),
        ("D", "C + 5 labelled background facts", HERE / "runs" / "run-01", "exp_real_tg_d_background_2*")]
rows = []
for arm, what, d, pat in ARMS:
    runs = sorted(glob.glob(str(d / pat)))
    if not runs:
        continue
    acc, gold, cost = [], [], 0.0
    for p in sorted(glob.glob(runs[-1] + "/repeat_*/scored.jsonl")):
        sc = [json.loads(l) for l in open(p)]
        acc.append(100 * sum(s["substring_exact_match"] > 0 for s in sc) / len(sc))
        gold.append(100 * sum(bool(s["answer_in_retrieved"]) for s in sc) / len(sc))
        cost += sum(s.get("cost_usd", 0) for s in sc)
    rows.append({"arm": arm, "what": what, "repeats": len(acc), "accuracy_mean": round(statistics.mean(acc), 1),
                 "accuracy_sd": round(statistics.stdev(acc), 1), "per_repeat": " / ".join(f"{a:.0f}" for a in acc),
                 "gold_in_final_facts": round(statistics.mean(gold), 1), "cost_per_100_questions_usd": round(cost / len(acc), 3)})
with open(HERE / "table.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
md = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])] + ["| " + " | ".join(str(v) for v in r.values()) + " |" for r in rows]
(HERE / "table.md").write_text("\n".join(md) + "\n")
print("\n".join(md))
