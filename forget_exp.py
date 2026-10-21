"""Saturation experiment for the forgetting strategies (paper evidence).

Re-runs the *heavy* regime from clm_exp.py (durable fact every 2 turns + long
filler, B=900, 60 turns) with the two opt-in strategies toggled independently:
baseline (both off), decay only, supersede only, both. The baseline saturates:
the long tier fills the window and live retention drops to zero while phase 3
offloads everything. We record final live-tier occupancy, live fact retention,
archive size and peak tokens. Deterministic stub backend.
"""
import json, os, re, sys, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "clm-mem"))
from clm_mem import MemoryHarness, HarnessConfig
from clm_mem.llm import StubChat
from clm_mem.blocks import LONG

BUDGET = 900
TURNS = 60
PAD3 = ("Here is a longish status update with plenty of incidental detail "
        "that eats tokens while we work. ") * 3

def make_msg(i):
    if i % 2 == 1:
        return f"Remember: project codename Nova-{i}, port {80+i}. {PAD3}"
    return f"Quick temp note {i}: {PAD3}"

CODENAME = re.compile(r"codename Nova-(\d+)", re.I)

def fact_nums(text):
    return {int(m) for m in CODENAME.findall(text)}

def run(name, **flags):
    wd = f"exp-data/forget/{name}"
    shutil.rmtree(wd, ignore_errors=True)
    os.makedirs(wd, exist_ok=True)
    h = MemoryHarness(StubChat(), HarnessConfig(
        max_context_tokens=BUDGET, shortterm_keep_pct=0.5,
        keep_recent_turns=2, classify_mode="both", workdir=wd, **flags))
    peak = 0
    sat_turn = None            # first turn where long tier > 60% of budget
    occ = []
    for i in range(1, TURNS + 1):
        h.step(make_msg(i))
        t = h.tokens()
        peak = max(peak, t)
        long_tok = sum(h.counter.count_block(b) for b in h.blocks if b.tag == LONG)
        occ.append(long_tok)
        if sat_turn is None and long_tok > 0.6 * BUDGET:
            sat_turn = i
    live_long = [b for b in h.blocks if b.tag == LONG]
    # 'live facts' counts every tag tier -- a demoted-but-still-live fact is
    # still recoverable from the window, which is what saturation measures.
    live_facts = set()
    for b in h.blocks:
        live_facts |= fact_nums(b.content)
    emitted = set(range(1, TURNS + 1, 2))   # odd turns <= 60 carry the facts
    arch = []
    ap = os.path.join(wd, "archive.jsonl")
    if os.path.exists(ap):
        with open(ap) as f:
            arch = [json.loads(l) for l in f]
    arch_facts = set()
    for r in arch:
        arch_facts |= fact_nums(r["content"])
    kinds = {}
    for e in h.events:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    return {
        "run": name,
        "decay_enabled": flags.get("decay_enabled", False),
        "supersede_enabled": flags.get("supersede_enabled", False),
        "peak_tokens": peak, "budget": BUDGET,
        "saturation_turn": sat_turn,          # None = never saturated
        "final_long_blocks": len(live_long),
        "live_codenames": len(live_facts & emitted),
        "emitted_codenames": len(emitted),
        "recovered_from_archive": len((live_facts | arch_facts) & emitted),
        "archive_records": len(arch),
        "maintain_events": {k: v for k, v in kinds.items()
                            if k.startswith("maintain")},
        "p3_offloads": sum(v for k, v in kinds.items()
                           if k == "evict-phase3"),
    }

def main():
    os.makedirs("exp-data/forget", exist_ok=True)
    results = [
        run("baseline"),
        run("decay", decay_enabled=True),
        run("supersede", supersede_enabled=True),
        run("both", decay_enabled=True, supersede_enabled=True),
    ]
    os.makedirs("exp-data", exist_ok=True)
    out = "exp-data/forget_results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=1)
    hdr = (f"{'run':<10}{'decay':>6}{'sup':>6}{'sat@':>6}{'liveLN':>8}"
           f"{'recov':>7}{'arch':>6}{'P3':>5}")
    print(hdr)
    for r in results:
        rec = f"{r['recovered_from_archive']}/{r['emitted_codenames']}"
        print(f"{r['run']:<10}{str(r['decay_enabled']):>6}"
              f"{str(r['supersede_enabled']):>6}"
              f"{str(r['saturation_turn']):>6}"
              f"{r['final_long_blocks']:>8}{rec:>7}"
              f"{r['archive_records']:>6}{r['p3_offloads']:>5}")
    print("wrote", out)

if __name__ == "__main__":
    main()
