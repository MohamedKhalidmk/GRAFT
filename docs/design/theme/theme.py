"""Shared GRAFT chart theme (the look of charts.py) and the run readers every experiments/test-0N-*/make_table.py uses.

Colours, Nunito fonts, a horizontal bar chart with the mean and the range over repeats ("one run" when there is one),
and scoring helpers: "right" = substring_exact_match > 0, "gold reached the model" = answer_in_retrieved.
"""
import csv
import glob
import json
import math
import os
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
for _w in ("600", "700", "800"):
    fm.fontManager.addfont(str(D / f"Nunito-{_w}.ttf"))
plt.rcParams.update({"font.family": "Nunito", "font.weight": 600})

IVORY, INK, INK2, INK3, LINE = "#F3EFE6", "#2A2723", "#5F5A52", "#8E887D", "#E2DCCF"
NAVY, YELLOW, GREEN, RED, STONE = "#22344A", "#F2C230", "#5FA845", "#C8362E", "#C9C2B4"

# What each colour means, everywhere.
LEGEND = {NAVY: "GRAFT default", GREEN: "kept: new default", YELLOW: "being tested", STONE: "baseline or not adopted",
          RED: "broken run"}

DATASET = "FactConsolidation multi-hop · 100 questions with edited facts"


# ---------------------------------------------------------------- runs

def latest(base, pattern):
    """Newest run folder matching pattern under base (a Path or a list of Paths), or None."""
    bases = base if isinstance(base, (list, tuple)) else [base]
    hits = sorted(h for b in bases for h in glob.glob(str(Path(b) / pattern)))
    return hits[-1] if hits else None


def all_runs(base, pattern):
    bases = base if isinstance(base, (list, tuple)) else [base]
    return sorted(h for b in bases for h in glob.glob(str(Path(b) / pattern)))


def score_repeat(scored_path):
    """One repeat's scored.jsonl -> dict of per-repeat numbers (percent of questions)."""
    sc = [json.loads(line) for line in open(scored_path)]
    n = len(sc)
    gold = [s.get("answer_in_retrieved") for s in sc]
    return {"n": n,
            "acc": 100 * sum(s["substring_exact_match"] > 0 for s in sc) / n,
            "gold": None if all(g is None for g in gold) else 100 * sum(bool(g) for g in gold) / n,
            "cut": None if all(s.get("stop_reason") is None for s in sc) else sum(s.get("stop_reason") == "max_tokens" for s in sc),
            "cost": sum(s.get("cost_usd", 0) or 0 for s in sc),
            "in_tok": sum(s.get("input_tokens", 0) or 0 for s in sc),
            "out_tok": sum(s.get("output_tokens", 0) or 0 for s in sc),
            "calls": sum(s.get("llm_calls", 0) or 0 for s in sc)}


def score_runs(run_dirs):
    """Repeats of one or more run folders (each with repeat_*/scored.jsonl), pooled in order."""
    reps = []
    for r in run_dirs if isinstance(run_dirs, (list, tuple)) else [run_dirs]:
        reps += [score_repeat(p) for p in sorted(glob.glob(str(Path(r) / "repeat_*" / "scored.jsonl")))]
    return reps


def summarise(reps):
    """Mean / sd / per-repeat text for accuracy and gold over repeats."""
    acc = [r["acc"] for r in reps]
    gold = [r["gold"] for r in reps if r["gold"] is not None]
    n_q = sum(r["n"] for r in reps)
    return {"repeats": len(reps),
            "accuracy_mean": round(statistics.mean(acc), 1),
            "accuracy_sd": round(statistics.stdev(acc), 1) if len(acc) > 1 else 0,
            "per_repeat": " / ".join(f"{a:.0f}" for a in acc),
            "gold_in_final_facts": round(statistics.mean(gold), 1) if gold else "",
            "cost_per_100_questions_usd": round(100 * sum(r["cost"] for r in reps) / n_q, 3)}


def rel(path, here):
    return os.path.relpath(path, here)


