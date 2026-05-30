"""
Standard economics diagram library.
Each function draws the canonical textbook version of a diagram type.
Returns a matplotlib Figure — caller uses st.pyplot(fig).

Philosophy: draw the standard concept diagram, not question-specific values.
The student adjusts the concept to the question's specific numbers/shifts.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Shared theme ───────────────────────────────────────────────────────────────
BG   = "#1C1C1E"
TEXT = "#E8EAED"
GRID = "#2d2d2d"
BLUE = "#8AB4F8"   # demand curves
GREEN= "#81C995"   # supply / LM / savings
RED  = "#F28B82"   # alternative / shifted curves
GOLD = "#FDD663"   # special curves (e.g., Phillips LRAS)
GRAY = "#9AA0A6"   # dashed reference lines

def _dark_fig(w=6.5, h=4.8):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    for spine in ax.spines.values():
        spine.set_color(GRAY)
    ax.tick_params(colors=TEXT, labelsize=9)
    ax.grid(True, color=GRID, linewidth=0.6, linestyle="-", alpha=0.8)
    return fig, ax

def _style_ax(ax, xlabel, ylabel, title):
    ax.set_xlabel(xlabel, color=TEXT, fontsize=11, labelpad=6)
    ax.set_ylabel(ylabel, color=TEXT, fontsize=11, labelpad=6)
    ax.set_title(title, color=TEXT, fontsize=12, pad=10, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(TEXT)
    ax.spines["left"].set_color(TEXT)

def _dot(ax, x, y, label, label_offset=(6, 4)):
    ax.plot(x, y, "o", color="white", markersize=7, zorder=6)
    ax.annotate(label, (x, y), textcoords="offset points",
                xytext=label_offset, color=TEXT, fontsize=9, fontweight="bold")

def _vdot(ax, x, y_max, y_min=0):
    ax.plot([x, x], [y_min, y_max], ":", color=GRAY, linewidth=1, alpha=0.7)

def _hdot(ax, x_min, x_max, y):
    ax.plot([x_min, x_max], [y, y], ":", color=GRAY, linewidth=1, alpha=0.7)

def _legend(ax):
    leg = ax.legend(loc="upper right", facecolor="#2a2a2a",
                    labelcolor=TEXT, edgecolor=GRAY, fontsize=9)
    leg.get_frame().set_linewidth(0.8)

# ── 1. Demand-Supply Curve ─────────────────────────────────────────────────────

def draw_demand_supply(shifted=False, title="Demand and Supply Analysis"):
    """Standard demand-supply diagram. shifted=True adds a rightward D2 shift."""
    fig, ax = _dark_fig()
    q = np.linspace(1, 9, 200)
    D1 = 10 - q
    S  = 1  + q

    ax.plot(q, D1, color=BLUE,  linewidth=2.5, label="D₁ (Demand)")
    ax.plot(q, S,  color=GREEN, linewidth=2.5, label="S  (Supply)")

    # Equilibrium E1: D1=S → 10-Q=1+Q → Q=4.5, P=5.5
    q1, p1 = 4.5, 5.5
    _dot(ax, q1, p1, "E₁")
    _vdot(ax, q1, p1); _hdot(ax, 0, q1, p1)
    ax.text(q1, 0.3, "Q₁", color=GRAY, fontsize=9, ha="center")
    ax.text(0.3, p1, "P₁", color=GRAY, fontsize=9, va="center")

    if shifted:
        D2 = 12 - q  # +2 rightward shift
        ax.plot(q, D2, color=BLUE, linewidth=2.5, linestyle="--", label="D₂ (Shifted Demand)")
        # E2: 12-Q=1+Q → Q=5.5, P=6.5
        q2, p2 = 5.5, 6.5
        _dot(ax, q2, p2, "E₂", label_offset=(6, -14))
        _vdot(ax, q2, p2); _hdot(ax, 0, q2, p2)
        ax.text(q2, 0.3, "Q₂", color=GRAY, fontsize=9, ha="center")
        ax.text(0.3, p2, "P₂", color=GRAY, fontsize=9, va="center")
        ax.annotate("", xy=(q2, 3.5), xytext=(q1, 3.5),
                    arrowprops=dict(arrowstyle="->", color=GOLD, lw=1.5))

    ax.set_xlim(0, 10); ax.set_ylim(0, 11)
    ax.set_xticks([]); ax.set_yticks([])
    _style_ax(ax, "Quantity (Q)", "Price (P)", title)
    _legend(ax)
    plt.tight_layout()
    return fig


# ── 2. IS-LM Curve ─────────────────────────────────────────────────────────────

def draw_is_lm(fiscal_shift=False, monetary_shift=False,
               title="IS-LM Model (Goods & Money Market Equilibrium)"):
    """Standard IS-LM diagram. Optionally show fiscal or monetary policy shifts."""
    fig, ax = _dark_fig()
    Y = np.linspace(1, 9, 200)

    # IS: r = 10 - Y (downward sloping — higher income → lower interest rate needed)
    IS1 = 10 - Y
    # LM: r = Y - 2  (upward sloping — higher income → higher money demand → higher r)
    LM1 = Y - 2

    ax.plot(Y, IS1, color=BLUE,  linewidth=2.5, label="IS (Goods Market)")
    ax.plot(Y, LM1, color=GREEN, linewidth=2.5, label="LM (Money Market)")

    # Equilibrium: 10-Y = Y-2 → Y=6, r=4
    Y0, r0 = 6, 4
    _dot(ax, Y0, r0, "E")
    _vdot(ax, Y0, r0); _hdot(ax, 0, Y0, r0)
    ax.text(Y0, 0.2, "Y*", color=GRAY, fontsize=9, ha="center")
    ax.text(0.2, r0, "r*", color=GRAY, fontsize=9, va="center")

    if fiscal_shift:
        IS2 = 12 - Y  # rightward shift: govt spending ↑
        ax.plot(Y, IS2, color=BLUE, linewidth=2.5, linestyle="--", label="IS₂ (Fiscal Expansion)")
        Y2, r2 = 7, 5
        _dot(ax, Y2, r2, "E₂", label_offset=(6, -14))
        ax.annotate("Fiscal\nExpansion →", xy=(8, 3), color=GOLD, fontsize=8.5, ha="center")

    if monetary_shift:
        LM2 = Y - 4  # downward shift: money supply ↑
        ax.plot(Y, LM2, color=GREEN, linewidth=2.5, linestyle="--", label="LM₂ (Monetary Expansion)")
        Y3, r3 = 7, 3
        _dot(ax, Y3, r3, "E₃", label_offset=(6, 4))

    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.set_xticks([]); ax.set_yticks([])
    _style_ax(ax, "National Income (Y)", "Interest Rate (r)", title)
    _legend(ax)
    plt.tight_layout()
    return fig


# ── 3. Phillips Curve ──────────────────────────────────────────────────────────

def draw_phillips_curve(srpc=True, lrpc=True,
                        title="Phillips Curve (Inflation–Unemployment Trade-off)"):
    """Short-run and/or long-run Phillips Curve."""
    fig, ax = _dark_fig()
    u = np.linspace(2, 12, 200)

    if srpc:
        # SRPC: π = 6 - 0.5u (downward sloping)
        pi1 = 6 - 0.5 * u
        ax.plot(u, pi1, color=BLUE, linewidth=2.5, label="SRPC (Short-Run Phillips Curve)")

        # Shifted SRPC (expectations shift up)
        pi2 = 9 - 0.5 * u
        ax.plot(u, pi2, color=BLUE, linewidth=2.5, linestyle="--",
                label="SRPC₂ (Higher Inflation Expectations)")
        ax.annotate("", xy=(5, pi2[np.argmin(abs(u-5))]),
                    xytext=(5, pi1[np.argmin(abs(u-5))]),
                    arrowprops=dict(arrowstyle="->", color=GOLD, lw=1.5))

    if lrpc:
        # LRPC: vertical at natural rate of unemployment (u* = 6%)
        ax.axvline(x=6, color=RED, linewidth=2.5, linestyle="-", label="LRPC at u* = 6% (Natural Rate)")
        ax.text(6.2, 8.5, "LRPC", color=RED, fontsize=9, fontweight="bold")

    ax.axhline(y=0, color=GRAY, linewidth=0.8, linestyle="-", alpha=0.5)
    ax.set_xlim(1, 13); ax.set_ylim(-1, 10)
    ax.set_xticks([]); ax.set_yticks([])
    _style_ax(ax, "Unemployment Rate (u%)", "Inflation Rate (π%)", title)
    _legend(ax)
    plt.tight_layout()
    return fig


# ── 4. Indifference Curve ──────────────────────────────────────────────────────

def draw_indifference_curve(budget_shift=False,
                            title="Consumer Equilibrium (Indifference Curve Analysis)"):
    """IC analysis: 2 indifference curves + budget line + equilibrium."""
    fig, ax = _dark_fig()
    x = np.linspace(0.5, 9, 300)

    # IC: x * y = k → y = k/x
    for k, lbl in [(4, "IC₁"), (8, "IC₂")]:
        y = k / x
        mask = (y > 0.3) & (y < 9)
        color = GREEN if k == 8 else BLUE
        ax.plot(x[mask], y[mask], color=color, linewidth=2.5, label=lbl)

    # Budget line: 2x + 2y = 16 → y = 8 - x
    ax.plot(x, 8 - x, color=RED, linewidth=2.5, label="Budget Line (BL)")

    # Equilibrium on IC₂: tangency at (4, 4) where IC₂ slope = BL slope
    ax.plot(4, 4, "o", color="white", markersize=8, zorder=6)
    ax.annotate("E* (Optimum)", (4, 4), textcoords="offset points",
                xytext=(8, 6), color=TEXT, fontsize=9, fontweight="bold")
    _vdot(ax, 4, 4); _hdot(ax, 0, 4, 4)
    ax.text(4, 0.2, "X*", color=GRAY, fontsize=9, ha="center")
    ax.text(0.2, 4, "Y*", color=GRAY, fontsize=9, va="center")

    if budget_shift:
        ax.plot(x, 10 - x, color=RED, linewidth=2, linestyle="--",
                label="BL₂ (Income ↑)")

    ax.set_xlim(0, 9); ax.set_ylim(0, 9)
    ax.set_xticks([]); ax.set_yticks([])
    _style_ax(ax, "Good X", "Good Y", title)
    _legend(ax)
    plt.tight_layout()
    return fig


# ── 5. Production Function ─────────────────────────────────────────────────────

def draw_production_function(title="Total, Average & Marginal Product"):
    """TP, AP, and MP curves (Law of Variable Proportions)."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.5, 7), sharex=True)
    for ax in (ax1, ax2):
        ax.set_facecolor(BG)
        ax.grid(True, color=GRID, linewidth=0.6, alpha=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for s in ["bottom", "left"]:
            ax.spines[s].set_color(TEXT)
        ax.tick_params(colors=TEXT, labelsize=9)
    fig.patch.set_facecolor(BG)

    L = np.linspace(0.1, 8, 300)
    # TP: cubic — increases at increasing rate, then decreasing rate, then falls
    TP = 3*L**2 - 0.4*L**3
    AP = TP / L
    MP = 6*L - 1.2*L**2  # derivative of TP

    ax1.plot(L, TP, color=BLUE, linewidth=2.5, label="TP (Total Product)")
    # Stage markers
    for l_val, name in [(2.5, "Inflection"), (5, "TP max")]:
        ax1.axvline(x=l_val, color=GRAY, linewidth=0.8, linestyle="--", alpha=0.7)
    ax1.set_ylabel("Output (Q)", color=TEXT, fontsize=10)
    ax1.set_title(title, color=TEXT, fontsize=12, pad=8, fontweight="bold")
    ax1.legend(facecolor="#2a2a2a", labelcolor=TEXT, edgecolor=GRAY, fontsize=9)

    ax2.plot(L, AP, color=GREEN, linewidth=2.5, label="AP (Avg Product)")
    ax2.plot(L, MP, color=RED,   linewidth=2.5, label="MP (Marginal Product)")
    ax2.axhline(y=0, color=GRAY, linewidth=0.8, linestyle="-", alpha=0.5)
    ax2.axvline(x=2.5, color=GRAY, linewidth=0.8, linestyle="--", alpha=0.7)
    ax2.axvline(x=5,   color=GRAY, linewidth=0.8, linestyle="--", alpha=0.7)
    # Stage labels
    for x_pos, stage in [(1.25, "Stage I"), (3.75, "Stage II"), (6.5, "Stage III")]:
        ax2.text(x_pos, -0.8, stage, color=GOLD, fontsize=8.5, ha="center")
    ax2.set_xlabel("Labour (L)", color=TEXT, fontsize=10)
    ax2.set_ylabel("AP / MP", color=TEXT, fontsize=10)
    ax2.legend(facecolor="#2a2a2a", labelcolor=TEXT, edgecolor=GRAY, fontsize=9)

    plt.tight_layout()
    return fig


# ── 6. Solow Growth Model ──────────────────────────────────────────────────────

def draw_solow_model(title="Solow Growth Model — Steady State"):
    fig, ax = _dark_fig()
    k = np.linspace(0.1, 10, 300)

    # Production per worker: y = k^0.5
    y   = k ** 0.5
    # Investment/savings: s*y, s=0.3
    sy  = 0.3 * y
    # Depreciation + population growth: (δ+n)*k, use 0.1
    dep = 0.1 * k

    ax.plot(k, y,   color=BLUE,  linewidth=2.5, label="y = f(k)  [Output per worker]")
    ax.plot(k, sy,  color=GREEN, linewidth=2.5, label="s·f(k)  [Investment per worker]")
    ax.plot(k, dep, color=RED,   linewidth=2.5, label="(δ+n)·k  [Depreciation + Pop. growth]")

    # Steady state: sy = dep → 0.3√k = 0.1k → k* = 9, y* = 3
    k_star, y_star = 9, 3
    s_star = 0.3 * y_star
    _dot(ax, k_star, s_star, "k*")
    _vdot(ax, k_star, s_star)
    ax.text(k_star, 0.1, "k*", color=GOLD, fontsize=10, ha="center", fontweight="bold")

    ax.annotate("Capital\nAccumulation →", xy=(3.5, 0.5), color=GREEN, fontsize=8.5, ha="center")
    ax.annotate("← Capital\nDecumulation", xy=(9.5, 0.5), color=RED, fontsize=8.5, ha="center")

    ax.set_xlim(0, 10.5); ax.set_ylim(0, 4)
    ax.set_xticks([]); ax.set_yticks([])
    _style_ax(ax, "Capital per Worker (k)", "Output / Investment per Worker", title)
    _legend(ax)
    plt.tight_layout()
    return fig


# ── 7. Lorenz Curve ────────────────────────────────────────────────────────────

def draw_lorenz_curve(gini_level="high", title="Lorenz Curve — Income Inequality"):
    """gini_level: 'low', 'medium', 'high'."""
    fig, ax = _dark_fig()
    x = np.linspace(0, 1, 300)

    # Line of perfect equality
    ax.plot(x, x, color=GRAY, linewidth=1.5, linestyle="--", label="Line of Perfect Equality")

    params = {"low": 2.5, "medium": 4.0, "high": 7.0}
    p = params.get(gini_level, 4.0)
    lc = x ** p
    ax.plot(x, lc, color=BLUE, linewidth=2.5, label=f"Lorenz Curve ({gini_level.title()} Inequality)")

    # Shade the Gini area
    ax.fill_between(x, x, lc, alpha=0.15, color=RED, label="Gini Area (A)")
    ax.fill_between(x, lc, 0,  alpha=0.10, color=GREEN, label="Area B")

    gini = 1 - 2 * np.trapz(lc, x)
    ax.text(0.3, 0.7, f"Gini ≈ {gini:.2f}", color=GOLD, fontsize=11, fontweight="bold")

    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], color=TEXT, fontsize=8)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"], color=TEXT, fontsize=8)
    _style_ax(ax, "Cumulative % of Population", "Cumulative % of Income", title)
    _legend(ax)
    plt.tight_layout()
    return fig


