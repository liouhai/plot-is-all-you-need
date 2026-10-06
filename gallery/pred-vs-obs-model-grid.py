"""3 x 3 predicted-versus-observed panels comparing nine models; points coloured by error, one panel highlighted.

Drawn after exemplar 7687044694454529363_0001 (layout, marks, palette, metric boxes, the red highlighted panel).

*** SIMULATED DATA *** generated below with a fixed seed. Replace `MODELS` and the per-model
observed / predicted arrays for the training and test sets.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize

OUT = Path(__file__).with_suffix(".png")
MODELS = ["Random Forest", "RF-AdaBoost", "RF-Bagging", "RF-ET Stacking", "Hybrid RF-SVR", "RF-HGB Stacking",
          "Extra Trees", "Gradient Boosting", "Hist-GBDT"]
HIGHLIGHT = 4                      # index of the panel to pick out in red
BAND = 0.39                        # tolerance band around the 1:1 line
GOLD, NAVY, PURPLE, RED = "#e8a917", "#1b2a5c", "#7c5cc4", "#d1242f"

rng = np.random.default_rng(42)
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 5.6, "pdf.fonttype": 42, "axes.linewidth": 1.0})
fig, axes = plt.subplots(3, 3, figsize=(6.6, 6.4))
fig.subplots_adjust(left=0.055, right=0.955, top=0.972, bottom=0.05, wspace=0.42, hspace=0.3)
norm = Normalize(0, 1)
for k, (ax, model) in enumerate(zip(axes.ravel(), MODELS)):
    noise_tr, noise_te = rng.uniform(0.07, 0.15), rng.uniform(0.18, 0.26)
    stats = []
    for obs_n, noise, marker, size, alpha, line in ((420, noise_tr, "o", 6, 0.55, GOLD), (140, noise_te, "^", 8, 0.75, NAVY)):
        obs = rng.uniform(9.4, 13.9, obs_n)
        pred = 0.96 * obs + 0.45 + rng.normal(0, noise, obs_n) * (1 + 1.5 * (rng.random(obs_n) < 0.04))
        err = np.abs(pred - obs)
        sc = ax.scatter(obs, pred, c=err, cmap="RdYlBu_r", norm=norm, marker=marker, s=size, alpha=alpha, linewidths=0, zorder=3)
        slope, icpt = np.polyfit(obs, pred, 1)
        ax.plot([9, 14.3], [slope * 9 + icpt, slope * 14.3 + icpt], color=line, lw=0.9, zorder=4)
        r2 = 1 - ((pred - obs) ** 2).sum() / ((obs - obs.mean()) ** 2).sum()
        stats.append(f"MAE = {err.mean():.3f}\nRMSE = {np.sqrt((err ** 2).mean()):.3f}\n$R^2$ = {r2:.3f}\nY = {slope:.3f}X + {icpt:.3f}")
    ax.plot([9, 14.3], [9, 14.3], color="black", lw=0.8, zorder=2)
    for d in (-BAND, BAND):
        ax.plot([9, 14.3], [9 + d, 14.3 + d], color=PURPLE, lw=0.6, ls=(0, (3, 2)), zorder=2)
    ax.set_xlim(9.4, 14.1); ax.set_ylim(9.4, 14.1); ax.set_aspect("equal")
    ax.grid(color="#dcdcdc", lw=0.4, ls=(0, (1, 2)))
    ax.set_axisbelow(True)
    ax.set_title(f"({'abcdefghi'[k]}) {model} Model", fontweight="bold", fontsize=6.4, pad=3)
    ax.set_xlabel("Observed DO (mg/L)", labelpad=1.5)
    ax.set_ylabel("Predicted DO (mg/L)", labelpad=1.5)
    ax.tick_params(length=2, pad=1.5)
    hot = k == HIGHLIGHT
    ax.text(0.97, 0.03, "Training\n" + stats[0] + "\n\nTesting\n" + stats[1], transform=ax.transAxes, ha="right", va="bottom",
            fontsize=4.6, color=RED if hot else "black", linespacing=1.15, zorder=6,
            bbox=dict(boxstyle="round,pad=0.35", fc="#f6f6f6", ec=RED if hot else "#9a9a9a", lw=0.7 if hot else 0.5))
    handles = [plt.Line2D([], [], marker="o", ls="", color="#7d8bb5", ms=2.5, label="Training"),
               plt.Line2D([], [], marker="^", ls="", color="#7d8bb5", ms=2.8, label="Testing"),
               plt.Line2D([], [], color="black", lw=0.8, label="1:1 line"),
               plt.Line2D([], [], color=PURPLE, lw=0.6, ls=(0, (3, 2)), label=f"Error ≤ {BAND}"),
               plt.Line2D([], [], color=GOLD, lw=0.9, label="Train fit"), plt.Line2D([], [], color=NAVY, lw=0.9, label="Test fit")]
    ax.legend(handles=handles, loc="upper left", fontsize=4.4, frameon=True, fancybox=False, edgecolor="#555555",
              borderpad=0.5, labelspacing=0.3, handlelength=1.8).get_frame().set_linewidth(0.5)
    cax = ax.inset_axes([1.04, 0, 0.045, 1])
    cb = fig.colorbar(sc, cax=cax)
    cb.solids.set_alpha(1)
    cb.ax.tick_params(length=1.5, pad=1, labelsize=4.6)
    cb.outline.set_linewidth(0.5)
    cax.set_title("Error", fontsize=4.8, pad=2)

fig.text(0.995, 0.005, "Simulated data", ha="right", va="bottom", fontsize=6.5, color="#b0461e")
fig.savefig(OUT, dpi=300)
print(OUT)
