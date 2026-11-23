"""Test 10 table from the runs only (stdlib; run where the results are).

    python3 experiments/test-10-passage-index/make_table.py --runs-root $HOME/scratch/sgar/results/runs [--prefix exp_passages]

Per arm and repeat (one run folder each, exp_passages4k_<arm>_r<k>_<time>_j<job>; the newest complete folder wins):
right answers of 100 (substring exact match, MemoryAgentBench's metric as in tests 08 and 09), gold in the context
Qwen read (answer_in_retrieved), tokens shown per question (the whole context block on the final call, 4 characters
per token: fact lines or passages, plus G49's summary, the outdated notes and G53's opened text), Qwen calls per
question (all calls of the run, the guide's question parses included, over the questions), and for G53 the asks per
question and opened tokens per question.
"""
import argparse
import csv
import json
import math
import statistics
from pathlib import Path

ARMS = [("g35", "G35", "S179", "guided facts, 50 lines"), ("g52", "G52", "S183", "guided facts to 4,096 tokens"),
        ("g49", "G49", "S180", "the index: guided passages"), ("g53", "G53", "S184", "the index with reading"),
        ("g50", "G50", "S181", "HippoRAG 2-style passages"), ("g51", "G51", "S182", "BM25 passages")]


def runs(root: Path, prefix: str, arm: str) -> dict[int, Path]:
    out = {}
    for d in sorted(root.glob(f"{prefix}_{arm}_r*_*_j*")):
        s = d / "repeat_0" / "scored.jsonl"
        if s.exists() and sum(1 for _ in open(s)) == 100:
            out[int(d.name.split(f"{arm}_r")[1].split("_")[0])] = d  # sorted by time: the newest wins
    return out


def row(d: Path) -> dict:
    sc = [json.loads(l) for l in open(d / "repeat_0" / "scored.jsonl")]
    pr = {r["q_index"]: r for r in map(json.loads, open(d / "repeat_0" / "predictions.jsonl"))}
    n = len(sc)
    toks = [math.ceil(len(s.get("retrieved_text") or "") / 4) for s in sc]
    reading = [pr[s["q_index"]].get("reading") for s in sc if pr.get(s["q_index"], {}).get("reading")]
    return {"right": round(sum(s["substring_exact_match"] for s in sc)), "gold_in_context": sum(bool(s.get("answer_in_retrieved")) for s in sc),
            "tokens_mean": round(statistics.mean(toks)), "tokens_min": min(toks), "tokens_max": max(toks),
            "calls_per_q": round(sum(s.get("llm_calls") or 0 for s in sc) / n, 2),
            "asks_per_q": round(sum(r["asks"] for r in reading) / n, 2) if reading else None,
            "opened_tokens_per_q": round(sum(r["tokens_added"] for r in reading) / n) if reading else None,
            "cut_at_cap": sum(s.get("stop_reason") in ("max_tokens", "length") for s in sc), "run": d.name}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", required=True)
    ap.add_argument("--prefix", default="exp_passages4k")
    ap.add_argument("--out", default=str(Path(__file__).parent))
    a = ap.parse_args()
    rows = []
    for arm, cid, setup, what in ARMS:
        for k, d in sorted(runs(Path(a.runs_root), a.prefix, arm).items()):
            rows.append({"candidate": cid, "setup": setup, "arm": what, "repeat": k, **row(d)})
    out = Path(a.out)
    with open(out / "table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    lines = ["| Candidate | Arm | Right per repeat (of 100) | Mean | Spread | Gold in context | Tokens shown per question: mean (min-max) | Qwen calls per question | Asks per question | Opened tokens per question | Cut at the cap |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm, cid, setup, what in ARMS:
        rs = [r for r in rows if r["candidate"] == cid]
        if not rs:
            continue
        right = [r["right"] for r in rs]
        rng = lambda k: f"{min(r[k] for r in rs)}-{max(r[k] for r in rs)}" if len({r[k] for r in rs}) > 1 else str(rs[0][k])
        lines.append(f"| {cid} | {what} | {', '.join(map(str, right))} | {statistics.mean(right):.1f} | {max(right) - min(right)} | "
                     f"{rng('gold_in_context')}% | {round(statistics.mean(r['tokens_mean'] for r in rs)):,} "
                     f"({min(r['tokens_min'] for r in rs):,}-{max(r['tokens_max'] for r in rs):,}) | {rng('calls_per_q')} | "
                     f"{rng('asks_per_q') if rs[0]['asks_per_q'] is not None else '-'} | "
                     f"{rng('opened_tokens_per_q') if rs[0]['opened_tokens_per_q'] is not None else '-'} | {rng('cut_at_cap')} |")
    (out / "table.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
