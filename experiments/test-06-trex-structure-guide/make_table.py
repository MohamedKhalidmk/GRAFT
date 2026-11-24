"""test-06 table, from the runs only (runs/run-NN/exp_real_tg_<arm>_*/repeat_*/scored.jsonl), with arm A from test 05.
Qwen rows (exp_qwen_empty_b_guide_* here, arm A from test 05's exp_qwen_empty_a_modec_*) appear once those runs exist.
Also draws figure.png in the shared theme (docs/design/theme/theme.py)."""
import csv, glob, json, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "docs" / "design" / "theme"))
import theme as T  # noqa: E402

T05 = HERE.parent / "test-05-working-memory" / "runs"
ARMS = [("Haiku", "A", "mode C, empty start (test 05 rerun, run-01)", [T05 / "run-02"], "exp_real_wm_empty_a_modec_rerun1121_2*"),
        ("Haiku", "B", "the T-REx structure guide (run-01)", [HERE / "runs" / "run-01"], "exp_real_tg_b_guide_2*"),
        ("Haiku", "C", "T-REx as a bridge, walk only (run-01)", [HERE / "runs" / "run-01"], "exp_real_tg_c_bridge_2*"),
        ("Haiku", "D", "bridge + 5 labelled background facts (run-01)", [HERE / "runs" / "run-01"], "exp_real_tg_d_background_2*"),
        ("Haiku", "A (run-02)", "mode C, same day as G35 (run-02)", [HERE / "runs" / "run-02"], "exp_real_tg_a_sameday_2*"),
        ("Haiku", "B (run-02)", "the guide, same day as G08 (run-02)", [HERE / "runs" / "run-02"], "exp_real_tg_b_guide_sameday_2*"),
        ("Haiku", "E (run-03)", "guide + working memory, same day as G35 (run-03)", [HERE / "runs" / "run-03"], "exp_real_tg_e_guide_wm_v2_2*"),
        ("Haiku", "B (run-03)", "the guide alone, same day as G38 (run-03)", [HERE / "runs" / "run-03"], "exp_real_tg_b_guide_sameday2_2*"),
        ("Qwen", "A", "empty start, mode C (test 05)", sorted(T05.glob("run-*")), "exp_qwen_empty_a_modec_2*"),
        ("Qwen", "B", "T-REx as a structure guide (linking + planning)", sorted((HERE / "runs").glob("run-*")), "exp_qwen_empty_b_guide_2*")]
rows, accs = [], []
for model, arm, what, dirs, pat in ARMS:
    runs = sorted(h for d in dirs for h in glob.glob(str(d / pat)))
    if not runs:
        continue
    acc, gold, cost = [], [], 0.0
    for p in sorted(glob.glob(runs[-1] + "/repeat_*/scored.jsonl")):
        sc = [json.loads(l) for l in open(p)]
        acc.append(100 * sum(s["substring_exact_match"] > 0 for s in sc) / len(sc))
        gold.append(100 * sum(bool(s["answer_in_retrieved"]) for s in sc) / len(sc))
        cost += sum(s.get("cost_usd", 0) for s in sc)
    if not acc:
        continue
    accs.append(acc)
    rows.append({"candidate": T.ids(runs[-1])[0], "setup": T.ids(runs[-1])[1], "model": model, "arm": arm, "what": what, "repeats": len(acc), "accuracy_mean": round(statistics.mean(acc), 1),
                 "accuracy_sd": round(statistics.stdev(acc), 1) if len(acc) > 1 else 0, "per_repeat": " / ".join(f"{a:.0f}" for a in acc),
                 "gold_in_final_facts": round(statistics.mean(gold), 1), "cost_per_100_questions_usd": round(cost / len(acc), 3)})
with open(HERE / "table.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
md = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])] + ["| " + " | ".join(str(v) for v in r.values()) + " |" for r in rows]
(HERE / "table.md").write_text("\n".join(md) + "\n")
print("\n".join(md))

COLOUR = {"G08": T.NAVY, "G35": T.GREEN, "G38": T.YELLOW}
panels = []
for model in ("Haiku", "Qwen"):
    bars = [T.bar(f"{r['candidate']} · {r['what']}", a, COLOUR.get(r["candidate"], T.STONE)) for r, a in zip(rows, accs) if r["model"] == model]
    if bars:
        panels.append({"title": f"{model}: % right", "rows": bars})
T.bar_chart(HERE / "figure.png", "Test 06 · T-REx as a structure guide",
            "100 multi-hop questions · 3 repeats per arm · no T-REx fact reaches the answering model as a memory",
            panels, legend=[T.NAVY, T.GREEN, (T.YELLOW, "parked, not dropped"), T.STONE], label_in=4.4,
            footnote="G35 (the guide) kept on Haiku: 45.7 vs 34.7. G36 and G37 not adopted. G38 parked, not dropped.")
