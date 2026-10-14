# DocPilot Progress (part 2)

Continues the session log of [progress.md](progress.md) ("Right now" and the phase
checklist stay there). Newest session on top.

---

## Session log

### 2026-10-14, session 10: C0 retrieval eval, run by the learner (hands-on)

- Learner asked for a hands-on walkthrough (terminal, venv, reading the table and the
  JSON). Mentor guide: activate venv, `git restore` a stray editor comment (Pyrefly
  `ignore` line in `evals/common.py`) so the run is not `+dirty`, predict, run, read.
- Learner prediction (before the run): "about 3 of 19 will have the right chunk in the
  top 5, because it has the high recall@5" (circular reason). Hand check of q-005: not
  done (learner answered "all metrics are 5 only"; explained in chat).
- Real output, `python -m evals.run_retrieval_eval --split dev --config-id C0`, commit
  `06891f1` clean, laptop CPU: n=19; Recall@1 0.526, Recall@3 0.842, **Recall@5 0.842**,
  strict Recall@5 0.781, **MRR 0.667**, **nDCG@5 0.670**; search p50 1.3 ms, p95 2.2 ms
  (warm, n=19). File `evals/results/2026-10-14_C0_dev_retrieval.json`.
- Misses at @5 (3 of 19): q-017 paraphrase (GET "payload" vs doc "body", rank 6), q-018
  table-or-code (bullet list, 1 of 2 snippets at rank 6), q-023 how-to (path-param Enum
  "fixed set of allowed values" vs doc "predefined values"; not in top 10, the
  query-params Enum tip wins). Per-type rows have n = 1 to 5: read as examples, not scores.
- `evals/ABLATION.md` C0 retrieval columns filled. Next: L0 latency, abstention (hands-on).
