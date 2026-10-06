"""Ranked horizontal bars, each split into two contributions, under a ruled title.

Drawn after exemplar 7685755729743810175_0002 (a cropped screen recording; structure and colour idea only).

*** SIMULATED DATA *** generated below with a fixed seed. Replace `names`, `part_a`, `part_b`.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).with_suffix(".png")
BLUE, PINK = "#29b6e6", "#f2a59d"
LABELS = ("Main effect", "Interaction with location")

rng = np.random.default_rng(11)
names = ["den", "struc", "tech", "gov", "energy", "pgdp", "open", "urban", "invest", "trade"]
total = np.array([0.0190, 0.0142, 0.0062, 0.0026, 0.0025, 0.0023, 0.0010, 0.0005, 0.0003, 0.0002])
frac_a = np.array([0.0, 0.67, 0.70, 0.52, 0.50, 0.55, 0.0, 0.0, 0.0, 0.0])      # the smallest bars have one part only
part_a, part_b = total * frac_a, total * (1 - frac_a)

plt.rcParams.update({"font.family": "Times New Roman", "font.size": 9, "pdf.fonttype": 42, "axes.linewidth": 1.1})
fig, ax = plt.subplots(figsize=(5.2, 4.6))
fig.subplots_adjust(left=0.13, right=0.97, top=0.9, bottom=0.12)
y = np.arange(len(names))[::-1]
ax.barh(y, part_a, height=0.62, color=BLUE, label=LABELS[0])
ax.barh(y, part_b, left=part_a, height=0.62, color=PINK, label=LABELS[1])
ax.set_yticks(y, names, fontweight="bold")
ax.tick_params(left=False)
ax.set_xlim(0, total.max() * 1.04)
ax.set_xlabel("mean(|SHAP value|)", fontweight="bold")
for s in ("left", "top", "right"):
    ax.spines[s].set_visible(False)
for lab in ax.get_xticklabels():
    lab.set_fontweight("bold")
ax.legend(loc="lower right", frameon=False, fontsize=8.5, handlelength=1.2, handleheight=1.0)

# title sits under a full-width rule, as in the exemplar
fig.lines.append(plt.Line2D([0.13, 0.97], [0.955, 0.955], transform=fig.transFigure, color="black", lw=1.1))
fig.text(0.55, 0.945, "Global Feature Contribution Rank", ha="center", va="top", fontweight="bold", fontsize=10)

fig.text(0.995, 0.008, "Simulated data", ha="right", va="bottom", fontsize=6.5, color="#b0461e")
fig.savefig(OUT, dpi=300)
print(OUT)
