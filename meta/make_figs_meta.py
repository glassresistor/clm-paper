"""Generate the data figures of the arXiv paper from exp-data/results.json.

Writes fig_tokens, fig_tiers, fig_phases and fig_retention as PDFs into
meta/figures/. The architecture schematic (fig_arch.pdf) is produced by
make_arch.py; do not generate it here or it will be overwritten.
Runs after clm_exp.py:
    python3 clm_exp.py && python3 make_figs.py
"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

os.makedirs("meta/figures", exist_ok=True)
R = json.load(open("exp-data/results.json"))

C = {0.25: "#1f77b4", 0.5: "#ff7f0e", 0.75: "#2ca02c"}
LBL = {0.25: r"$\kappa=0.25$", 0.5: r"$\kappa=0.5$", 0.75: r"$\kappa=0.75$"}

def traj(key): return R[key]["trajectory"]

# ---------- Figure 1: token budget enforcement (two panels) ----------
fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.9))
for ax, scen in zip(axes, ("heavy", "balanced")):
    for kp in (0.25, 0.5, 0.75):
        t = traj(f"{scen}-{kp}")
        ax.plot([r["turn"] for r in t], [r["tokens"] for r in t],
                color=C[kp], lw=1.3, label=LBL[kp])
    ax.axhline(900, ls="--", c="k", lw=1.0)
    ax.set_xlabel("turn"); ax.set_ylabel("live-window tokens")
    ax.set_title(f"{scen} regime" + ("  (budget $B=900$)" if scen=="heavy" else ""))
    ax.set_ylim(0, 1050)
axes[0].legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig("meta/figures/fig_tokens.pdf"); plt.close(fig)

# ---------- Figure 2: tier composition stacked areas ----------
fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.9))
for ax, scen in zip(axes, ("heavy", "balanced")):
    t = traj(f"{scen}-0.5")
    xs = [r["turn"] for r in t]
    L = [r["long"] for r in t]; S = [r["short"] for r in t]; X = [r["transient"] for r in t]
    ax.stackplot(xs, X, S, L, labels=("transient", "short-term", "long-term"),
                 colors=["#9e9e9e", "#ffb74d", "#4db6ac"])
    ax.set_xlim(1, 60); ax.set_ylim(0, max(L)+8)
    ax.set_xlabel("turn"); ax.set_ylabel("live blocks")
    ax.set_title(f"{scen} regime, $\\kappa=0.5$")
axes[0].legend(loc="upper left", frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig("meta/figures/fig_tiers.pdf"); plt.close(fig)

# ---------- Figure 3: cumulative phase firings + archive growth ----------
fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.1))
mk = {"P1": "v", "P2": "s", "P3": "*"}
for kp in (0.25, 0.5, 0.75):
    t = traj(f"heavy-{kp}")
    c1 = c2 = c3 = 0
    xs, y1, y2, y3, ya = [], [], [], [], []
    for r in t:
        c1 += r["p1"]; c2 += r["p2"]; c3 += r["p3"]
        xs.append(r["turn"]); y1.append(c1); y2.append(c2); y3.append(c3)
        ya.append(r["archive"])
    for lbl, yy in (("P1", y1), ("P2", y2), ("P3", y3)):
        axes[0].plot(xs, yy, color=C[kp], marker=mk[lbl], markevery=(6, 8),
                    ms=4 if lbl != "P3" else 7, lw=1.0, label=f"$\\kappa$={kp} {lbl}")
    axes[1].plot(xs, ya, color=C[kp], lw=1.4, marker="o", ms=2.5,
                 markevery=(6, 8), label=LBL[kp])
axes[0].set_title("heavy regime: cumulative phase firings", fontsize=9)
axes[0].set_xlabel("turn"); axes[0].set_ylabel("evictions")
axes[0].legend(frameon=False, fontsize=7.5, loc="upper left", ncol=1)
axes[1].set_title("archive growth (offloaded + evicted)", fontsize=9)
axes[1].set_xlabel("turn"); axes[1].set_ylabel("archived records")
axes[1].legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout(); fig.savefig("meta/figures/fig_phases.pdf"); plt.close(fig)

# ---------- Figure 4: fact retention over time ----------
fig, ax = plt.subplots(figsize=(3.4, 2.6))
for scen in ("heavy", "balanced"):
    t = traj(f"{scen}-0.5")
    ys = [r["facts_live"] / max(1, r["facts_emitted"]) for r in t]
    ax.plot([r["turn"] for r in t], ys, lw=1.4, label=scen)
ax.set_xlabel("turn"); ax.set_ylabel(r"live facts / emitted")
ax.set_ylim(-0.05, 1.05); ax.legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig("meta/figures/fig_retention.pdf"); plt.close(fig)

# ---------- summary numbers for paper tables ----------
print("|scenario|kp|P1|P2|P3|archive@end|facts live@end|archived facts|")
for k, r in R.items():
    c1 = sum(t["p1"] for t in r["trajectory"])
    c2 = sum(t["p2"] for t in r["trajectory"])
    c3 = sum(t["p3"] for t in r["trajectory"])
    print(f"|{r['scenario']}|{r['keep_pct']}|{c1}|{c2}|{c3}|"
          f"{r['trajectory'][-1]['archive']}|{r['facts_live_at_end']}|"
          f"{r['facts_archived_recoverable']}|")
print("figures written to meta/figures/")
