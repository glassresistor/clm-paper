"""Benchmarks for the two forgetting strategies (stub backends, no GPU).

Regimes:
  heavy      -- durable fact every 2 turns + long filler; long tier alone
                overflows the budget (the paper's saturation regime).
  balanced   -- fact every 4 turns + moderate filler.
  churn      -- every durable fact UPDATES a slot ("codename Nova-k");
                tests supersession correctness under adversarial updates.
  dupheavy   -- each durable fact restated three times; tests write-time
                dedup savings (admitted blocks per emitted fact).

Strategies: off | decay | supersede | both. Sweep kappa on heavy/balanced;
churn/dupheavy at kappa=0.5. Metrics:
  budget_ok     -- peak live tokens never exceeded B (invariant).
  sat_turn      -- first turn the long tier occupied >60% of budget (None=never).
  live_core     -- distinct facts still in the LIVE window at the end.
  recovered     -- distinct facts findable via recall()/live scan at the end
                  (offload-don't-destroy: must equal emitted, always).
  admitted      -- long-tier blocks admitted per emitted fact (write-time
                   dedup savings; baseline ~3.0 for dupheavy, both <1).
"""
import json, os, re, shutil, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "clm-mem"))
from clm_mem import MemoryHarness, HarnessConfig
from clm_mem.llm import StubChat
from clm_mem.blocks import LONG

BUDGET = 900
TURNS = 60
PAD3 = ("Here is a longish status update with plenty of incidental detail "
        "that eats tokens while we work. ") * 3
PAD1 = PAD3[:120]

CODENAME = re.compile(r"codename Nova-(\d+)", re.I)

def nums(text: str) -> set:
    return {int(m) for m in CODENAME.findall(text)}

