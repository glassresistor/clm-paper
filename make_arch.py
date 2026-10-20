"""Clean architecture schematic for the clm-mem paper (fig_arch)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(6.9, 3.9))
ax.axis("off")
ax.set_xlim(0, 1); ax.set_ylim(0, 1)

def box(x, y, w, h, text, fc="#f4f4f8", fs=8, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.013",
                                fc=fc, ec="#555", lw=1.0))
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", linespacing=1.35)

def arw(x1, y1, x2, y2, style="-|>", dashed=False, rad=None, color="#333"):
    kw = dict(arrowstyle=style, lw=1.0, color=color, mutation_scale=14)
    if dashed:
        kw["linestyle"] = (0, (4, 3))
    cs = f"arc3,rad={rad}" if rad else "arc3,rad=0"
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(**kw, connectionstyle=cs))

# --- intake row ---------------------------------------------------------
box(0.02, 0.86, 0.15, 0.09, "user turn", bold=True)
box(0.27, 0.86, 0.24, 0.09, "pre-classify\n(SystemOne)", fc="#e8f4e8")
box(0.61, 0.86, 0.35, 0.09, "evict BEFORE generate", fc="#fdeee2")
arw(0.17, 0.905, 0.27, 0.905)
arw(0.51, 0.905, 0.61, 0.905)

# --- core loop row ------------------------------------------------------
box(0.02, 0.54, 0.33, 0.19,
    "live window (Blocks)\nlong / short / transient\nmirrored to context.md\n+ context.jsonl",
    fc="#e7f0fa", bold=True)
box(0.45, 0.54, 0.26, 0.19, "LLM decode\n(any OpenAI-compatible\nbackend)", fc="#fff4d6")
box(0.79, 0.54, 0.19, 0.19, "inline tag\nsplit\n<longterm>/..", fc="#efe3fa", fs=7.5)

arw(0.82, 0.86, 0.58, 0.73)          # evict-before -> decode
arw(0.35, 0.635, 0.45, 0.635)        # live window -> decode (context sent)
arw(0.71, 0.68, 0.79, 0.68)          # decode -> inline split
arw(0.88, 0.73, 0.19, 0.73, rad=-0.28)   # tagged chunks return to live window

# --- relabel + eviction row ---------------------------------------------
box(0.45, 0.26, 0.26, 0.17, "post-turn router\nor SystemOne re-label", fc="#efe3fa")
box(0.75, 0.26, 0.23, 0.17, "evict AFTER growth\nP1 transient drop\nP2 shortterm FIFO\nP3 longterm offload", fc="#fdeee2", fs=7.5)
arw(0.28, 0.54, 0.58, 0.43)          # live window -> router
arw(0.71, 0.345, 0.75, 0.345)        # router -> evict engine

# --- archive row ---------------------------------------------------------
box(0.45, 0.04, 0.53, 0.12, "archive.jsonl\n(recoverable via recall / reinject)", fc="#f8e0e6", bold=True)
arw(0.865, 0.26, 0.74, 0.16)          # evict engine -> archive
arw(0.45, 0.10, 0.19, 0.54, style="-", dashed=True, rad=0.35)   # reinject path back

ax.text(0.70, 0.215, "offload", fontsize=7, ha="center")
ax.text(0.24, 0.32, "reinject (dashed)", fontsize=7, ha="center", rotation=48)

fig.tight_layout()
fig.savefig("paper/figures/fig_arch.pdf")
plt.close(fig)
print("arch figure rebuilt")
