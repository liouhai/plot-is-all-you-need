"""Ranked feature-importance bars with an inset rose ring and a legend that doubles as a glossary.

Drawn after exemplar 7662738394782518543_0001 (all six parts).
Data: random-forest feature importance on scikit-learn's public diabetes dataset.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle

DATA = Path(__file__).with_suffix(".csv")  # columns: feature, full_name, importance
OUT = Path(__file__).with_suffix("")
XLABEL = "Feature importance (mean decrease in impurity)"

# colour ramp sampled from the exemplar's bars, top (largest) to bottom (smallest)
RAMP = ["#d53e51", "#e77a7d", "#eb8487", "#f2afaa", "#e4bfc5", "#dbcddb", "#d4d8e9", "#8cb2ce"]

plt.rcParams.update({"font.family": "Times New Roman", "font.size": 7, "pdf.fonttype": 42,
                     "axes.linewidth": 1.2, "mathtext.fontset": "stix"})

df = pd.read_csv(DATA).sort_values("importance", ascending=False).reset_index(drop=True)
n = len(df)
share = df.importance / df.importance.sum()
cmap = LinearSegmentedColormap.from_list("ramp", RAMP)
colors = [cmap(i / (n - 1)) for i in range(n)]

fig = plt.figure(figsize=(7.2, 3.9))  # double-column width, exemplar aspect
ax = fig.add_axes([0.065, 0.13, 0.64, 0.84])

# --- ranked bars
y = np.arange(n)[::-1]
xmax = df.importance.max() * 1.1
ax.barh(y, df.importance, height=0.6, color=colors, zorder=3)
for yi, v in zip(y, df.importance):
    label = ax.text(v + xmax * 0.012, yi, f"{v:.3f}", va="center", ha="left", fontsize=7, zorder=4)
    ax.plot([v + xmax * 0.07, xmax], [yi, yi], ls=(0, (4, 3)), lw=0.5, color="#cfcfcf", zorder=1)
ax.set_yticks(y, df.feature, fontweight="bold")
ax.set_xlim(0, xmax)
ax.set_ylim(-0.7, n - 0.3)
ax.set_xlabel(XLABEL, fontsize=9, fontweight="bold", labelpad=3)
ax.tick_params(axis="x", width=1.2, length=3, labelsize=7.5)
ax.tick_params(axis="y", length=0, pad=4)
for lab in ax.get_xticklabels():
    lab.set_fontweight("bold")
ax.spines[["top", "right"]].set_visible(False)

# --- inset rose ring: angle and radius both follow the share, largest wedge pulled out
ring = fig.add_axes([0.375, 0.115, 0.35, 0.65], projection="polar")
ring.set_theta_offset(np.pi / 2)
ring.set_theta_direction(1)
width = share.to_numpy() * 2 * np.pi
theta = np.cumsum(width) - width / 2
r0 = 0.28
outer = r0 + 0.2 + 0.52 * share / share.max()
lift = np.where(np.arange(n) == 0, 0.035, 0.0)  # pull the largest wedge out
ring.bar(theta, outer - r0, width=width, bottom=r0 + lift, color=colors, edgecolor="white", linewidth=0.9, zorder=3)
placed = []  # label boxes already drawn, in ring-radius units, so thin neighbouring wedges do not collide
for t, r, s in zip(theta, outer + lift, share):
    a = np.pi / 2 + t  # angle on the page
    rl = r + 0.07
    while any(abs(rl * np.cos(a) - px) < 0.27 and abs(rl * np.sin(a) - py) < 0.12 for px, py in placed):
        rl += 0.04
    placed.append((rl * np.cos(a), rl * np.sin(a)))
    if rl > r + 0.12:
        ring.plot([t, t], [r + 0.02, rl - 0.03], color="#888888", lw=0.4, zorder=4)
    ring.text(t, rl, f"{s:.1%}", fontsize=6.5, fontweight="bold", zorder=5,
              ha="left" if np.cos(a) > 0.02 else "right" if np.cos(a) < -0.3 else "center",
              va="bottom" if np.sin(a) > 0.5 else "top" if np.sin(a) < -0.5 else "center")
ring.set_ylim(0, 1.3)
ring.axis("off")

# --- legend column: gradient strip + one entry per feature (swatch, short name, full name)
strip = fig.add_axes([0.735, 0.13, 0.02, 0.80])
strip.imshow(np.linspace(0, 1, 256)[:, None], aspect="auto", cmap=cmap, origin="upper")
strip.axis("off")
lg = fig.add_axes([0.765, 0.13, 0.23, 0.80])
lg.set_xlim(0, 1)
lg.set_ylim(0, 1)
lg.axis("off")
lg.text(0.02, 1.012, "High importance", fontsize=7.5, fontweight="bold", va="bottom")
lg.text(0.02, -0.012, "Low importance", fontsize=7.5, fontweight="bold", va="top")
step = 1 / n
for i, row in df.iterrows():
    top = 1 - i * step
    lg.add_patch(Rectangle((0.02, top - 0.042), 0.12, 0.042, color=colors[i], lw=0))
    lg.text(0.17, top - 0.021, f"{row.feature}:", fontsize=7.5, fontweight="bold", va="center")
    lg.text(0.02, top - 0.072, row.full_name, fontsize=6.8, va="center")

fig.savefig(f"{OUT}.png", dpi=300)
fig.savefig(f"{OUT}.pdf")
print(OUT)
