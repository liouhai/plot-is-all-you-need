"""3 x 3 dependence plots: points coloured by their own SHAP value, a red smooth line, a dashed zero line.

Drawn after exemplar 7685755729743810175_0003 (a cropped screen recording; structure and colour idea only).

*** SIMULATED DATA *** generated below with a fixed seed. Replace `x` and `s`
(feature value and SHAP value per sample, one column per feature).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

OUT = Path(__file__).with_suffix(".png")
CMAP = LinearSegmentedColormap.from_list("blue_pink", ["#1b6fae", "#33b3e3", "#f4f6f8", "#f5b5bb", "#e5303d"])
NAMES = ["gdp", "den", "urban", "struc", "open", "gov", "tech", "energy", "invest"]
SHAPES = [lambda u: -1.6 * u + 0.6, lambda u: 1.2 * np.exp(-6 * u) - 0.5, lambda u: 1 / (1 + np.exp(-9 * (u - 0.5))) - 0.5,
          lambda u: 0.25 * np.sin(5 * u), lambda u: 0.9 * np.exp(-((u - 0.12) / 0.12) ** 2) - 0.55 * u,
          lambda u: 0.8 * np.exp(-5 * u) - 0.45, lambda u: -0.2 + 0.5 * u, lambda u: 1 - np.exp(-14 * u) - 0.75,
          lambda u: 0.6 * (u - 0.5) ** 2 * 4 - 0.25]

rng = np.random.default_rng(5)
n = 140


def smooth(x, y, grid, bw):
    """Gaussian-kernel running mean (a stand-in for LOWESS that needs only numpy)."""
    w = np.exp(-0.5 * ((grid[:, None] - x[None]) / bw) ** 2)
    return (w * y).sum(1) / w.sum(1)


plt.rcParams.update({"font.family": "Times New Roman", "font.size": 8, "pdf.fonttype": 42, "axes.linewidth": 0.9})
fig, axes = plt.subplots(3, 3, figsize=(6.6, 5.9))
fig.subplots_adjust(left=0.09, right=0.985, top=0.965, bottom=0.085, wspace=0.42, hspace=0.36)
for ax, name, f in zip(axes.ravel(), NAMES, SHAPES):
    u = rng.beta(1.2, 2.0, n)                              # most samples at low feature values
    x = u * rng.choice([5, 60, 1.5, 4000, 250000])
    s = (f(u) + rng.normal(scale=0.12, size=n)) * 0.004
    lim = np.abs(s).max()
    ax.scatter(x, s, c=s, cmap=CMAP, norm=TwoSlopeNorm(0, -lim, lim), s=13, edgecolors="white", linewidths=0.3, zorder=3)
    grid = np.linspace(x.min(), x.max(), 200)
    ax.plot(grid, smooth(x, s, grid, (x.max() - x.min()) * 0.07), color="#d7263d", lw=1.1, zorder=4)
    ax.axhline(0, color="black", lw=1.2, ls=(0, (4, 2)), zorder=2)
    ax.set_xlabel(name, fontweight="bold", labelpad=1.5)
    ax.ticklabel_format(axis="y", style="sci", scilimits=(-3, -3), useMathText=True)
    ax.tick_params(length=2.5, pad=2)
for ax in axes[:, 0]:
    ax.set_ylabel("SHAP value", fontweight="bold")

fig.text(0.995, 0.006, "Simulated data", ha="right", va="bottom", fontsize=6.5, color="#b0461e")
fig.savefig(OUT, dpi=290)
print(OUT)
