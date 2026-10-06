"""Two circular interaction networks over a SHAP waterfall drawn with arrow-shaped bars.

Drawn after exemplar 7682454731897228585_0032 (layout, marks, the two colourways).

*** SIMULATED DATA *** generated below with a fixed seed. Replace `importance`, `inter` (symmetric
feature-by-feature interaction strength) and `contrib` (one sample's SHAP values) with your own.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Patch, Polygon

OUT = Path(__file__).with_suffix(".png")
NAMES = ["vap", "pre", "temp", "lat", "relief", "slope", "elev", "urb", "nlgt", "hfi", "pop", "gdp",
         "raildst", "portdst", "lakedst", "rvrdst", "ctrdst", "capdst", "pet"]
WAYS = [(LinearSegmentedColormap.from_list("g", ["#b9e2b0", "#3fa55a", "#00441b"]),                # node ramp, edge ramp
         LinearSegmentedColormap.from_list("p", ["#d9d0ec", "#9b84cc", "#4b1d91"])),
        (LinearSegmentedColormap.from_list("b", ["#bcd7ec", "#4a93c7", "#08306b"]),
         LinearSegmentedColormap.from_list("o", ["#fbd3ae", "#f08a3c", "#8a2d04"]))]
RED, BLUE = "#d9534f", "#4f81bd"

rng = np.random.default_rng(21)
n = len(NAMES)
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 7, "pdf.fonttype": 42, "axes.linewidth": 1.0})
fig = plt.figure(figsize=(6.2, 6.6))

# --- top: two networks, same layout, different data and colourway
ang = np.pi / 2 - 2 * np.pi * np.arange(n) / n
px, py = np.cos(ang), np.sin(ang)
for k, (node_cmap, edge_cmap) in enumerate(WAYS):
    ax = fig.add_axes([0.015 + 0.49 * k, 0.535, 0.48, 0.48 * 6.2 / 6.6 * 2.6 / 2.9])
    importance = rng.gamma(2.0, 5.0, n)
    inter = np.triu(rng.gamma(0.6, 0.5, (n, n)), 1)
    inter[rng.integers(0, n // 2), rng.integers(n // 2, n)] = 2.6          # a few dominant pairs
    inter[rng.integers(0, n // 2), rng.integers(n // 2, n)] = 2.2
    enorm, nnorm = Normalize(0, inter.max()), Normalize(0, importance.max())
    for i, j in sorted(zip(*np.nonzero(inter)), key=lambda ij: inter[ij]):   # strongest edges on top
        v = inter[i, j]
        ax.plot([px[i], px[j]], [py[i], py[j]], color=edge_cmap(enorm(v)), lw=0.3 + 3.2 * enorm(v) ** 2,
                alpha=0.55 + 0.45 * enorm(v), solid_capstyle="round", zorder=1 + v)
    ax.scatter(px, py, s=20 + 70 * nnorm(importance), c=importance, cmap=node_cmap, norm=nnorm, vmin=None,
               edgecolors="none", zorder=10)
    for name, a in zip(NAMES, ang):
        ax.text(1.1 * np.cos(a), 1.1 * np.sin(a), name, fontsize=6.5, va="center",
                ha="left" if np.cos(a) > 0.25 else "right" if np.cos(a) < -0.25 else "center")
    ax.set_xlim(-1.45, 1.45); ax.set_ylim(-1.3, 1.3); ax.axis("off")
    ax.text(-1.45, 1.3, f"({'ab'[k]}) Impact intensity", fontsize=8, va="top")
    for m, (cmap, norm, title, ends) in enumerate(((node_cmap, nnorm, "Importance", "Low  →  High"),
                                                   (edge_cmap, enorm, "Interaction intensity", "Weak  →  Strong"))):
        cax = fig.add_axes([0.07 + 0.49 * k + 0.2 * m, 0.5, 0.15, 0.008])
        cb = fig.colorbar(ScalarMappable(norm, cmap), cax=cax, orientation="horizontal")
        cb.outline.set_visible(False)
        cb.ax.tick_params(length=2, labelsize=5.5, pad=1)
        cb.ax.locator_params(nbins=3)
        cax.set_title(f"{title}\n{ends}", fontsize=5.5, pad=2)

# --- bottom: waterfall with arrow bars, largest contributions first
ax = fig.add_axes([0.1, 0.105, 0.8, 0.33])
contrib = rng.normal(0, 1, n) * np.linspace(2.4, 0.15, n)
contrib[0], contrib[1] = -2.9, -1.4
order = np.argsort(-np.abs(contrib))
base, w = 572.66, 0.52
level = base
for x, i in enumerate(order):
    v0, v1 = level, level + contrib[i]
    tip = np.sign(contrib[i]) * min(abs(contrib[i]) * 0.45, 0.28)
    ax.add_patch(Polygon([(x - w / 2, v0), (x + w / 2, v0), (x + w / 2, v1 - tip), (x, v1), (x - w / 2, v1 - tip)],
                         fc=RED if contrib[i] > 0 else BLUE, ec="black", lw=0.6, zorder=3))
    if x < n - 1:
        ax.plot([x, x + 1], [v1, v1], color="#555555", lw=0.5, ls=(0, (3, 2)), zorder=2)
    level = v1
ax.set_xlim(-0.8, n - 0.2)
ax.set_xticks(range(n), [NAMES[i] for i in order], rotation=90)
ax.grid(axis="x", color="#e3e3e3", lw=0.5)
ax.set_axisbelow(True)
ax.yaxis.tick_right()
ax.yaxis.set_label_position("right")
ax.set_ylabel("SHAP value")
ax.margins(y=0.08)
box = dict(boxstyle="square,pad=0.3", fc="white", ec="black", lw=0.7)
ax.text(-0.045, 0.5, f"E[f(x)] = {base:.2f}", transform=ax.transAxes, rotation=90, ha="center", va="center", bbox=box)
ax.text(0.975, 0.5, f"f(x) = {level:.2f}", transform=ax.transAxes, rotation=90, ha="center", va="center", bbox=box)
fig.legend(handles=[Patch(fc=RED, ec="black", lw=0.5, label="Positive"), Patch(fc=BLUE, ec="black", lw=0.5, label="Negative")],
           loc="lower center", ncol=2, frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, 0.0), title="Impact direction",
           title_fontproperties={"weight": "bold", "size": 7.5})

fig.text(0.995, 0.006, "Simulated data", ha="right", va="bottom", fontsize=6.5, color="#b0461e")
fig.savefig(OUT, dpi=300)
print(OUT)
