"""GRAFT results chart in the shared Flotilla/GRAFT theme.
Numbers: experiments/test-01, 03, 04, 05 READMEs (FactConsolidation-MH, 100 questions, Claude Haiku 5.5, 256-token answers)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Patch

D = os.path.dirname(os.path.abspath(__file__))
for w in ("600", "700", "800"):
    fm.fontManager.addfont(os.path.join(D, f"Nunito-{w}.ttf"))
plt.rcParams.update({"font.family": "Nunito", "font.weight": 600})

IVORY, INK, INK2, INK3, LINE = "#F3EFE6", "#2A2723", "#5F5A52", "#8E887D", "#E2DCCF"
NAVY, YELLOW, GREEN, STONE = "#22344A", "#F2C230", "#5FA845", "#C9C2B4"

# (label, mean, low, high, n_runs, colour)
rows = [
    ("Working memory in the graph (C v2)", 35.7, 34, 38, 3, YELLOW),
    ("GRAFT, mode C (default)",           34.7, 33, 36, 6, NAVY),
    ("Same steps, prompt only (C- v2)",   33.0, 33, 33, 3, STONE),
    ("GRAFT + RoG base (Freebase)",       21.0, None, None, 1, STONE),
    ("GRAFT + full T-REx base (EiG)",     17.7, 15, 20, 3, STONE),
    ("HippoRAG 2",                        15.0, None, None, 1, STONE),
    ("BM25",                               4.0, None, None, 1, STONE),
][::-1]

fig, ax = plt.subplots(figsize=(9, 5.8), dpi=200)
fig.patch.set_facecolor(IVORY); ax.set_facecolor(IVORY)
for i, (lab, m, lo, hi, n, col) in enumerate(rows):
    ax.barh(i, m, height=0.56, color=col, zorder=3)
    if lo is not None and hi != lo:
        ax.plot([lo, hi], [i, i], color=INK, lw=1.6, zorder=4)
        for x in (lo, hi):
            ax.plot([x, x], [i - 0.13, i + 0.13], color=INK, lw=1.6, zorder=4)
    end = max(m, hi or m)
    note = f"{m:.1f}" + ("" if n > 1 else "   one run")
    ax.text(end + 0.8, i, note, va="center", fontsize=10, weight=800, color=INK)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[0] for r in rows], fontsize=10.5, color=INK, weight=700)
ax.set_xlim(0, 46); ax.set_ylim(-0.6, len(rows) - 0.4)
ax.set_xticks([0, 10, 20, 30, 40])
ax.tick_params(axis="x", colors=INK3, labelsize=9, length=0); ax.tick_params(axis="y", length=0, pad=8)
ax.grid(axis="x", color=LINE, lw=1); ax.set_axisbelow(True)
for s in ax.spines.values(): s.set_visible(False)
fig.text(0.03, 0.94, "Accuracy on FactConsolidation multi-hop", fontsize=19, weight=800, color=INK)
fig.text(0.03, 0.895, "100 questions with edited facts · Claude Haiku 5.5 answers · % correct, mean with range over repeats",
         fontsize=10, color=INK2)
fig.legend(handles=[Patch(color=NAVY, label="GRAFT default"), Patch(color=YELLOW, label="being tested"),
                    Patch(color=STONE, label="baseline or not adopted")],
           loc="upper left", bbox_to_anchor=(0.025, 0.875), ncol=3, frameon=False, fontsize=9.5,
           labelcolor=INK2, handlelength=1.1, handleheight=1.1, columnspacing=1.6)
fig.text(0.03, 0.02, "Repeats vary by about 2 points: Haiku's sampling can't be fixed. Single runs: BM25 and HippoRAG 2 on Nov 13, RoG base on Nov 20.",
         fontsize=8.5, color=INK3)
plt.subplots_adjust(left=0.33, right=0.97, top=0.8, bottom=0.1)
plt.savefig(os.path.join(D, "assets/results.png"), facecolor=IVORY)
print("ok")
