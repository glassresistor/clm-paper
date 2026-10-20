"""Synthetic evaluation of the clm-mem MemoryHarness (for the arXiv paper).

Two synthetic regimes, each with three shortterm_keep_pct settings:
  heavy     -- durable fact every 2 turns + long filler  -> long-term alone
               eventually overflows the budget, exercising phase-3 offload.
  balanced  -- durable fact every 4 turns + moderate filler -> long-term fits;
               phases 1-2 evict filler while facts stay live.
"""
import json, os, re, sys, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "clm-mem"))
from clm_mem import MemoryHarness, HarnessConfig
from clm_mem.llm import StubChat
from clm_mem.blocks import LONG, SHORT, TRANSIENT

BUDGET = 900
TURNS = 60
PAD3 = ("Here is a longish status update with plenty of incidental detail "
        "that eats tokens while we work. ") * 3
PAD1 = "Here is a longish status update with plenty of incidental detail that eats tokens. "

def make_msg(i, period, pad):
    if i % period == 1:
        return f"Remember: project codename Nova-{i}, port {80+i}. {pad}"
    return f"Quick temp note {i}: {pad}"

def fact_id(content):
    m = re.search(r"codename Nova-(\d+)", content)
    return int(m.group(1)) if m else -1

def run(scen, period, pad, keep_pct, workdir):
    shutil.rmtree(workdir, ignore_errors=True)
    os.makedirs(workdir, exist_ok=True)
    h = MemoryHarness(StubChat(), HarnessConfig(
        max_context_tokens=BUDGET, shortterm_keep_pct=keep_pct,
        keep_recent_turns=2, classify_mode="both", workdir=workdir))
    traj = []
    prev = 0
    for i in range(1, TURNS + 1):
        h.step(make_msg(i, period, pad))
        ev = h.events[prev:]; prev = len(h.events)
        emitted = set(range(1, i + 1, period))
        live_ids = {f for f in (fact_id(b.content) for b in h.blocks) if f >= 0}
        traj.append({
            "turn": i, "tokens": h.tokens(), "budget": BUDGET,
            "long": h.counts()[LONG], "short": h.counts()[SHORT],
            "transient": h.counts()[TRANSIENT],
            "archive": h.archive_size(),
            "p1": sum(e["kind"] == "evict-phase1" for e in ev),
            "p2": sum(e["kind"] == "evict-phase2" for e in ev),
            "p3": sum(e["kind"] == "evict-phase3" for e in ev),
            "facts_live": len(live_ids & emitted),
            "facts_emitted": len(emitted),
        })
    arch = os.path.join(h.cfg.workdir, "archive.jsonl")
    arch_ids = set()
    if os.path.exists(arch):
        with open(arch) as f:
            for line in f:
                fid = fact_id(json.loads(line)["content"])
                if fid >= 0:
                    arch_ids.add(fid)
    emitted_all = set(range(1, TURNS + 1, period))
    live_ids = {f for f in (fact_id(b.content) for b in h.blocks) if f >= 0}
    return {
        "scenario": scen, "keep_pct": keep_pct, "trajectory": traj,
        "facts_emitted": len(emitted_all),
        "facts_live_at_end": len(live_ids & emitted_all),
        "facts_archived_recoverable": len(arch_ids & emitted_all),
        "final_tokens": h.tokens(),
    }

out = {}
for scen, period, pad in (("heavy", 2, PAD3), ("balanced", 4, PAD1)):
    for kp in (0.25, 0.5, 0.75):
        r = run(scen, period, pad, kp, f"exp-data/{scen}-{kp}")
        out[f"{scen}-{kp}"] = r
        print(f"{scen} keep={kp}: live@end={r['facts_live_at_end']}/"
              f"{r['facts_emitted']} archived={r['facts_archived_recoverable']} "
              f"final_tokens={r['final_tokens']}")

with open("exp-data/results.json", "w") as f:
    json.dump(out, f, indent=1)
print("saved exp-data/results.json")
