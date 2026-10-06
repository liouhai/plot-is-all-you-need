"""SHAP importance bars and beeswarm back to back on a shared feature spine, with an inset spiral rose.

Drawn after exemplar 7526596960389877027_0001 (layout, marks, palette, colour bars).
Changed from the exemplar: feature names sit outside short bars instead of on top of them.

*** SIMULATED DATA *** generated below with a fixed seed. Replace `imp`, `shap` and `fval`
with your own model's output (importance per feature; SHAP value and feature value per sample).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Wedge

OUT = Path(__file__).with_suffix(".png")
CMAP = LinearSegmentedColormap.from_list("blue_purple_red", ["#0a0af0", "#4a0fa8", "#8f1068", "#d01030", "#ff1414"])
NAMES = ["Primary industry share of GDP", "Local fiscal budget revenue", "Secondary industry added value", "GDP",
         "Students in higher education", "Retail sales of commodities", "Regular secondary schools",
         "Balance of current assets", "Total profit", "Value-added tax due", "Railway passenger volume",
         "Total salary of workers", "Vegetable production", "Average salary of workers", "Road freight volume"]

rng = np.random.default_rng(7)
n_feat, n_obs = len(NAMES), 260
imp = 0.77 * np.array([1, .85, .66, .60, .53, .27, .18, .155, .15, .135, .13, .125, .12, .115, .10])
fval = rng.normal(size=(n_obs, n_feat))                                  # standardised feature values
sign = np.where(np.arange(n_feat) % 4 == 2, -1, 1)
shap = fval * sign * imp * 1.6 + rng.normal(scale=0.12, size=(n_obs, n_feat)) * imp ** 0.5
share = imp / imp.sum()

plt.rcParams.update({"font.family": "Times New Roman", "font.size": 7.5, "pdf.fonttype": 42, "axes.linewidth": 1.0})
fig = plt.figure(figsize=(7.2, 4.6))
axl = fig.add_axes([0.095, 0.10, 0.49, 0.86])
axr = fig.add_axes([0.585, 0.10, 0.325, 0.86], sharey=axl)
y = np.arange(n_feat)[::-1]
colour = CMAP(imp / imp.max())

# --- left: importance bars growing leftwards from the spine
axl.barh(y, imp, height=0.6, color=colour)
for yi, v, name in zip(y, imp, NAMES):
    inside = v > 0.42 * imp.max()
    axl.text(0.006 if inside else v + 0.008, yi, name, ha="right", va="center",
             color="white" if inside else "black", fontsize=7)
axl.set_xlim(imp.max() * 1.07, 0)
axl.set_ylim(-0.8, n_feat - 0.3)
axl.set_yticks([])
axl.set_xlabel(r"Contribution to carbon emissions (10$^4$ t)")
for s in ("left", "top"):
    axl.spines[s].set_visible(False)
axl.spines["bottom"].set_linestyle((0, (1, 2)))
axl.text(0.02, 0.985, "(a)", transform=axl.transAxes, fontweight="bold", va="top")

# --- right: beeswarm, points coloured by feature value
edges = np.linspace(shap.min(), shap.max(), 150)
for j, yi in enumerate(y):
    b = np.digitize(shap[:, j], edges)
    off = np.zeros(n_obs)
    for k in np.unique(b):                      # stack points that share an x-bin symmetrically about the row
        idx = np.where(b == k)[0]
        off[idx] = (np.arange(len(idx)) - (len(idx) - 1) / 2) * 0.042
    axr.scatter(shap[:, j], yi + np.clip(off, -0.38, 0.38), c=fval[:, j], cmap=CMAP, vmin=-2, vmax=2,
                s=1.6, linewidths=0, rasterized=True)
axr.axvline(0, color="#9a9a9a", lw=0.7, zorder=0)
axr.set_xlim(-3.3, 3.3)
axr.set_xticks([-2, 0, 2])
axr.set_xlabel("SHAP value (impact on model output)")
axr.tick_params(left=False, labelleft=False)
for s in ("top", "right"):
    axr.spines[s].set_visible(False)
axr.text(0.93, 0.985, "(b)", transform=axr.transAxes, fontweight="bold", va="top")

# --- full-height colour strips at both ends, labelled only High / Low
grad = np.linspace(1, 0, 256)[:, None]
for x0, label, side in ((0.04, "Contribution", "left"), (0.935, "Feature value", "right")):
    cax = fig.add_axes([x0, 0.10, 0.008, 0.86])
    cax.imshow(grad, aspect="auto", cmap=CMAP)
    cax.set_xticks([]); cax.set_yticks([])
    for s in cax.spines.values():
        s.set_visible(False)
    cax.text(0.5, 1.012, "High", transform=cax.transAxes, ha="center", va="bottom")
    cax.text(0.5, -0.012, "Low", transform=cax.transAxes, ha="center", va="top")
    cax.text(-1.9 if side == "left" else 3.2, 0.5, label, transform=cax.transAxes, rotation=90 if side == "left" else -90,
             ha="center", va="center")

# --- inset spiral rose: equal angles, radius grows as the share shrinks, coloured band width follows the share
rose = fig.add_axes([0.075, 0.115, 0.27, 0.27 * 7.2 / 4.6])
rose.set_xlim(-1.25, 1.25); rose.set_ylim(-1.25, 1.25); rose.set_aspect("equal"); rose.axis("off")
step = 360 / n_feat
for i in range(n_feat):
    a1 = 90 - i * step                          # start at 12 o'clock, go clockwise
    r = 0.52 + 0.48 * i / (n_feat - 1)
    band = 0.10 + 0.9 * share[i]
    rose.add_patch(Wedge((0, 0), r, a1 - step + 1.5, a1 - 1.5, width=r - 0.16, fc="#e9e9ee", ec="none"))
    rose.add_patch(Wedge((0, 0), r, a1 - step + 1.5, a1 - 1.5, width=band, fc=colour[i], ec="white", lw=0.4))
    mid = np.radians(a1 - step / 2)
    rose.text((r + 0.15) * np.cos(mid), (r + 0.15) * np.sin(mid), f"{share[i] * 100:.1f}%", fontsize=5.5,
              ha="center", va="center")

fig.text(0.995, 0.008, "Simulated data", ha="right", va="bottom", fontsize=6.5, color="#b0461e")
fig.savefig(OUT, dpi=270)
print(OUT)
