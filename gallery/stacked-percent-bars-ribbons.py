"""100 % stacked bars joined by pale ribbons, so each component reads as a continuous band over time.

Drawn after exemplar 7686314977182892964_0001 (layout, marks, palette, labels).
Added: a legend, which the exemplar lacks.

*** SIMULATED DATA *** below. Replace `months`, `LABELS` and `pct` (rows = components, bottom to top; columns sum to 100).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

OUT = Path(__file__).with_suffix(".png")
LABELS = ["Point sources", "Sediment release", "Runoff"]                  # bottom to top
DARK = ["#f4665b", "#7f9fcb", "#fdd163"]
PALE = ["#fbb7b0", "#c3d2e6", "#fdebb9"]

months = ["Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"]
pct = np.array([[22, 30, 11, 7, 11, 27, 28, 40, 20],
                [22, 13, 10, 11, 20, 17, 23, 22, 29],
                [56, 57, 79, 82, 69, 56, 49, 38, 51]], float)

plt.rcParams.update({"font.family": "Times New Roman", "font.size": 9, "pdf.fonttype": 42, "axes.linewidth": 1.6})
fig, ax = plt.subplots(figsize=(6.0, 3.9))
fig.subplots_adjust(left=0.1, right=0.975, top=0.9, bottom=0.11)
x, w = np.arange(len(months)), 0.52
top = np.cumsum(pct, axis=0)
bot = top - pct
for k in range(len(LABELS)):
    ax.bar(x, pct[k], w, bottom=bot[k], color=DARK[k], ec="white", lw=0.6, zorder=3)
    for a in range(len(months) - 1):            # ribbon from the right edge of one bar to the left edge of the next
        ax.fill_between([x[a] + w / 2, x[a + 1] - w / 2], [bot[k, a], bot[k, a + 1]], [top[k, a], top[k, a + 1]],
                        color=PALE[k], lw=0, zorder=2)
    for xi, b, p in zip(x, bot[k], pct[k]):
        if p >= 7:
            ax.text(xi, b + p / 2, f"{p:.0f}%", ha="center", va="center", fontsize=7.5, fontweight="bold", fontstyle="italic")
ax.set_xlim(-w / 2 - 0.02, len(months) - 1 + w / 2 + 0.02)
ax.set_ylim(0, 100)
ax.set_xticks(x, months)
ax.set_ylabel("Contribution (%)")
ax.tick_params(direction="out", width=1.2)
ax.text(0.012, 0.965, "(a) WY", transform=ax.transAxes, va="top", fontweight="bold", fontsize=10, zorder=5)
ax.legend(handles=[Patch(fc=c, label=l) for c, l in zip(DARK[::-1], LABELS[::-1])], loc="lower center",
          bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False, fontsize=8.5, handlelength=1.1, columnspacing=1.6)

fig.text(0.995, 0.008, "Simulated data", ha="right", va="bottom", fontsize=6.5, color="#b0461e")
fig.savefig(OUT, dpi=300)
print(OUT)
