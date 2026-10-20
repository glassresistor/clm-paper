# clm-mem paper artifact (v0.3.0)

Research artifact for *"clm-mem: A Zero-Training Memory Harness for Open Chat
Models"* — a self-classified long/short-term memory harness with a
deterministic three-phase eviction engine, evaluated on synthetic stress
regimes against a deterministic stub backend.

## Layout

| Path            | What it is |
|-----------------|------------|
| `paper/main.tex`, `paper/main.pdf` | The report; compiles via `paper/build.sh` (locally built pdflatex format, `paper/texsrc/`, `paper/pfb/`). |
| `clm-mem/`      | The harness source package (14 modules, 3,012 lines), its pytest suite (`tests/`) and README. Installed with `pip install -e clm-mem`. |
| `clm_exp.py`    | Experiment driver: runs the real `MemoryHarness` on stub backends over two regimes x three kappa values and writes `exp-data/results.json`. |
| `make_figs.py`  | Renders the four data figures from `exp-data/results.json`. |
| `make_arch.py`  | Renders the architecture schematic (`fig_arch.pdf`). |
| `exp-data/`     | Per-run mirrors (`context.md`, `context.jsonl`, `archive.jsonl`) and the aggregate `results.json` committed as evidence. |

## Reproducing

```bash
bash run_all.sh   # clm_exp.py -> make_figs.py -> make_arch.py -> paper/build.sh
```

The committed `exp-data/results.json` was reproduced byte-for-byte from
`clm_exp.py` on Python 3.13 / matplotlib 3.x; the harness is deterministic
(StubChat), so re-runs are exact. Unit/integration tests: `pytest clm-mem/tests`.

## Notes for reviewers

- Quantitative results are engine-level (deterministic stub backend): they
  validate budget enforcement and the offload-don't-destroy invariant, not
  model judgment. Real-model benchmarks (LoCoMo, LongMemEval, RULER) are a
  plan, described as such in the paper.
- `clm-mem/workspaces/` and `clm-mem/smoke/` are local serve/demo runtime
  state and are git-ignored; they are not part of the artifact.