def write_tables(here, rows):
    """table.csv and table.md from a list of dicts (same keys)."""
    here = Path(here)
    rows = [with_ids(r) for r in rows]
    keys = list(rows[0])
    with open(here / "table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    md = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
    md += ["| " + " | ".join(str(r[k]) for k in keys) + " |" for r in rows]
    (here / "table.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


def read_table(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def per_repeat_values(text):
    """'35 / 34 / 35' -> [35.0, 34.0, 35.0]."""
    return [float(v) for v in str(text).split("/") if v.strip()]


# ---------------------------------------------------------------- charts

def bar(label, values, colour=STONE, note=""):
    """One chart row: values are the per-repeat numbers (mean drawn as the bar, range as a whisker)."""
    return {"label": label, "values": [float(v) for v in values], "colour": colour, "note": note}


def _xmax(panels):
    top = max((max(r["values"]) for p in panels for r in p["rows"] if r["values"]), default=10)
    return top


def bar_chart(out, title, subtitle, panels, legend=None, footnote="", width=9.0, label_in=3.0, value_room=1.22):
    """Horizontal bars in the GRAFT theme.

    panels: list of {"title": str or None, "rows": [bar(...)], "xlabel": str or None, "one_run_note": bool (default True)}
    legend: list of colours (labels from LEGEND) or (colour, label) pairs; None for no legend.
    """
    row_h, head = 0.56, 1.05 + (0.42 if legend else 0)
    p_title, p_axis, foot = 0.42, 0.42, 0.45 if footnote else 0.2
    heights = [(p_title if p["title"] else 0.1) + len(p["rows"]) * row_h + 0.25 + p_axis for p in panels]
    H = head + sum(heights) + foot
    fig = plt.figure(figsize=(width, H), dpi=200)
    fig.patch.set_facecolor(IVORY)
    fx, fy = lambda inch: inch / width, lambda inch: inch / H

    fig.text(fx(0.27), 1 - fy(0.55), title, fontsize=19, weight=800, color=INK)
    fig.text(fx(0.27), 1 - fy(0.88), subtitle, fontsize=10, color=INK2)
    if legend:
        handles = [Patch(color=c, label=LEGEND[c]) if isinstance(c, str) else Patch(color=c[0], label=c[1]) for c in legend]
        fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(fx(0.22), 1 - fy(1.02)), ncol=len(handles),
                   frameon=False, fontsize=9.5, labelcolor=INK2, handlelength=1.1, handleheight=1.1, columnspacing=1.6)

    top = _xmax(panels)
    xmax = top * value_room + 6
    step = 10 if top > 25 else 5
    ticks = list(range(0, int(math.floor(top / step) * step) + step + 1, step))
    ticks = [t for t in ticks if t <= xmax - 3]

    y = H - head
    for p, h in zip(panels, heights):
        if p["title"]:
            fig.text(fx(0.27), fy(y - 0.28), p["title"], fontsize=12, weight=800, color=INK)
            y -= p_title
        else:
            y -= 0.1
        ax_h = len(p["rows"]) * row_h + 0.25
        ax = fig.add_axes([fx(label_in), fy(y - ax_h), 1 - fx(label_in) - fx(0.27), fy(ax_h)])
        _draw(ax, p["rows"], xmax, ticks, p.get("xlabel"), p.get("one_run_note", True))
        y -= h - (p_title if p["title"] else 0.1)
    if footnote:
        fig.text(fx(0.27), fy(0.18), footnote, fontsize=8.5, color=INK3)
    fig.savefig(out, facecolor=IVORY)
    plt.close(fig)
    print("wrote", out)


def _draw(ax, rows, xmax, ticks, xlabel, one_run_note=True):
    ax.set_facecolor(IVORY)
    rows = rows[::-1]
    for i, r in enumerate(rows):
        v = r["values"]
        if not v:
            ax.text(0.8, i, "no run", va="center", fontsize=10, weight=800, color=INK3)
            continue
        m, lo, hi = statistics.mean(v), min(v), max(v)
        ax.barh(i, m, height=0.56, color=r["colour"], zorder=3)
        if len(v) > 1 and hi != lo:
            ax.plot([lo, hi], [i, i], color=INK, lw=1.6, zorder=4)
            for x in (lo, hi):
                ax.plot([x, x], [i - 0.13, i + 0.13], color=INK, lw=1.6, zorder=4)
        note = f"{m:.1f}" + ("   one run" if len(v) == 1 and one_run_note else "") + (f"   {r['note']}" if r["note"] else "")
        ax.text(max(m, hi) + xmax * 0.017, i, note, va="center", fontsize=10, weight=800, color=INK)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r["label"] for r in rows], fontsize=10.5, color=INK, weight=700)
    ax.set_xlim(0, xmax)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xticks(ticks)
    ax.tick_params(axis="x", colors=INK3, labelsize=9, length=0)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.grid(axis="x", color=LINE, lw=1)
    ax.set_axisbelow(True)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=9, color=INK3)
    for s in ax.spines.values():
        s.set_visible(False)


# ------------------------------------------------------------------ registry (docs/REGISTRY.md)
_REG = None


def registry():
    """run name -> (candidate, setup), from the setup table of docs/REGISTRY.md (the frozen IDs)."""
    global _REG
    if _REG is None:
        import re
        _REG = {}
        for line in (ROOT / "docs" / "REGISTRY.md").read_text().splitlines():
            m = re.match(r"\| (S\d+) \| ([^|]+?) \| .*\| ([^|]*`[^|]*) \|\s*$", line)
            if m:
                for name in re.findall(r"`([^`]+)`", m.group(3)):
                    if name.endswith("r0..2"):
                        for k in range(3):
                            _REG[name[:-5] + f"r{k}"] = (m.group(2).strip(), m.group(1))
                    else:
                        _REG[name] = (m.group(2).strip(), m.group(1))
    return _REG


def ids(run_dir):
    """(candidate, setup) of a run folder: its name minus the _<timestamp>[_j<job>] suffix, looked up in the registry."""
    import re
    name = re.sub(r"_2026\d{4}-\d{6}.*$", "", Path(str(run_dir)).name)
    return registry().get(name, ("", ""))


def with_ids(row):
    """The row with candidate and setup columns first (from the first run folder named in it), if it has none."""
    if "candidate" in row:
        return row
    import re
    cand = setup = ""
    for v in row.values():
        for name in re.findall(r"(exp_[A-Za-z0-9_]+?_2026\d{4}-\d{6}[^;/ ]*)", str(v)):
            cand, setup = ids(name)
            if cand:
                break
        if cand:
            break
    return {"candidate": cand, "setup": setup, **row}


def tag(label, run_dir):
    """A figure label with the candidate ID in front, e.g. "G35 · the guide"."""
    if isinstance(run_dir, (list, tuple)):
        run_dir = run_dir[0] if run_dir else ""
    import re
    cand = ids(run_dir)[0]
    ours = re.match(r"^[GF]\d+$", cand or "")
    return f"{cand} · {label}" if ours and not str(label).startswith(cand) else label
