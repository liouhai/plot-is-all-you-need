"""Grouped stacked bars built from rounded blocks, totals on top, a dashed empty frame for a missing part.

Drawn after exemplar 7688722519456743145_0020 (layout, marks, palette, legend box, the dashed outer frame).

*** SIMULATED DATA *** below. Replace `BARS` (scenario, bar name, {component: value}) and `MISSING`.
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch

OUT = Path(__file__).with_suffix(".png")
COLORS = {"Policy A base": "#4f8ef7", "Policy B base": "#f9f0b0", "Policy C base": "#a8e6cf", "Overlap (green)": "#8fbc9a",
          "Overlap (coral)": "#f58a8a", "Overlap (lavender)": "#c6c3f5", "Synergy bonus": "#a5e6ea"}
MISSING_COLOR = "#2e9e6b"
BARS = [("One policy (A / B / C)", "Policy A", {"Policy A base": 22, "Overlap (green)": 7, "Overlap (coral)": 9, "Synergy bonus": 10}),
        ("One policy (A / B / C)", "Policy B", {"Policy B base": 30, "Overlap (green)": 8, "Overlap (lavender)": 8, "Synergy bonus": 8}),
        ("One policy (A / B / C)", "Policy C", {"Policy C base": 36, "Overlap (coral)": 9, "Overlap (lavender)": 8, "Synergy bonus": 7}),
        ("Two policies (A ∪ B)", "Trade-offs", {"Policy A base": 20, "Policy B base": 26, "Overlap (coral)": 7, "Overlap (lavender)": 6, "Synergy bonus": 5}),
        ("Two policies (A ∪ B)", "Unrelated", {"Policy A base": 22, "Policy B base": 28, "Overlap (coral)": 10, "Overlap (lavender)": 9, "Synergy bonus": 9}),
        ("Two policies (A ∪ B)", "Synergies", {"Policy A base": 22, "Policy B base": 28, "Overlap (green)": 8, "Overlap (coral)": 9, "Overlap (lavender)": 9, "Synergy bonus": 10}),
        ("Three policies (A ∪ B ∪ C)", "Trade-offs", {"Policy A base": 20, "Policy B base": 26, "Policy C base": 30, "Overlap (coral)": 7}),
        ("Three policies (A ∪ B ∪ C)", "Unrelated", {"Policy A base": 22, "Policy B base": 28, "Policy C base": 34, "Overlap (green)": 8, "Overlap (lavender)": 10, "Synergy bonus": 12}),
        ("Three policies (A ∪ B ∪ C)", "Synergies", {"Policy A base": 22, "Policy B base": 28, "Policy C base": 34, "Overlap (green)": 9, "Overlap (coral)": 10, "Overlap (lavender)": 11, "Synergy bonus": 16})]
MISSING = {6: 7}                                 # bar index -> size of the part that is absent, drawn as an empty dashed frame
W, GAP = 0.5, 1.6                                # bar width, vertical gap between blocks (data units)

plt.rcParams.update({"font.family": ["Avenir Next", "Helvetica Neue", "Arial", "DejaVu Sans"], "font.size": 7.5, "pdf.fonttype": 42})
fig, ax = plt.subplots(figsize=(6.4, 4.3))
fig.subplots_adjust(left=0.08, right=0.975, top=0.97, bottom=0.18)


def block(x, y, h, **kw):
    ax.add_patch(FancyBboxPatch((x - W / 2 + 0.05, y), W - 0.1, h, boxstyle="round,pad=0,rounding_size=0.05",
                                mutation_aspect=28, **kw))


xs, centres, scenario_names = [], {}, []
for k, (scenario, name, parts) in enumerate(BARS):
    x = k + (k // 3) * 0.9
    xs.append(x)
    centres.setdefault(scenario, []).append(x)
    y = 0
    for comp, v in parts.items():
        h = max(v - GAP, 0.8)
        block(x + 0.03, y - 0.5, h, fc="#000000", ec="none", alpha=0.07, zorder=1)             # shadow
        block(x, y, h, fc=COLORS[comp], ec="none", zorder=2)
        y += v
    if k in MISSING:
        block(x, y, MISSING[k] - GAP, fc="none", ec=MISSING_COLOR, lw=1.1, ls=(0, (3, 2)), zorder=2)
        y += MISSING[k]
    ax.text(x, y + 1.5, f"{sum(parts.values())}", ha="center", va="bottom", fontweight="bold", fontsize=8)
ax.set_xticks(xs, [b[1] for b in BARS])
ax.set_xlim(-0.8, xs[-1] + 0.8); ax.set_ylim(0, 178)
ax.set_yticks([0, 30, 60, 90, 120, 150])
ax.set_ylabel("Effect score", fontweight="bold")
ax.tick_params(length=0)
for scenario, c in centres.items():
    ax.text(sum(c) / len(c), -22, scenario, ha="center", va="top", fontweight="bold", fontsize=8)
for sp in ax.spines.values():                    # dashed grey frame instead of solid axes
    sp.set_linestyle((0, (4, 3))); sp.set_color("#9a9a9a"); sp.set_linewidth(0.8)

handles = [Patch(fc=c, label=l) for l, c in COLORS.items()] + [Patch(fc="none", ec=MISSING_COLOR, ls=(0, (3, 2)), lw=1.0, label="Trade-off: part missing")]
leg = ax.legend(handles=handles, ncol=3, loc="upper left", bbox_to_anchor=(0.015, 0.93), fontsize=6.5, handlelength=1.8,
                columnspacing=1.2, fancybox=True, edgecolor="#8a8a8a")
leg.get_frame().set_linewidth(0.8)
ax.text(0.02, 0.975, "Samples", transform=ax.transAxes, va="top", fontweight="bold", fontsize=8)
ax.text(0.14, 0.972, "(synergy and trade-off bars show only the most extreme cases)", transform=ax.transAxes, va="top", fontsize=6.5)

fig.text(0.995, 0.008, "Simulated data", ha="right", va="bottom", fontsize=6.5, color="#b0461e")
fig.savefig(OUT, dpi=300)
print(OUT)
