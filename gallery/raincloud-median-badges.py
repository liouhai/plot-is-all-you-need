"""Raincloud plot for ten groups: dots on the left, half violin on the right, the median in a round badge.

Drawn after exemplar 7688722519456743145_0014 (layout, marks, palette, the dashed outer frame).

*** SIMULATED DATA *** generated below with a fixed seed. Replace `groups` (name -> 1-D array of observations).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gaussian_kde

OUT = Path(__file__).with_suffix(".png")
COLORS = ["#0a6aa8", "#1489c4", "#12a5c8", "#3dbfe0", "#7ed0e4", "#a9e3f1", "#c9eef6", "#ea0a6e", "#f48b8b", "#74b3f0"]

rng = np.random.default_rng(2)
centres = [44, 87, 56, 95, 78, 118, 60, 107, 82, 126]
groups = {f"Group {k + 1}": rng.normal(c, rng.uniform(9, 15), 80) for k, c in enumerate(centres)}

plt.rcParams.update({"font.family": ["Avenir Next", "Helvetica Neue", "Arial", "DejaVu Sans"], "font.size": 8, "pdf.fonttype": 42})
fig, ax = plt.subplots(figsize=(6.4, 3.9))
fig.subplots_adjust(left=0.09, right=0.975, top=0.9, bottom=0.12)
for x, ((name, v), col) in enumerate(zip(groups.items(), COLORS)):
    yy = np.linspace(v.min() - 6, v.max() + 6, 200)
    dens = gaussian_kde(v)(yy)
    ax.fill_betweenx(yy, x + 0.04, x + 0.04 + dens / dens.max() * 0.36, color=col, alpha=0.9, lw=0, zorder=2)   # the cloud
    ax.scatter(x - 0.07 - rng.random(len(v)) * 0.24, v, s=3.5, color=col, linewidths=0, zorder=3)              # the rain
    med = np.median(v)
    ax.scatter(x + 0.04, med, s=120, fc="white", ec="black", lw=0.8, zorder=4)
    ax.text(x + 0.04, med, f"{med:.0f}", ha="center", va="center", fontsize=5.5, color="#d0021b", fontweight="bold", zorder=5)
ax.set_xticks(range(len(groups)), groups.keys())
ax.set_xlim(-0.6, len(groups) - 0.4); ax.set_ylim(0, 178)
ax.set_yticks([30, 60, 90, 120, 150])
ax.set_ylabel("Effect score", fontweight="bold")
ax.set_title("Policy analysis raincloud chart", fontweight="bold", fontsize=10)
ax.tick_params(length=0)
for sp in ax.spines.values():                   # dashed grey frame instead of solid axes
    sp.set_linestyle((0, (4, 3))); sp.set_color("#9a9a9a"); sp.set_linewidth(0.8)

fig.text(0.995, 0.008, "Simulated data", ha="right", va="bottom", fontsize=6.5, color="#b0461e")
fig.savefig(OUT, dpi=300)
print(OUT)
