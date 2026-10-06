"""Upper-triangle bubble matrix: size and colour both encode the value, legend tucked into the empty corner.

Drawn after exemplar 7685907497739889910_0008 (one of its six colourways; swap CMAP for the others).

*** SIMULATED DATA *** generated below with a fixed seed. Replace `names` and `val`
(a symmetric variable-by-variable matrix of non-negative strengths).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, Normalize

OUT = Path(__file__).with_suffix(".png")
CMAP = LinearSegmentedColormap.from_list("blue_white_red", ["#2a2ad0", "#9aa0ee", "#f7f4f4", "#f09a8c", "#c8141e"])
names = ["SLOPE", "PRE", "LST", "MAOC", "GST", "NOC", "ST", "TEM", "POC", "PH", "SRDS", "SWC", "DEM", "WS", "ASPECT"]

rng = np.random.default_rng(8)
n = len(names)
val = np.triu(rng.gamma(0.5, 0.35, (n, n)), 1)
val[0, 1:5] = [7.0, 5.6, 4.1, 3.3]; val[1, 2:5] = [4.7, 3.6, 2.4]; val[2, 3:5] = [2.9, 1.6]     # strong cluster at top-left
norm = Normalize(0, val.max())
size = lambda v: 6 + 150 * norm(v)

plt.rcParams.update({"font.family": "Times New Roman", "font.size": 7.5, "font.weight": "bold", "pdf.fonttype": 42,
                     "axes.linewidth": 1.6})
fig, ax = plt.subplots(figsize=(5.0, 4.9))
fig.subplots_adjust(left=0.14, right=0.97, top=0.97, bottom=0.15)
i, j = np.triu_indices(n, 1)
ax.scatter(j, i, s=size(val[i, j]), c=val[i, j], cmap=CMAP, norm=norm, edgecolors="#333333", linewidths=0.35, zorder=3)
ax.set_xlim(-0.6, n - 0.4); ax.set_ylim(n - 0.4, -0.6)
ax.set_xticks(range(n), names, rotation=45, ha="right", rotation_mode="anchor")
ax.set_yticks(range(n), names)
ax.grid(color="#e4e4e4", lw=0.5)
ax.set_axisbelow(True)
ax.tick_params(length=2.5)
ax.text(1.0, 2.2, "(a)", fontsize=9)
ax.set_ylabel("Driving factor")

# legend in the empty lower-left corner: a colour bar and a column of size samples for the same values
ticks = np.round(np.linspace(0, val.max(), 4), 1)
ax.text(0.0, 6.6, "Interaction strength", fontsize=7)
cax = ax.inset_axes([0.6, 7.3, 0.55, 6.2], transform=ax.transData)
cb = fig.colorbar(ScalarMappable(norm, CMAP), cax=cax, ticks=[])
cb.outline.set_linewidth(0.6)
for t in ticks:
    yy = 13.5 - 6.2 * norm(t)
    ax.scatter(2.3, yy, s=size(t), c=[CMAP(norm(t))], edgecolors="#333333", linewidths=0.35, zorder=3, clip_on=False)
    ax.text(3.0, yy, f"{t:.1f}", va="center", fontsize=6.5)

fig.text(0.995, 0.006, "Simulated data", ha="right", va="bottom", fontsize=6.5, color="#b0461e", fontweight="normal")
fig.savefig(OUT, dpi=300)
print(OUT)
