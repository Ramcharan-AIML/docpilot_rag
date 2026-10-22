# DocPilot Progress (part 3)

Continues the session log of [2_progress.md](2_progress.md) ("Right now" and the phase
checklist stay in [progress.md](progress.md)). Newest session on top.

---

## Session log

### 2026-10-22, session 39: Phase 3 gate (FINAL-test), final results sheet, handoff

- docs/interview/final_results.md (best numbers + 5 resume lines), teaching
  primer_prometheus_grafana.md; context sent to the Phase_Guardrails session.
- FINAL-test (`c1fb7dd`, test n=17): R@1 0.647, R@3 0.824, R@5 0.941, MRR 0.765, nDCG
  0.790 (C0: 0.353 / 0.941 / 0.608). Same code run dirty earlier: identical scores, rerank
  p50 473 vs 895 ms (laptop load).
- Learner asked for a UI (demo); proposed Streamlit after guardrails (decision pending).

### 2026-10-22, session 38: 3.9 generation eval, 3.10 front door, scope cut (D-057, D-058)

- Learner: 3 days to submit; wants production (Docker, Prometheus/Grafana, CI/CD, AWS S3,
  Terraform) taught from zero; dropped agents/multi-agent/stretch; 3.7 and 3.8 skipped.
- 3.9 built (one judge call per answer, qwen judge, caches, spot checks); learner ran
  G-best `--n 10` (`4c75fac`): faithfulness 1.0, correctness 1.0, abstention 1.0, LLM p50
  990 ms. Checked q-006: correct answer from other chunks despite a retrieval miss.
- 3.10: rag.ask() now uses retrieve() (hybrid + MiniLM); API warms models at startup;
  tests updated (201). One real ask(): 2.7 s total (rerank 993 ms, LLM 1591 ms, n=1).

### 2026-10-22, session 37: steps 3.6 query transforms (D-056) and 3.7 built

- Built query_transforms.py, multi_search(), transform_cache.py, --transform; 3.7
  compare_embedders.py (5 models, pinned, prefixes from model cards), all_payloads();
  psutil pinned in requirements-dev; +11 tests (194). Plan fix: 3.7 script in evals/.
- Learner ran 4 transform rows (`f779c39`, 164 Groq calls, 0 retries): all R@5 0.878 =
  C7-mini-r20; changed top-10 sets of 15-17 questions but the answer moved only for q-017.
  Decompose split nothing. No transform kept. 3.7 not run yet.