def msg_for(regime, i):
    fact = "Remember: project codename Nova-%d, port %d." % (i, 80 + i % 19)
    if regime == "heavy":
        return f"{fact} {PAD3}" if i % 2 == 1 else f"Quick temp note {i}: {PAD3}"
    if regime == "balanced":
        return f"{fact} {PAD1}" if i % 4 == 1 else f"Quick temp note {i}: {PAD1}"
    if regime == "churn":   # updates: every fact turn restates the slot with
        # a new value; the filler between references the CURRENT codename,
        # so reheating has something real to warm (nova-k = last emitted)
        if i % 2 == 1:
            return f"{fact} {PAD3}"
        k = i - 1
        return f"Still working on nova-{k}, note {i}: {PAD1}"
    if regime == "dupheavy":  # same fact restated three times in a row
        j = ((i - 1) // 3) * 3 + 1   # first turn of the triple
        if (i - 1) % 3 == 0:
            return f"{fact} {PAD1}"
        if (i - 1) % 3 == 1:
            return f"as discussed, project codename Nova-{j}, port {80 + j % 19}. {PAD1}"
        return f"confirmed again: project codename Nova-{j}, port {80 + j % 19}. {PAD1}"
    raise ValueError(regime)

def run(regime, strat, kappa):
    flags = {"both": dict(decay_enabled=True, supersede_enabled=True),
             "decay": dict(decay_enabled=True),
             "supersede": dict(supersede_enabled=True),
             "off": {},
             # both strategies on a gentler curve: longer half-life / lower
             # floor keeps facts live as long entries for ~2 half-lives before
             # demoting -- a curated core rather than churn
             "tuned": dict(decay_enabled=True, supersede_enabled=True,
                           decay_half_life=40, demote_threshold=0.35),
             "sup-fast": dict(supersede_enabled=True, supersede_fast=True),
             }[strat]   # exact mapping: substring tests here would
                        # silently make 'both' mean 'off'
    wd = f"exp-data/bench/{regime}_{strat.replace('+','_')}_{kappa}"
    shutil.rmtree(wd, ignore_errors=True)
    os.makedirs(wd, exist_ok=True)
    h = MemoryHarness(StubChat(), HarnessConfig(
        max_context_tokens=BUDGET, shortterm_keep_pct=kappa,
        keep_recent_turns=2, classify_mode="both", workdir=wd, **flags))
    # ground truth: every fact number the generator ever emits for this regime
    emitted = set()
    for i in range(1, TURNS + 1):
        emitted |= nums(msg_for(regime, i))

    peak = 0; sat = None; occ_curve = []
    for i in range(1, TURNS + 1):
        h.step(msg_for(regime, i))
        t = h.tokens(); peak = max(peak, t)
        long_tok = sum(h.counter.count_block(b) for b in h.blocks if b.tag == LONG)
        occ_curve.append(long_tok)
        if sat is None and long_tok > 0.6 * BUDGET:
            sat = i
    # final recovery test: live scan + actual recall calls (offload-don't-destroy)
    live_facts = set()
    for b in h.blocks: live_facts |= nums(b.content)
    recov = set(live_facts & emitted)
    for qnum in sorted(emitted - recov):
        if h.recall(f"Nova-{qnum}"): recov.add(qnum)
    kinds = {}
    for e in h.events: kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    admitted_live_arch = sum(
        1 for r in [json.loads(l) for l in open(os.path.join(wd, "archive.jsonl"))]
        if nums(r["content"]) & emitted)
    return {
        "regime": regime, "strategy": strat, "kappa": kappa,
        "peak_tokens": peak, "budget_ok": peak <= BUDGET,
        "sat_turn": sat,
        "final_long_blocks": len([b for b in h.blocks if b.tag == LONG]),
        "live_core": len(live_facts & emitted),
        "emitted": len(emitted),
        "recovered": len(recov),
        "invariant_ok": len(recov) >= len(emitted),
        "archive_records": h.archive_size(),
        "archived_fact_copies": admitted_live_arch,
        "p1": kinds.get("evict-phase1", 0), "p2": kinds.get("evict-phase2", 0),
        "p3": kinds.get("evict-phase3", 0),
        "maint_supersede": kinds.get("maintain-supersede", 0),
        "maint_dedup": kinds.get("maintain-dedup", 0),
        "maint_decay": kinds.get("maintain-decay", 0),
        "maint_reheat": kinds.get("maintain-reheat", 0),
    }

def main():
    results = []
    for regime in ("heavy", "balanced"):
        for kappa in (0.25, 0.5, 0.75):
            for strat in ("off", "decay", "supersede", "both"):
                results.append(run(regime, strat, kappa))
    for regime in ("heavy", "balanced"):
        results.append(run(regime, "tuned", 0.5))
    for regime in ("balanced", "churn", "dupheavy"):
        for strat in ("off", "supersede", "sup-fast", "both"):
            results.append(run(regime, strat, 0.5))
    os.makedirs("exp-data", exist_ok=True)
    out = "exp-data/forget_bench.json"
    with open(out, "w") as f: json.dump(results, f, indent=1)
    print(f"wrote {out} ({len(results)} runs)")

    # --- report -------------------------------------------------------------
    def fmt(r):
        return (f"{r['regime']:<9}{r['strategy']:<10}{r['kappa']:>5}"
                f"{'OK' if r['budget_ok'] else 'FAIL':>6}"
                f"{str(r['sat_turn']):>6}{r['final_long_blocks']:>7}"
                f"{r['live_core']:>4}/{r['emitted']:<3}"
                f"{('OK' if r['invariant_ok'] else 'FAIL'):>5}"
                f"{r['p3']:>4}{r['archive_records']:>6}")
    print(f"{'regime':<9}{'strategy':<10}{'k':>5}{'budget':>8}{'sat@':>6}"
          f"{'longLN':>7}{'core':>7}{'recov':>6}{'P3':>4}{'arch':>6}")
    for r in results: print(fmt(r))

    bad_budget = [r for r in results if not r["budget_ok"]]
    bad_inv = [r for r in results if not r["invariant_ok"]]
    assert not bad_budget, f"budget invariant violated: {bad_budget}"
    assert not bad_inv, f"recovery invariant violated: {bad_inv}"
    print("invariants hold across all runs: budget <= B, full archive recovery")

if __name__ == "__main__":
    main()
