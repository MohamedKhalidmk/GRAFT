"""Build the results table (the SF part of the paper's Table 3) from saved runs.

    python -m eval.table --length 262k --mode real

For each method, the most recent run with the requested context length and LLM mode is used.
Every number comes from that run's summary.json; the paper's numbers come from
results/paper_table3.csv (made by data/paper_reference.py) and are shown as a separate,
labelled reference block, never mixed with ours.

Writes results/table_<length>_<mode>.csv and .md.
"""

import argparse
import csv
import json
import os
from pathlib import Path

from eval.methods import AGENTIC, LONG_CONTEXT, METHODS, OURS, REPO, SIMPLE_RAG, STRUCTURE_RAG

FAMILY_ORDER = [LONG_CONTEXT, SIMPLE_RAG, STRUCTURE_RAG, AGENTIC, OURS]
PAPER_CSV = REPO / "results" / "paper_table3.csv"
COLUMNS = ["Method", "Family", "FC-SH", "FC-MH", "Avg", "Tokens / question", "Memory build time (s)",
           "Query time (s)", "API cost ($)", "Questions (SH/MH)", "Repeats", "Answer in retrieved (SH/MH)"]


def results_dir() -> Path:
    return Path(os.environ.get("RESULTS_DIR", REPO / "results"))


def latest_summaries(length: str, mode: str) -> dict[tuple[str, str], dict]:
    """(method key, variant) -> summary of its most recent finished run at this length and mode.
    A variant is a method run with settings changed from its defaults (e.g. an GRAFT ablation)."""
    found: dict[tuple[str, str], tuple[float, dict]] = {}
    for path in (results_dir() / "runs").glob("*/summary.json"):
        s = json.loads(path.read_text())
        if s["length"] != length or s["llm_mode"] != mode or set(s["accuracy"]) != {"sh", "mh"}:
            continue
        key = (s["method"], s.get("variant", ""))
        mtime = path.stat().st_mtime
        if key not in found or mtime > found[key][0]:
            found[key] = (mtime, {**s, "run_dir": str(path.parent)})
    return {k: v for k, (_, v) in found.items()}


def _fmt(value: float | None, digits: int = 1) -> str:
    return "" if value is None else f"{value:.{digits}f}"


def row_for(s: dict) -> dict:
    sh, mh = s["accuracy"]["sh"], s["accuracy"]["mh"]

    def acc(a: dict) -> str:
        return _fmt(a["mean"]) + (f" ± {a['std']:.1f}" if s["repeats"] > 1 else "")

    recall = s.get("answer_in_retrieved")
    return {
        "Method": s["display"] + (f" [{s['variant']}]" if s.get("variant") else ""), "Family": s["family"], "FC-SH": acc(sh), "FC-MH": acc(mh),
        "Avg": _fmt((sh["mean"] + mh["mean"]) / 2), "Tokens / question": _fmt(s["tokens_per_question"], 0),
        "Memory build time (s)": _fmt(s["memory_build_time_s"]), "Query time (s)": _fmt(s["query_time_s"], 2),
        "API cost ($)": _fmt(s["api_cost_usd"]["total"], 3),
        "Questions (SH/MH)": f"{s['n_questions']['sh']}/{s['n_questions']['mh']}", "Repeats": str(s["repeats"]),
        "Answer in retrieved (SH/MH)": f"{100 * recall['sh']:.0f}/{100 * recall['mh']:.0f}" if recall else "",
    }


def our_rows(length: str, mode: str) -> list[dict]:
    summaries = latest_summaries(length, mode)
    keys = sorted(summaries, key=lambda k: (FAMILY_ORDER.index(METHODS[k[0]].family), list(METHODS).index(METHODS[k[0]].key), k[1]))
    return [row_for(summaries[k]) for k in keys]


def paper_rows() -> list[dict]:
    if not PAPER_CSV.exists():
        return []
    with open(PAPER_CSV) as f:
        return [{"System": r["System"], "Family": r["Family"], "FC-SH": r["FC-SH"], "FC-MH": r["FC-MH"],
                 "Avg": r["SF Avg"]} for r in csv.DictReader(f)]


def markdown(rows: list[dict], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(str(r.get(c, "")) for c in columns) + " |" for r in rows]
    return "\n".join(lines)


def build(length: str, mode: str) -> Path:
    ours, paper = our_rows(length, mode), paper_rows()
    out = results_dir() / f"table_{length}_{mode}"
    with open(out.with_suffix(".csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(ours)
    title = f"## Selective Forgetting, FactConsolidation {length}, Claude Haiku 5.5"
    if mode == "fake":
        title += "\n\n**FAKE LLM: pipeline test only. Accuracy is meaningless; tokens and cost are rough estimates.**"
    md = [title, "", "Accuracy in %, substring exact match (the paper's metric). ± is the standard deviation "
                     "over repeats. Answer in retrieved: share of questions whose gold answer appears in the memory "
                     "handed to the model (methods that report it).", "", markdown(ours, COLUMNS)]
    if paper:
        md += ["", "## Reference only: paper's Table 3 (GPT-4o-mini backbone, 262K, not a reproduction)", "",
               "Source: arXiv 2507.05257v4, extracted by data/paper_reference.py.", "",
               markdown(paper, ["System", "Family", "FC-SH", "FC-MH", "Avg"])]
    out.with_suffix(".md").write_text("\n".join(md) + "\n")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--length", default="262k")
    parser.add_argument("--mode", choices=["real", "fake"], default="real")
    args = parser.parse_args()
    out = build(args.length, args.mode)
    print(out.with_suffix(".md").read_text())


if __name__ == "__main__":
    main()
