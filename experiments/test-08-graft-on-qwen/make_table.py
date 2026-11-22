"""test-08 table, from the runs only: GRAFT with Qwen3.8-27B (W4A16, local vLLM) answering instead of Haiku.
Reads runs/run-NN/exp_qwen_empty_<arm>_*/repeat_*/scored.jsonl. Compare arms only within one run (same day, same job).
Also draws figure.png in the shared theme (docs/design/theme/theme.py)."""
import csv, glob, json, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "docs" / "design" / "theme"))
import theme as T  # noqa: E402

# (run, arm, what, run-name pattern)
ARMS = [("run-01", "A", "mode C, empty start", "exp_qwen_empty_a_modec_2*"),
        ("run-01", "B", "the T-REx structure guide", "exp_qwen_empty_b_guide_2*"),
        ("run-01", "C v2", "working memory in the graph", "exp_qwen_empty_c_wm_graph_v2_2*"),
        ("run-01", "C- v2", "same steps, prompt only", "exp_qwen_empty_cm_wm_prompt_v2_2*"),
        ("run-02", "B", "the guide alone, same day as E", "exp_qwen_empty_b_guide_sameday_2*"),
        ("run-02", "E", "the guide + working memory (C v2)", "exp_qwen_empty_e_guide_wm_v2_2*")]
rows, accs = [], []
for run, arm, what, pat in ARMS:
    runs = sorted(glob.glob(str(HERE / "runs" / run / pat)))
    if not runs:
        continue
    R = runs[-1]
    reps = sorted(glob.glob(R + "/repeat_*/scored.jsonl"))
    acc, gold, cut, calls, tout = [], [], 0, 0, 0
    for p in reps:
        sc = [json.loads(l) for l in open(p)]
        acc.append(100 * sum(s["substring_exact_match"] > 0 for s in sc) / len(sc))
        gold.append(100 * sum(bool(s["answer_in_retrieved"]) for s in sc) / len(sc))
        cut += sum(s.get("stop_reason") in ("max_tokens", "length") for s in sc)
        calls += sum(s.get("llm_calls", 0) for s in sc); tout += sum(s.get("output_tokens", 0) for s in sc)
    if not acc:
        continue
    n = 100 * len(reps)
    accs.append(acc)
    rows.append({"candidate": T.ids(R)[0], "setup": T.ids(R)[1], "run": run, "arm": arm, "what": what, "repeats": len(acc), "accuracy_mean": round(statistics.mean(acc), 1),
                 "accuracy_sd": round(statistics.stdev(acc), 1) if len(acc) > 1 else 0,
                 "per_repeat": " / ".join(f"{a:.0f}" for a in acc), "gold_in_final_facts": round(statistics.mean(gold), 1),
                 "answers_cut_at_256_tokens_pct": round(100 * cut / n, 1), "calls_per_question": round(calls / n, 2),
                 "output_tokens_per_question": round(tout / n), "folder": str(Path(R).relative_to(HERE))})
with open(HERE / "table.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
cols = [c for c in rows[0] if c != "folder"]
md = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows]
(HERE / "table.md").write_text("\n".join(md) + "\n")
print("\n".join(md))

COLOUR = {"A": T.NAVY, "B": T.GREEN, "E": T.YELLOW}
panels = []
for run, title in [("run-01", "Qwen, run-01 (2026-11-21)"), ("run-02", "Qwen, run-02 (same day: E vs B)")]:
    bars = [T.bar(f"{r['candidate']} · {r['what']}", a, COLOUR.get(r["arm"], T.STONE)) for r, a in zip(rows, accs) if r["run"] == run]
    if bars:
        panels.append({"title": title + ": % right", "rows": bars})
T.bar_chart(HERE / "figure.png", "Test 08 · GRAFT on Qwen",
            "100 multi-hop questions · Qwen3.8-27B W4A16 answers · 3 repeats per arm · free (local vLLM)",
            panels, legend=[T.NAVY, T.GREEN, T.YELLOW, T.STONE], label_in=4.2,
            footnote="The guide (B) holds on Qwen: 47.0 vs 39.3 for mode C. Compare arms only within a run.")
