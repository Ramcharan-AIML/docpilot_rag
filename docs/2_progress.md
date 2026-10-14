# DocPilot Progress (part 2)

Continues the session log of [progress.md](progress.md) ("Right now" and the phase
checklist stay there). Newest session on top.

---

## Session log

### 2026-10-14, session 10b: latency baseline L0 (learner run)

- Learner's paper check of q-001 `[0, 1, 0, ...]`: Recall@1 0, @3 1.0, @5 1.0, RR 0.5:
  all correct. Latency predictions: not given.
- Real output, `python -m evals.run_latency --split dev --config-id C0`, commit `8295859`
  clean, laptop CPU (Windows 11), Groq `openai/gpt-oss-120b`, 1 warm-up, sleep 2 s,
  n=22: embed_query p50 15.8 / p95 85.4 / max 102.9 ms; search 1.0 / 1.9 / 2.4 ms;
  llm 1060.4 / 1748.8 / 1858.6 ms; **total 1107.2 / 1763.7 / 1945.5 ms**;
  wall incl. 429 waits 5933.9 / 8208.5 / 8238.2 ms.
- **15 rate-limit (429) retries** from question 9 on (q-012 twice); server asked to wait
  1 to 7 s. Which Groq limit (requests or tokens per minute) was hit: n/a, headers not
  logged. The `total` column excludes the waits; `wall_with_retries` includes them.
- Lesson: the LLM is about 96% of total time (1060 of 1107 ms at p50); embedding warm is
  about 130x faster than the 1b cold runs (about 2000 ms incl. model load).

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
