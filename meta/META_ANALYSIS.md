# Meta-analysis: clm-paper rerun with the new clm-mem submodule (83bbc86)

**Date:** 2026-10-21 · **Author:** automated artifact review

## 1. What was done

- Built a dedicated virtual environment inside `clm-paper` (`clm-paper/.venv`, Python 3.13.14) from the version pinned *inside* the paper repo: `clm-mem/requirements.lock.txt` (the frozen snapshot shipped by the submodule), an editable install of `./clm-mem` at the submodule pin, plus matplotlib for figures.
- Re-ran all three experiment drivers committed in the paper (`clm_exp.py`, `forget_exp.py`, `forget_bench.py`) with that environment and the new harness code.
- Compared the new outputs against the committed (old) results byte-for-byte, and audited every quantitative claim in `paper/main.tex` against the measured data.
- Rendered figures from the rerun into `meta/figures/` (never overwriting `paper/figures/`) to check figure reproducibility without touching the artifact.

## 2. Environment

| item | committed artifact | this rerun |
|---|---|---|
| Python | 3.13 | 3.13.14 |
| matplotlib | 3.10.9 | 3.11.2 |
| numpy | 2.5.2 | 2.5.4 |
| openai (pinned) | 3.28.0 | 3.28.0 |
| pytest | 9.1.1 | 9.1.1 |
| clm-mem | d8d8c47 (pin in ca209ba, **missing from history**) | 83bbc86 (submodule HEAD) |
| test suite | 44 passing (clm-mem 9569701) | 62 passed |

## 3. Reproduction verdict

| dataset | committed md5 | rerun md5 | identical |
|---|---|---|---|
| results.json | `7a1ac005c5…` | `7a1ac005c5…` | **yes** |
| forget_results.json | `b368806679…` | `b368806679…` | **yes** |
| forget_bench.json | `f15c8e1ca8…` | `f15c8e1ca8…` | **yes** |

All three aggregate datasets reproduce **byte-for-byte** under the new code — including `forget_results.json` / `forget_bench.json`, whose committed versions were produced by a commit (d8d8c47) that no longer exists in the submodule history. This is strong evidence that 83bbc86 is behaviourally equivalent to d8d8c47 on every driver in this repo.

The only observable difference from the new code is a **schema change** in the per-run mirrors: the `Block` dataclass gained `importance` and `last_access` fields (added by the forgetting-strategy commit), which now appear in every `context.jsonl`. Six files changed on disk (`exp-data/{heavy,balanced}-{0.25,0.5,0.75}/context.jsonl`); all `context.md` and `archive.jsonl` mirrors are unchanged, and the bench/forget mirrors already carried the new fields (proving they were generated post-strategy). **No behavioural metric changed.**

Figures: PDFs differ in bytes only because matplotlib was bumped (3.10.9 → 3.11.2): metadata + rasterisation/antialiasing. The plotted arrays are identical (`results.json` md5 match). Pixel-level check (150 dpi, fraction of pixels differing >30 levels): tokens 8.6%, tiers 6.0%, phases 6.9%, retention 3.7% — text-edge differences only.

One build gap: `paper/build.sh` does **not** compile in this environment (MetaFont `mf.base` / a usable `pdftex.map` are not part of the artifact; only `tcrm1000.pk` is cached). The committed `main.pdf` cannot be rebuilt from the repo alone. See §6.

## 4. What changed in clm-mem between the runs

`bede625 → 83bbc86` (the substantive jump; d8d8c47 sits inside this lineage):

- **Phase-0 forgetting strategies** (`harness.py` +173 lines, `config.py` +22): decay & reheating (importance seeded by tag long=1.0/short=0.6/transient=0.3, half-life `decay_half_life`, demotion floor, reheat on identifier match; phase-3 ranks offloads by effective importance instead of strict age) and supersession (lexical subject-slot extraction: duplicate dropped at write time, partial match labelled `[superseded by…]` and demoted). Both opt-in; defaults off.
- **Block schema**: `importance`, `last_access` fields (`blocks.py`).
- **Design language / studio UI** (`static/dyson.js`, svgs, style.css), CLI flags `--decay/--supersede`, MCP tool `clm_set_forget`.
- **Tests**: +165 lines `tests/test_forgetting.py`; suite grew 44 → 62 passing.

