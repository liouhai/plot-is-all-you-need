"""One-page summary of a multi-class model: class metrics, confusion matrix, ROC curves, SHAP beeswarm, two dependence plots.

Drawn after exemplar 7667898025846508841_0001 (a phone screenshot of a seven-part collage; the set of panels and
the deep blue / deep red / purple palette are kept, the layout is regularised into a 2 x 3 grid).

*** SIMULATED DATA *** generated below with a fixed seed. Replace the arrays in each block with your model's output.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

OUT = Path(__file__).with_suffix(".png")
BLUE, RED, PURPLE = "#27348b", "#b5121b", "#7b5fb8"
DIV = LinearSegmentedColormap.from_list("blue_red", [BLUE, "#8f9bd6", "#f3f0f0", "#e08a85", RED])
SEQ = LinearSegmentedColormap.from_list("white_blue", ["#f4f5fb", "#8f9bd6", BLUE])
CLASSES = ["Class 1", "Class 2", "Class 3"]
FEATS = ["Evapotranspiration", "LST night", "Solar radiation", "LST day", "Elevation", "Cloud cover", "Slope",
         "Wind speed", "Soil moisture", "Precipitation"]

rng = np.random.default_rng(13)
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 7, "pdf.fonttype": 42, "axes.linewidth": 0.9})
fig, axes = plt.subplots(2, 3, figsize=(6.6, 4.5))
fig.subplots_adjust(left=0.115, right=0.975, top=0.94, bottom=0.11, wspace=0.46, hspace=0.5)
(a, b, c), (d, e, f) = axes
tag = lambda ax, s: ax.set_title(s, loc="left", fontweight="bold", fontsize=8, pad=4)

# (a) precision / recall / F1 per class
metrics = np.array([[0.93, 0.90, 0.91], [0.88, 0.92, 0.90], [0.95, 0.94, 0.94]])
for k, (name, col) in enumerate(zip(("Precision", "Recall", "F1"), (BLUE, RED, PURPLE))):
    a.bar(np.arange(3) + (k - 1) * 0.26, metrics[:, k], 0.24, color=col, label=name)
a.set_xticks(range(3), CLASSES); a.set_ylim(0.6, 1.0); a.set_ylabel("Score")
a.legend(ncol=3, fontsize=5.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.02), handlelength=1, columnspacing=0.8)
a.spines[["top", "right"]].set_visible(False)
tag(a, "(a) Metrics by class")

# (b) confusion matrix
cm = np.array([[412, 18, 9], [25, 388, 21], [6, 14, 431]])
b.imshow(cm, cmap=SEQ)
for i in range(3):
    for j in range(3):
        b.text(j, i, cm[i, j], ha="center", va="center", color="white" if cm[i, j] > 200 else "black", fontsize=7.5)
b.set_xticks(range(3), CLASSES); b.set_yticks(range(3), CLASSES, rotation=90, va="center")
b.set_xlabel("Predicted label"); b.set_ylabel("True label"); b.tick_params(length=0)
tag(b, "(b) Confusion matrix")

# (c) one-vs-rest ROC curves
fpr = np.linspace(0, 1, 200)
for name, col, power in zip(CLASSES, (BLUE, RED, PURPLE), (0.045, 0.07, 0.03)):
    tpr = fpr ** power
    c.plot(fpr, tpr, color=col, lw=1.2, label=f"{name} (AUC = {((tpr[1:] + tpr[:-1]) / 2 * np.diff(fpr)).sum():.3f})")
c.plot([0, 1], [0, 1], color="black", lw=0.7, ls=(0, (4, 3)))
c.set_xlabel("False positive rate"); c.set_ylabel("True positive rate")
c.legend(fontsize=5.5, frameon=False, loc="lower right")
tag(c, "(c) ROC curves")

# (d) SHAP beeswarm
n_obs = 260
scale = np.linspace(1, 0.15, len(FEATS))
fval = rng.normal(size=(n_obs, len(FEATS)))
shap = (fval * rng.choice([1, -1], len(FEATS)) * 0.7 + rng.normal(scale=0.3, size=fval.shape)) * scale
edges = np.linspace(shap.min(), shap.max(), 90)
for j in range(len(FEATS)):
    bins = np.digitize(shap[:, j], edges)
    off = np.zeros(n_obs)
    for k in np.unique(bins):
        idx = np.where(bins == k)[0]
        off[idx] = (np.arange(len(idx)) - (len(idx) - 1) / 2) * 0.07
    sc = d.scatter(shap[:, j], len(FEATS) - 1 - j + np.clip(off, -0.4, 0.4), c=fval[:, j], cmap=DIV, vmin=-2, vmax=2,
                   s=1.6, linewidths=0, rasterized=True)
d.axvline(0, color="#9a9a9a", lw=0.6, zorder=0)
d.set_yticks(range(len(FEATS)), FEATS[::-1], fontsize=5.5); d.tick_params(axis="y", length=0)
d.set_xlabel("SHAP value")
d.spines[["top", "right", "left"]].set_visible(False)
cb = fig.colorbar(sc, ax=d, pad=0.02, aspect=30, ticks=[])
cb.outline.set_visible(False)
cb.set_label("Feature value", fontsize=5.5, labelpad=2)
tag(d, "(d) Feature effects")

# (e, f) dependence plots with a smooth trend and its band
for ax, name, shape, letter in ((e, FEATS[0], lambda u: 1 / (1 + np.exp(-8 * (u - 0.45))) - 0.5, "e"),
                                (f, FEATS[1], lambda u: 0.5 - 1.2 * (u - 0.35) ** 2 * 4, "f")):
    u = np.sort(rng.random(170))
    s = shape(u) + rng.normal(scale=0.12, size=u.size)
    ax.scatter(u, s, c=s, cmap=DIV, s=8, edgecolors="white", linewidths=0.25, zorder=3)
    w = np.exp(-0.5 * ((u[:, None] - u[None]) / 0.06) ** 2)
    trend = (w * s).sum(1) / w.sum(1)
    ax.fill_between(u, trend - 0.12, trend + 0.12, color=PURPLE, alpha=0.18, lw=0, zorder=2)
    ax.plot(u, trend, color=PURPLE, lw=1.2, zorder=4)
    ax.axhline(0, color="black", lw=0.7, ls=(0, (4, 3)), zorder=1)
    ax.set_xlabel(f"{name} (scaled)"); ax.set_ylabel("SHAP value")
    tag(ax, f"({letter}) Dependence: {name}")

fig.text(0.995, 0.006, "Simulated data", ha="right", va="bottom", fontsize=6.5, color="#b0461e")
fig.savefig(OUT, dpi=295)
print(OUT)
