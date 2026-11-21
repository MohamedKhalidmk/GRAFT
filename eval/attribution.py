"""Where did the gold answer come from? For runs that label each retrieved fact by source (hybrid: "graph", "embed"
or "both"), count per question whether the gold answer appears only in graph-side facts, only in embedding-search
facts, in facts of both kinds (or in a fact both lists ranked), or in none.

    python -m eval.attribution RUN_DIR [RUN_DIR ...]
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from eval.benchmark import answer_in_text


def classify(row: dict) -> str:
    blocks = re.split(r"^Memory \d+:\n", row.get("retrieved_text", ""), flags=re.M)[1:]
    srcs = row.get("fact_sources") or []
    hits = {s for b, s in zip(blocks, srcs) if answer_in_text(row["answers"], b)}
    if not hits:
        # the gold answer may still be in the whole text (e.g. split across facts); count it apart
        return "neither" if not row.get("answer_in_retrieved") else "only_across_facts"
    if "both" in hits or {"graph", "embed"} <= hits:
        return "both"
    return "only_graph" if "graph" in hits else "only_embed"


def main() -> None:
    for run in sys.argv[1:]:
        rows = [json.loads(l) for f in sorted(Path(run).glob("repeat_*/scored.jsonl")) for l in open(f)]
        c = Counter(classify(r) for r in rows)
        n = len(rows)
        sub = [r["answer_in_subgraph"] for r in rows if "answer_in_subgraph" in r]
        q = [r["query_time_s"] for r in rows if r.get("query_time_s") is not None]
        print(f"{Path(run).name}: n={n} gold_in_subgraph={sum(sub) if sub else 'n/a'} "
              f"gold_in_retrieved={sum(bool(r.get('answer_in_retrieved')) for r in rows)} "
              f"query_s_mean={sum(q) / len(q):.2f}" if q else "",
              {k: c[k] for k in ("only_graph", "only_embed", "both", "neither", "only_across_facts")})


if __name__ == "__main__":
    main()
