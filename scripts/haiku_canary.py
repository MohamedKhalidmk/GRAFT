"""History of the fixed Haiku check: every run that re-answered the 2026-11-13 run's exact facts (canary and replay
runs), with its date, score, answer length and whether Haiku's replies changed. Identical inputs, so a moved score
means something changed on the API side (or chance: about 1.8 points of spread per run).

    python scripts/haiku_canary.py [--runs $RESULTS_DIR/runs] [--out experiments/test-07-haiku-drift/haiku_canary.md]
"""
import argparse
import glob
import json
import os
import statistics
import time
from pathlib import Path

PATTERNS = ["exp_c_real_mh_262k_ans256_2026111*", "exp_real_replay38_2*", "exp_real_canary_replay38_2*"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=os.path.join(os.environ.get("RESULTS_DIR", "results"), "runs"))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rows, first = [], None
    for pat in PATTERNS:
        for run in sorted(glob.glob(os.path.join(a.runs, pat))):
            if "rerun" in run:
                continue
            for rep in sorted(glob.glob(run + "/repeat_*/scored.jsonl")):
                sc = [json.loads(l) for l in open(rep)]
                use = Path(rep).with_name("usage.jsonl")
                us = [json.loads(l) for l in open(use)] if use.exists() else []
                answers = {s["q_index"]: s["prediction"] for s in sc}
                first = first or answers
                rows.append({"when": time.strftime("%Y-%m-%d %H:%M", time.localtime(min(u["ts"] for u in us))) if us else "?",
                             "run": f"{Path(run).name}/{Path(rep).parent.name}",
                             "right": sum(s["substring_exact_match"] > 0 for s in sc),
                             "mean_output_tokens": round(statistics.mean(u["output_tokens"] for u in us), 1) if us else None,
                             "replies_same_as_first": sum(answers.get(q) == t for q, t in first.items()),
                             "request_ids_logged": sum(bool(u.get("request_id")) for u in us)})
    rows.sort(key=lambda r: r["when"])
    md = ["| When | Run | Right (of 100) | Mean output tokens | Replies identical to the 2026-11-13 run | Request IDs logged |",
          "|---|---|---|---|---|---|"]
    md += [f"| {r['when']} | {r['run']} | {r['right']} | {r['mean_output_tokens']} | {r['replies_same_as_first']} | {r['request_ids_logged']} |" for r in rows]
    text = "\n".join(md)
    print(text)
    if a.out:
        Path(a.out).write_text("# Fixed Haiku check\n\nThe same 100 prompts every time (the 2026-11-13 run's retrieved facts, "
                               "configs/runs/exp/canary/). Built by scripts/haiku_canary.py.\n\n" + text + "\n")


if __name__ == "__main__":
    main()
