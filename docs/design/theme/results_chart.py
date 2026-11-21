"""README results chart (assets/results.png), built only from the tests' table.csv files: no typed-in numbers.

    python docs/design/theme/results_chart.py          # write assets/results.png
    python docs/design/theme/results_chart.py --check  # print every number and the table row it came from

Each chart row pools the per-repeat accuracies of the table rows it names (mean as the bar, range as the whisker).
Qwen rows appear in their own panel once tests 05/06 have Qwen runs in their tables.
"""
import statistics
import sys

import theme as T

EXP = T.ROOT / "experiments"
TABLES = {"01": EXP / "test-01-read-order" / "table.csv", "03": EXP / "test-03-base-graph-rog" / "table.csv",
          "04": EXP / "test-04-base-graph-trex-full" / "table.csv", "05": EXP / "test-05-working-memory" / "table.csv",
          "06": EXP / "test-06-trex-structure-guide" / "table.csv"}

# (label, colour, [(test, {column: value} filter that picks table rows)]); the model column, if any, is added below.
ROWS = [
    ("GRAFT + T-REx structure guide", T.GREEN, [("06", {"arm": "B"})]),
    ("Working memory in the graph (C v2)", T.YELLOW, [("05", {"arm": "C v2"})]),
    ("GRAFT, mode C (previous default)", T.NAVY, [("05", {"arm": "A"})]),
    ("Same steps, prompt only (C- v2)", T.STONE, [("05", {"arm": "C- v2"})]),
    ("GRAFT + RoG base (Freebase)", T.STONE, [("03", {"kind": "paid"})]),
    ("GRAFT + full T-REx base (EiG)", T.STONE, [("04", {"run": "run-02", "pass": "EiG"})]),
    ("GRAFT + T-REx background facts", T.STONE, [("06", {"arm": "D"})]),
    ("GRAFT + T-REx as a bridge", T.STONE, [("06", {"arm": "C"})]),
    ("HippoRAG 2", T.STONE, [("01", {"variant": "HippoRAG 2", "answer_tokens": "256"})]),
    ("BM25", T.STONE, [("01", {"variant": "BM25", "answer_tokens": "256"})]),
]


def pick(test, flt, model):
    rows = T.read_table(TABLES[test])
    out = []
    for i, r in enumerate(rows):
        if "model" in r and r["model"] != model:
            continue
        if "model" not in r and model != "Haiku":
            continue
        if all(r.get(k) == v for k, v in flt.items()):
            out.append((i, r))
    return out


def build(model):
    bars, lines = [], []
    for label, colour, sources in ROWS:
        vals, gold, srcs = [], [], []
        for test, flt in sources:
            for i, r in pick(test, flt, model):
                v = T.per_repeat_values(r["per_repeat"])
                vals += v
                if r.get("gold_in_final_facts") not in ("", None):
                    gold.append((float(r["gold_in_final_facts"]), len(v)))
                srcs.append(f"{TABLES[test].relative_to(T.ROOT)} row {i + 2} ({', '.join(f'{k}={v}' for k, v in flt.items())}"
                            f"{', model=' + model if 'model' in r else ''}): per_repeat {r['per_repeat']}")
        if not vals:
            if model == "Haiku":
                lines.append(f"MISSING  {label}: no table row matches {sources}")
            continue
        g = round(sum(a * n for a, n in gold) / sum(n for _, n in gold), 1) if gold else None
        bars.append(T.bar(label + ("" if model == "Haiku" else f" · {model}"), vals, colour))
        lines.append(f"{label} [{model}]: mean {statistics.mean(vals):.1f}, range {min(vals):.0f}-{max(vals):.0f}, "
                     f"{len(vals)} {'repeats' if len(vals) > 1 else 'run'}, gold reached the model "
                     f"{g if g is not None else 'not recorded'}")
        lines += ["    from " + s for s in srcs]
    return bars, lines


def main():
    haiku, lines = build("Haiku")
    qwen, qlines = build("Qwen")
    if "--check" in sys.argv:
        print("\n".join(lines + qlines))
        return
    panels = [{"title": "Claude Haiku 5.5 answers" if qwen else None, "rows": haiku}]
    if qwen:
        panels.append({"title": "Qwen answers", "rows": qwen})
    T.bar_chart(T.ROOT / "assets" / "results.png", "Accuracy on FactConsolidation multi-hop",
                "100 questions with edited facts · " + ("" if qwen else "Claude Haiku 5.5 answers · ")
                + "% correct, mean with range over repeats",
                panels, legend=[(T.GREEN, "new default on Haiku"), (T.NAVY, "previous default"), T.YELLOW, T.STONE],
                footnote="Repeats vary by about 2 points: Haiku's sampling can't be fixed. "
                         "Single runs: BM25 and HippoRAG 2 on Nov 13, RoG base on Nov 20.")


if __name__ == "__main__":
    main()
