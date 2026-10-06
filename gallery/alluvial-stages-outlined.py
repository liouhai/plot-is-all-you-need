"""Alluvial diagram over five stages: outlined stage bars, soft ribbons, dashed horizontal guides.

Drawn after exemplar 7688165147727602411_0001 (layout, marks, palette, legend).

*** SIMULATED DATA *** below. Replace `STAGES`, `CLASSES`, `start` (class sizes at the first stage) and
`moves` (one class-by-class transition matrix per pair of neighbouring stages; rows = from, columns = to).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch, Rectangle

OUT = Path(__file__).with_suffix(".png")
STAGES = ["Orig", "1st", "2nd", "3rd", "4th"]
CLASSES = ["National SEZs", "General SEZs", "Non-SEZs"]                   # top to bottom
DARK = ["#f5c287", "#e98b88", "#8e8cc0"]
PALE = ["#f9dfc0", "#f4c2c0", "#c9c8e2"]
GAP, BAR_W = 2.0, 0.07                                                     # gap between classes (data units), bar width

start = np.array([14.0, 13.0, 73.0])
share = [np.array([[.93, .05, .02], [.10, .82, .08], [.04, .05, .91]]), np.array([[.90, .08, .02], [.12, .80, .08], [.02, .07, .91]]),
         np.array([[.95, .04, .01], [.10, .84, .06], [.03, .05, .92]]), np.array([[.96, .03, .01], [.12, .82, .06], [.03, .06, .91]])]
moves, size = [], [start]
for s in share:
    moves.append(size[-1][:, None] * s)
    size.append(moves[-1].sum(0))
total = start.sum() + GAP * (len(CLASSES) - 1)


def tops(sz):
    """y of the top edge of each class block, stacking downwards from `total`."""
    return total - np.concatenate([[0], np.cumsum(sz[:-1] + GAP)])


plt.rcParams.update({"font.family": "Times New Roman", "font.size": 9, "pdf.fonttype": 42})
fig, ax = plt.subplots(figsize=(5.4, 5.6))
fig.subplots_adjust(left=0.06, right=0.94, top=0.92, bottom=0.15)
u = np.linspace(0, 1, 60)
ease = 3 * u ** 2 - 2 * u ** 3                                             # smooth S-curve between stages
for s, m in enumerate(moves):
    top_a, top_b = tops(size[s]), tops(size[s + 1])
    out_used, in_used = np.zeros(len(CLASSES)), np.zeros(len(CLASSES))
    for i in range(len(CLASSES)):
        for j in range(len(CLASSES)):
            ya, yb = top_a[i] - out_used[i], top_b[j] - in_used[j]
            upper = ya + (yb - ya) * ease
            ax.fill_between(s + BAR_W / 2 + (1 - BAR_W) * u, upper - m[i, j], upper, color=PALE[i], alpha=0.75, lw=0, zorder=2)
            out_used[i] += m[i, j]
            in_used[j] += m[i, j]
for s, sz in enumerate(size):
    for k, (t, h) in enumerate(zip(tops(sz), sz)):
        ax.add_patch(Rectangle((s - BAR_W / 2, t - h), BAR_W, h, fc=DARK[k], ec="black", lw=1.3, zorder=4))
for frac in (0.25, 0.5, 0.75, 1.0):
    ax.axhline(total * frac, color="black", lw=0.7, ls=(0, (4, 3)), zorder=3)
ax.set_xlim(-0.25, len(STAGES) - 0.75); ax.set_ylim(-1, total + 1)
ax.set_xticks(range(len(STAGES)), STAGES, fontsize=10)
ax.set_yticks([])
ax.tick_params(bottom=False, pad=8)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.set_title("(b) Place-based policies perspective", fontweight="bold", fontsize=11, pad=8)
fig.legend(handles=[Patch(fc=c, ec="black", lw=0.9, label=l) for c, l in zip(DARK, CLASSES)], loc="lower center",
           ncol=3, frameon=False, fontsize=9.5, handlelength=1.3, bbox_to_anchor=(0.5, 0.015))

fig.text(0.995, 0.006, "Simulated data", ha="right", va="bottom", fontsize=6.5, color="#b0461e")
fig.savefig(OUT, dpi=300)
print(OUT)
