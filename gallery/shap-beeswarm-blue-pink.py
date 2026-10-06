"""SHAP beeswarm with a soft blue-to-pink ramp, dotted row guides and interaction terms among the features.

Drawn after exemplar 7685755729743810175_0001 (a cropped screen recording; structure and colour idea only).

*** SIMULATED DATA *** generated below with a fixed seed. Replace `shap` and `fval`
with your model's SHAP values and feature values (samples x features).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

OUT = Path(__file__).with_suffix(".png")
CMAP = LinearSegmentedColormap.from_list("blue_pink", ["#1b6fae", "#33b3e3", "#dfeaf2", "#f5b5bb", "#e5303d"])
NAMES = ["den x GEO", "struc", "struc x GEO", "tech", "gov", "energy", "tech x GEO", "energy x GEO",
         "gov x GEO", "pgdp x GEO", "open x GEO", "pgdp", "urban", "urban x GEO"]

rng = np.random.default_rng(3)
n_obs, n_feat = 420, len(NAMES)
scale = np.linspace(1.0, 0.18, n_feat)
fval = rng.normal(size=(n_obs, n_feat))
sign = rng.choice([1, -1], n_feat)
shap = (sign * fval * 0.55 + rng.standard_t(4, size=(n_obs, n_feat)) * 0.35) * scale * 0.012

plt.rcParams.update({"font.family": "Times New Roman", "font.size": 9, "pdf.fonttype": 42})
fig, ax = plt.subplots(figsize=(5.6, 5.2))
fig.subplots_adjust(left=0.2, right=0.86, top=0.97, bottom=0.1)
y = np.arange(n_feat)[::-1]
edges = np.linspace(shap.min(), shap.max(), 120)
for j, yi in enumerate(y):
    ax.axhline(yi, color="#cfcfcf", lw=0.6, ls=(0, (1, 3)), zorder=0)
    b = np.digitize(shap[:, j], edges)
    off = np.zeros(n_obs)
    for k in np.unique(b):                      # stack points that share an x-bin symmetrically about the row
        idx = np.where(b == k)[0]
        off[idx] = (np.arange(len(idx)) - (len(idx) - 1) / 2) * 0.03
    sc = ax.scatter(shap[:, j], yi + np.clip(off, -0.36, 0.36), c=fval[:, j], cmap=CMAP, vmin=-2, vmax=2,
                    s=7, linewidths=0, rasterized=True)
ax.axvline(0, color="#8a8a8a", lw=1.0, zorder=1)
ax.set_yticks(y, NAMES, fontweight="bold")
ax.tick_params(left=False)
ax.set_ylim(-0.7, n_feat - 0.3)
ax.set_xlabel("SHAP value (impact on model output)", fontweight="bold")
for s in ("left", "top", "right"):
    ax.spines[s].set_visible(False)

cax = fig.add_axes([0.9, 0.1, 0.014, 0.87])
cb = fig.colorbar(sc, cax=cax, ticks=[])
cb.outline.set_visible(False)
cb.set_label("Feature value", rotation=-90, labelpad=12, fontweight="bold")
cax.text(0.5, 1.008, "High", transform=cax.transAxes, ha="center", va="bottom", fontsize=8)
cax.text(0.5, -0.008, "Low", transform=cax.transAxes, ha="center", va="top", fontsize=8)

fig.text(0.995, 0.008, "Simulated data", ha="right", va="bottom", fontsize=6.5, color="#b0461e")
fig.savefig(OUT, dpi=300)
print(OUT)