## 5. Old vs new results (all three datasets)

### 5.1 Synthetic stress (`clm_exp.py`, B=900, 60 turns)

| run | P1 | P2 | P3 | arch@60 | live facts | archived | final tok | old==new |
|---|---|---|---|---|---|---|---|---|
| heavy-0.25 | 52 | 55 | 31 | 174 | 0/30 | 30 | 898 | ✓ |
| heavy-0.5 | 54 | 68 | 31 | 174 | 0/30 | 30 | 898 | ✓ |
| heavy-0.75 | 55 | 77 | 31 | 174 | 0/30 | 30 | 898 | ✓ |
| balanced-0.25 | 31 | 41 | 37 | 182 | 5/15 | 10 | 877 | ✓ |
| balanced-0.5 | 34 | 56 | 37 | 182 | 5/15 | 10 | 877 | ✓ |
| balanced-0.75 | 37 | 78 | 37 | 182 | 5/15 | 10 | 877 | ✓ |

Budget invariant holds (peak ≤ B in all six); offload-don't-destroy holds (live+archived = emitted). The paper's `tab:syn` matches these numbers exactly.

### 5.2 Forgetting strategies (`forget_bench.py`, 38 runs)

All invariants hold in every run (`budget_ok` and `invariant_ok` all True). Key patterns:
- **heavy/κ=0.5/off**: sat@5, long blocks 28, core 0/30, P3 29, archive 171, recovered 30/30.
- **heavy/κ=0.5/decay**: sat@5, long blocks 11, core 1/30, P3 1, archive 155, recovered 30/30.
- **heavy/κ=0.5/supersede**: sat@19, long blocks 28, core 0/30, P3 25, archive 167, recovered 30/30.
- **heavy/κ=0.5/both**: sat@never, long blocks 11, core 1/30, P3 0, archive 154, recovered 30/30.
- **heavy/κ=0.5/tuned**: sat@19, long blocks 28, core 0/30, P3 25, archive 167, recovered 30/30.

- **churn/off**: sat@5, long 26, core 0/30, sup=0 dedup=0 decay=0 reheat=0, arch 123.
- **churn/supersede**: sat@29, long 26, core 0/30, sup=6 dedup=0 decay=0 reheat=0, arch 119.
- **churn/sup-fast**: sat@29, long 26, core 0/30, sup=6 dedup=0 decay=0 reheat=0, arch 119.
- **churn/both**: sat@never, long 6, core 2/30, sup=6 dedup=0 decay=21 reheat=30, arch 135.
- **dupheavy/off**: sat@12, long 16, core 7/20, sup=0 dedup=0 decay=0 reheat=0, arch 168.
- **dupheavy/supersede**: sat@never, long 5, core 2/20, sup=154 dedup=12 decay=0 reheat=0, arch 145.
- **dupheavy/sup-fast**: sat@never, long 5, core 2/20, sup=154 dedup=12 decay=0 reheat=0, arch 145.
- **dupheavy/both**: sat@never, long 2, core 3/20, sup=152 dedup=13 decay=3 reheat=40, arch 147.

### 5.3 The two forgetting drivers disagree on the same nominal regime (major)

`forget_exp.py` and `forget_bench.py` both claim to run "heavy @ κ=0.5", but their message generators differ (ports `80+i` vs `80+i%19`), which changes StubChat's sampled replies and therefore the whole eviction cascade:

| strategy | driver | sat@ | long blk | core | P3 | archive | peak |
|---|---|---|---|---|---|---|---|
| off | forget_exp | 5 | 26 | 0/30 | 31 | 174 | 898 |
| off | forget_bench | 5 | 28 | 0/30 | 29 | 171 | 895 |
| decay | forget_exp | 5 | 11 | 1/30 | 1 | 155 | 886 |
| decay | forget_bench | 5 | 11 | 1/30 | 1 | 155 | 886 |
| supersede | forget_exp | 19 | 27 | 0/30 | 6 | 148 | 897 |
| supersede | forget_bench | 19 | 28 | 0/30 | 25 | 167 | 895 |
| both | forget_exp | never | 7 | 2/30 | 0 | 157 | 896 |
| both | forget_bench | never | 11 | 1/30 | 0 | 154 | 885 |

