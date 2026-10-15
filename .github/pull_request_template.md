## What changed

<!-- One or two sentences. -->

## Why

<!-- Plan step (e.g. "Phase 2 step 2.3") and decision id (e.g. D-035), or the bug it fixes. -->

## How I tested

<!-- Commands you ran and what you saw: pytest, ruff, a script run, a screenshot. -->

## Eval impact

<!-- Real numbers from evals/results/ (Recall@5, MRR, nDCG@5, abstention, p50/p95),
     before -> after, with the result file name. Or write: "no retrieval change". -->

## Checklist

- [ ] `pytest -q` passes
- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] `python scripts/check_file_lengths.py` passes (no file over 500 lines)
- [ ] no secrets, `.env`, downloaded docs or `qdrant_local/` in the diff
- [ ] new dependency? decision entry with version and date in `docs/decisions.md`
- [ ] `docs/progress.md` / `docs/2_progress.md` and the user guide updated
