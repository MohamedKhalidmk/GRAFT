"""test-01 table and figure, from the runs only: runs/run-01 (16-token answers, Fir job 3787840) and runs/run-02
(256-token re-answers, Fir job 3845944; HippoRAG 2 on the Mac, also at 2,048 tokens). One repeat per run."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "docs" / "design" / "theme"))
import theme as T  # noqa: E402

VARIANTS = [("a", "A", "PPR -> GNN + GOAt", T.STONE), ("b", "B", "GNN + GOAt -> PPR", T.STONE),
            ("c", "C", "PPR -> GNN + GOAt -> short PPR", T.NAVY), ("d_extend", "D", "A, synthetic starting graph", T.STONE),
            ("bm25", "BM25", "top 512-token chunks", T.STONE), ("hipporag", "HippoRAG 2", "benchmark copy, top 10 passages", T.STONE)]
LIMITS = [("run-01", 16, ""), ("run-02", 256, "_ans256"), ("run-02", 2048, "_ans2048")]

rows, chart = [], {16: [], 256: []}
for run, limit, suffix in LIMITS:
    for key, name, what, colour in VARIANTS:
        R = T.latest(HERE / "runs" / run, f"exp_{key}_real_mh_262k{suffix}_2*")
        if not R:
            continue
        reps = T.score_runs([R])
        s = T.summarise(reps)
        rows.append({"variant": name, "what": what, "answer_tokens": limit, "repeats": s["repeats"],
                     "accuracy_mean": s["accuracy_mean"], "per_repeat": s["per_repeat"],
                     "gold_in_final_facts": s["gold_in_final_facts"], "cut_off": "" if any(r["cut"] is None for r in reps) else sum(r["cut"] for r in reps),
                     "cost_per_100_questions_usd": s["cost_per_100_questions_usd"], "run": T.rel(R, HERE)})
        if limit in chart:
            chart[limit].append(T.bar(T.tag(what, R) if len(name) == 1 else name, [r["acc"] for r in reps], colour))

T.write_tables(HERE, rows)
T.bar_chart(HERE / "figure.png", "Test 01 · Read order and starting graph",
            "% right of 100 · Claude Haiku 5.5 · one run each, 2026-11-13",
            [{"title": "Answers up to 256 tokens", "rows": chart[256]},
             {"title": "Answers up to 16 tokens (the benchmark's setting: most answers cut off)", "rows": chart[16]}],
            legend=[T.NAVY, T.STONE],
            footnote="C became the default read order. HippoRAG 2's cut-offs are not in its per-question rows.")