The paper's `tab:forget_heavy` uses the **forget_bench** numbers, but the prose finding quotes a **forget_exp** number ("the offload treadmill from 31 to 1"). Under forget_bench it is 29 → 1. A reviewer who runs `forget_exp.py` gets supersede-only P3=6 / arch=148 and will not be able to reconcile them with the table's P3=25 / arch=167. See `meta/figures/fig_meta_drivers.pdf`.

Other meta-findings from the rerun:
- **`tuned` is inert.** heavy/balanced `tuned` (h=40, floor 0.35) is identical to plain `supersede` in *every* recorded field. Decay cannot fire inside a 60-turn run at that curve: importance after 60 turns = 0.5^(60/40) ≈ 0.354 > floor 0.35. So the paper's claim that the gentler curve "removes adjudication pressure" is unsupported — it removes nothing; it merely disables decay.
- **`sup-fast` adds nothing** in balanced/churn/dupheavy (identical to `supersede` in all fields) — consistent with the paper's claim, but note sup-fast was never swept on heavy.
- **Reheating only does work where filler references current values**: churn/both reheat=30, dupheavy/both reheat=40, decay-only regimes reheat=0 (stub replies never echo identifiers).
- **Demotion pressure is regime-driven**: decay adjudications heavy=45 (any κ), balanced=10, churn/both=21, dupheavy/both=3.

## 6. Discrepancy ledger (paper text/tables vs measured data)

| id | location | severity | issue | fix |
|---|---|---|---|---|
| D1 | paper/main.tex:235 (tab:forget_heavy, heavy off k=0.75) | minor (transcription) | live core 2/30 → measured: 0/30 | set to 0/30, or move the 2/30 to the decay row where it belongs |
| D2 | paper/main.tex:279 (tab:forget_adv, balanced decay) | minor (transcription) | core 2/15 → measured: 3/15 | set to 3/15 (prose already says "2--3/15") |
| D3-supersede | paper/main.tex:280-282 (tab:forget_adv balanced supersede) | moderate (understates supersession by ~5x) | sup column = 4 → measured: 19 | set to 19 (or note the table reports a different kappa) |
| D3-sup-fast | paper/main.tex:280-282 (tab:forget_adv balanced sup-fast) | moderate (understates supersession by ~5x) | sup column = 4 → measured: 19 | set to 19 (or note the table reports a different kappa) |
| D3-both | paper/main.tex:280-282 (tab:forget_adv balanced both) | moderate (understates supersession by ~5x) | sup column = 4 → measured: 19 | set to 19 (or note the table reports a different kappa) |
| D4 | paper/main.tex:297 (prose "Saturation breaks") | moderate (mixed provenance) | "offload treadmill from 31 to 1 phase-3 firing" mixes two drivers: forget_exp baseline=31, forget_bench baseline=29 → measured: forget_exp baseline P3=31; forget_bench heavy/off/0.5 P3=29 | use one driver in prose: "29 to 1" (forget_bench) or state both |
| D5 | paper/main.tex:300 | minor (counting) | "Across all 44 strategy runs" → measured: forget_bench has 38 runs; forget_exp adds 4 (=42, of which the 4 duplicate heavy@0.5); 44 = 38 + 6 synthetic (not strategy runs) | say "all 38 strategy runs" or clarify that 44 includes the 6 synthetic baseline runs |
| D6 | paper/main.tex (prose "Honest costs", tuned row) | moderate (claim not supported) | gentler curve h=40/floor 0.35 "removes adjudication pressure but re-saturates the long tier" → measured: heavy tuned identical to supersede-only in ALL fields (sup=7 vs 7, sat=19, P3=25); decay never fires within 60 turns since 0.5**(60/40)=0.354 > floor | state that at h=40/floor 0.35 decay is inert over a 60-turn run, so "tuned" reduces to supersede-only; or extend the run / lower floor |
| D7 | forget_bench.py docstring + paper prose "Duplicates never enter" | moderate (metric contract broken) | "admitted: long-tier blocks admitted per emitted fact (baseline ~3.0 for dupheavy, both <1)" -- metric not implemented → measured: archived_fact_copies/emitted = 2.65 (off) vs 2.65 (both); no admitted-blocks counter exists | count long-tier admissions per emitted fact from events, or drop the claim; dedup adjudications (12-13) are real |
| D8-off | forget_exp.py vs forget_bench.py "heavy @ kappa=0.5" | major (two drivers disagree on the same nominal regime; paper tables use forget_bench, prose quotes a forget_exp number) | forget_exp: long=26, P3=31, arch=174, peak=898 → measured: forget_bench: long=28, P3=29, arch=171, peak=895 | unify message generators (ports differ: 80+i vs 80+i%19) or retire forget_exp; label every number with its driver |
| D8-supersede | forget_exp.py vs forget_bench.py "heavy @ kappa=0.5" | major (two drivers disagree on the same nominal regime; paper tables use forget_bench, prose quotes a forget_exp number) | forget_exp: long=27, P3=6, arch=148, peak=897 → measured: forget_bench: long=28, P3=25, arch=167, peak=895 | unify message generators (ports differ: 80+i vs 80+i%19) or retire forget_exp; label every number with its driver |

