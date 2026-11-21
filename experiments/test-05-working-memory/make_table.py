"""test-05 table, from the runs only: per arm, accuracy over repeats (substring exact match), gold fact in the final
facts, LLM calls, tokens and cost per question. Reads runs/run-NN/exp_wm_empty_<arm>_*/repeat_*/scored.jsonl."""
import csv, glob, json, statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = [("a_modec", "A", "mode C, one answer call"), ("b_qlayer", "B", "question layer"),
        ("c_wm_graph", "C", "working memory in the graph"), ("cm_wm_prompt", "C-", "same steps, prompt only"),
        ("c_wm_graph_v2", "C v2", "C, step prompt with the newer-fact rule"), ("cm_wm_prompt_v2", "C- v2", "C-, same prompt")]
rows = []
for key, arm, what in ARMS:
    runs = sorted(glob.glob(str(HERE / "runs" / "run-*" / f"exp_wm_empty_{key}_2*")))
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
    rows.append({"arm": arm, "what": what, "repeats": len(reps), "accuracy_mean": round(statistics.mean(acc), 1),
                 "accuracy_sd": round(statistics.stdev(acc), 1) if len(acc) > 1 else 0, "per_repeat": " / ".join(f"{a:.0f}" for a in acc),
                 "gold_in_final_facts": round(statistics.mean(gold), 1), "calls_per_question": round(calls / n, 2),
                 "input_tokens_per_question": round(tin / n), "output_tokens_per_question": round(tout / n),
                 "cost_per_100_questions_usd": round(cost / len(reps), 3), "run": str(Path(R).relative_to(HERE))})
with open(HERE / "table.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
md = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])] + ["| " + " | ".join(str(v) for v in r.values()) + " |" for r in rows]
(HERE / "table.md").write_text("\n".join(md) + "\n")
print("\n".join(md))
