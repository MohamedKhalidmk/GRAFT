"""test-05 table, from the runs only: per arm, accuracy over repeats (substring exact match), gold fact in the final
facts, LLM calls, tokens and cost per question. Reads runs/run-NN/exp_wm_empty_<arm>_*/ (Haiku) and exp_qwen_empty_<arm>_*/ (Qwen) repeat_*/scored.jsonl.
Also draws figure.png in the shared theme (docs/design/theme/theme.py); Qwen rows appear once their runs are here."""
import csv, glob, json, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "docs" / "design" / "theme"))
import theme as T  # noqa: E402
ARMS = [("a_modec", "A", "mode C, one answer call"), ("b_qlayer", "B", "question layer"),
        ("c_wm_graph", "C", "working memory in the graph"), ("cm_wm_prompt", "C-", "same steps, prompt only"),
        ("c_wm_graph_v2", "C v2", "C, step prompt with the newer-fact rule"), ("cm_wm_prompt_v2", "C- v2", "C-, same prompt"),
        ("a_modec_rerun1121", "A", "mode C, rerun the same day as round 2")]
rows, per_rep_acc, per_rep_gold = [], [], []
for model, prefix in [("Haiku", "exp_wm_empty"), ("Haiku", "exp_real_wm_empty"), ("Qwen", "exp_qwen_empty")]:
  for key, arm, what in ARMS:
      runs = sorted(glob.glob(str(HERE / "runs" / "run-*" / f"{prefix}_{key}_2*")))
      if not runs:
          continue
      R = runs[-1]
      acc, gold, calls, cost, tin, tout = [], [], 0, 0.0, 0, 0
      reps = sorted(glob.glob(R + "/repeat_*/scored.jsonl"))
      for p in reps:
          sc = [json.loads(l) for l in open(p)]
          acc.append(100 * sum(s["substring_exact_match"] > 0 for s in sc) / len(sc))
          gold.append(100 * sum(bool(s["answer_in_retrieved"]) for s in sc) / len(sc))
          calls += sum(s.get("llm_calls", 0) for s in sc); cost += sum(s.get("cost_usd", 0) for s in sc)
          tin += sum(s.get("input_tokens", 0) for s in sc); tout += sum(s.get("output_tokens", 0) for s in sc)
      n = 100 * len(reps)
      per_rep_acc.append(acc); per_rep_gold.append(gold)
      rows.append({"candidate": T.ids(R)[0], "setup": T.ids(R)[1], "model": model, "arm": arm, "what": what, "repeats": len(reps), "accuracy_mean": round(statistics.mean(acc), 1),
                   "accuracy_sd": round(statistics.stdev(acc), 1) if len(acc) > 1 else 0, "per_repeat": " / ".join(f"{a:.0f}" for a in acc),
                   "gold_in_final_facts": round(statistics.mean(gold), 1), "calls_per_question": round(calls / n, 2),
                   "input_tokens_per_question": round(tin / n), "output_tokens_per_question": round(tout / n),
                   "cost_per_100_questions_usd": round(cost / len(reps), 3), "run": str(Path(R).relative_to(HERE))})
with open(HERE / "table.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
md = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])] + ["| " + " | ".join(str(v) for v in r.values()) + " |" for r in rows]
(HERE / "table.md").write_text("\n".join(md) + "\n")
print("\n".join(md))

# figure: Haiku round 1, round 2, then Qwen (if any)
COLOUR = {"A": T.NAVY, "C": T.YELLOW, "C v2": T.YELLOW}
panels = []
for title, keep in [("Haiku, round 1 (2026-11-20)", lambda r: r["model"] == "Haiku" and "run-01" in r["run"]),
                    ("Haiku, round 2 (2026-11-21, same day)", lambda r: r["model"] == "Haiku" and "run-02" in r["run"]),
                    ("Qwen", lambda r: r["model"] == "Qwen")]:
    bars = [T.bar(f"{r['candidate']} · {r['what']}", a, COLOUR.get(r["arm"], T.STONE)) for r, a in zip(rows, per_rep_acc) if keep(r)]
    if bars:
        panels.append({"title": title + ": % right", "rows": bars})
T.bar_chart(HERE / "figure.png", "Test 05 · Working memory in the graph",
            "100 multi-hop questions · 3 repeats per arm · compare arms only within a round",
            panels, legend=[T.NAVY, T.YELLOW, T.STONE], label_in=4.2,
            footnote="Not kept on Haiku: C is about 1 point over A, inside the spread, at three times the cost.")