# ── 8. Isoquant / Isocost ──────────────────────────────────────────────────────

def draw_isoquant(title="Isoquant-Isocost Analysis (Producer Equilibrium)"):
    fig, ax = _dark_fig()
    L = np.linspace(0.5, 9, 300)

    for q_val, color, lbl in [(4, GRAY, "IQ₁ (Q=100)"), (8, BLUE, "IQ₂ (Q=200)")]:
        K = q_val / L
        mask = (K > 0.3) & (K < 9)
        ax.plot(L[mask], K[mask], color=color, linewidth=2.5, label=lbl)

    # Isocost: wL + rK = C → K = C/r - (w/r)L, use slope=-1
    ax.plot(L, 9 - L, color=RED, linewidth=2.5, label="Isocost Line (IC)")
    ax.plot(L, 11 - L, color=RED, linewidth=2, linestyle="--", label="Isocost₂ (Cost ↑)")

    # Tangency with IQ₂: IQ₂ at L=2√2, K=2√2
    L_eq, K_eq = 2*np.sqrt(2), 2*np.sqrt(2)
    _dot(ax, L_eq, K_eq, "E* (MRTS = w/r)")
    _vdot(ax, L_eq, K_eq); _hdot(ax, 0, L_eq, K_eq)

    ax.set_xlim(0, 9); ax.set_ylim(0, 9)
    ax.set_xticks([]); ax.set_yticks([])
    _style_ax(ax, "Labour (L)", "Capital (K)", title)
    _legend(ax)
    plt.tight_layout()
    return fig


# ── Dispatcher: diagram_type → draw function ───────────────────────────────────

DIAGRAM_DISPATCH = {
    "demand_supply_curve":  lambda: draw_demand_supply(),
    "is_lm_curve":          lambda: draw_is_lm(),
    "phillips_curve":       lambda: draw_phillips_curve(),
    "indifference_curve":   lambda: draw_indifference_curve(),
    "production_function":  lambda: draw_production_function(),
    "growth_model":         lambda: draw_solow_model(),
    "lorenz_curve":         lambda: draw_lorenz_curve(),
    "isoquant":             lambda: draw_isoquant(),
}

def get_standard_diagram(diagram_type: str):
    """Returns a matplotlib Figure for the given diagram type, or None if not covered."""
    fn = DIAGRAM_DISPATCH.get(diagram_type)
    return fn() if fn else None


COVERED_TYPES = set(DIAGRAM_DISPATCH.keys())