Severity classes: *minor* = transcription/counting only; *moderate* = claim not supported by the shipped data or mixed provenance; *major* = numbers a reviewer cannot reconcile from the committed code.

## 7. Verdict

- **Reproducibility: strong.** Every aggregate dataset regenerates byte-for-byte with the new submodule; the deterministic stub engine has no hidden state or randomness. The `README` claim "re-runs are exact" holds for the data.
- **Behavioural equivalence: confirmed.** Default-off forgetting strategies preserve prior behaviour exactly on all six synthetic runs; the only effect of the new code on those runs is mirror schema (`importance`, `last_access`).
- **Reporting quality: needs a patch pass.** 11 discrepancies, incl. two *major* (driver disagreement + prose mixing drivers) and one broken metric contract. None invalidate the headline claims (budget invariant, offload-don't-destroy, saturation breaking), but they are reviewer-visible.
- **Build: incomplete artifact.** `paper/build.sh` cannot compile from repo contents alone (needs MetaFont base / font map configuration that was present on the original machine). Either commit a working `pdftex.map` + generated pk cache, or document the TeX prerequisites.

## 8. Recommended actions

1. Patch `paper/main.tex`: D1 (0/30), D2 (3/15), D3 (4→19), D4 ("29 to 1" or label both drivers), D5 ("38 strategy runs"), D6/D7 wording.
2. Merge `forget_exp.py` into `forget_bench.py` (or mark forget_exp as a deprecated smoke test) so one canonical heavy@κ generator exists; regenerate `tab:forget_heavy` from that single source.
3. Implement the documented admission metric in `forget_bench.py` (`admitted_per_fact`) or drop the "~3.0 vs <1" claim; keep dedup adjudication counts, which are real (12/13).
4. Consider running a longer horizon (e.g. 120 turns) or a lower floor so `tuned` actually exercises decay; otherwise drop the row.
5. Commit the TeX build prerequisites or switch `build.sh` to system `pdflatex` with `updmap`-generated maps; add a CI job that runs `run_all.sh` in a clean checkout.
6. If the paper wants the new engine's numbers, re-run and commit the six changed `context.jsonl` mirrors (schema drift) — they are currently uncommitted working-tree changes.

## 9. Files produced by this review

| file | contents |
|---|---|
| `meta/META_ANALYSIS.md` | this report |
| `meta/reproduction_report.json` | environment, provenance, md5 reproduction, mirror/figure/test deltas |
| `meta/discrepancies.json` | machine-readable discrepancy ledger (11 entries) |
| `meta/drivers_heavy05.json` | forget_exp vs forget_bench on heavy @ κ=0.5 |
| `meta/committed/*.json` | the committed (old) datasets extracted from git HEAD |
| `meta/figures/fig_*.pdf` | figures rendered from the rerun (artifact `paper/figures/` untouched) |
| `meta/figures/fig_meta_drivers.pdf` | driver-divergence figure |
| `meta/make_figs_meta.py` | patched copy of make_figs.py that writes into meta/ |