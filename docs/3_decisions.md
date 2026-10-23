# Decision Log (part 3)

Continues [2_decisions.md](2_decisions.md) (D-038 to D-056), which reached the
500-line limit. Same format: what, why, alternative, why not.

---

## D-057: generation eval v0 with an LLM judge; step 3.7 built but not run (2026-10-22)

- **What:** `evals/run_generation_eval.py` + `evals/judge_prompts.py`: retrieve (best or
  dense) -> `rag.generate()` -> ONE judge call (claims + supported, correctness yes/partly/no,
  relevancy 1-5) -> deterministic abstention check. Generator and judge outputs cached;
  ~20% of judged items written to `evals/spot_checks/` for a human verdict. MLflow
  experiment `docpilot-generation`. `git_commit()` ignores `evals/spot_checks/`.
- **Judge:** `qwen/qwen3.8-27b` on Groq (listed on `/openai/v1/models` with the learner's
  key, 2026-10-22; preview model, may disappear). Different family from the generator
  (gpt-oss), so it does not grade its own style (Rule 11). Temperature 0. Smoke test: it
  caught a planted unsupported claim (faithfulness 0.5).
- **Numbers (`4c75fac`, 10 judged + 5 unanswerable):** faithfulness 1.000, hallucination
  rate 0.000, correctness 1.000, relevancy 5.0, abstention 1.000, LLM p50 990 ms.
- **Why one judge call and n=10:** free-tier tokens (200K per day per model); one call does
  all three checks; the cache makes a later `--n 20` pay only for the new questions.
  **G-dense not run** (deadline, quota).
- **Step 3.7 (embedding comparison):** `evals/compare_embedders.py` is built and tested
  (5 models pinned, prefixes from the model cards) but **not run**: the 3-day deadline and
  a 3.5 GB download for a model change we would also have to re-index for. bge-small stays
  (D-002). `psutil==7.2.2` (already in the lock via accelerate) pinned in
  requirements-dev for its RAM column.
- **Alternative:** RAGAS / DeepEval. **Why not now:** own metrics first (Rule 8); they also
  need an LLM per metric (more quota).

## D-058: one retrieval front door in the app; scope cut for the deadline (2026-10-22)

- **What (step 3.10):** `retrieval/pipeline.py`: `RetrievalSettings` (hybrid, rerank
  candidates, reranker, top_k, ...), `BEST` (hybrid + MiniLM rerank 20, top 4) and
  `DENSE_ONLY` (the Phase 1/2 app), `retrieve()` (times embed/search/rerank) and
  `warm_up_models()`. `rag.ask()` now uses `retrieve()` (default BEST) and `generate()`;
  the API loads all models at startup (no cold first request). One real question: 4/4
  chunks from the right Docker page; embed 75, search 40, rerank 993, LLM 1591 ms (n=1).
- **Scope cut (learner, 2026-10-22, 3 days to submission):** Phase 4 (agents) and Phase 5
  (multi-agent, HITL) dropped; Phase 8 stretch dropped; 3.7 and 3.8 (metadata filters: 453
  chunks, 12 ms search, misses are tables not wrong-technology) skipped. Kept: light
  guardrails (Phase 6) and the core of Phase 7 production: Docker image, Prometheus +
  Grafana latency monitoring, GitHub CI/CD to GHCR, AWS S3 via Terraform (EC2 if time).
  `PROJECT_DOCUMENTATION.md` still describes the full plan; the README marks the dropped
  parts as future work. Never present them as done.

## D-059: Phase 6 light guardrails in plain Python, measured by a red-team run (2026-10-22)

- **What:** `src/docpilot/guardrails/`: `input_guard.py` (empty, too long, NFKC +
  zero-width clean-up, 4 injection pattern groups), `context_guard.py` (chunks in
  `<document id source>` boxes, `</document>` inside text escaped), `output_guard.py`
  (canary leak -> blocked, exact not-found sentence, cite-or-refuse incl. `【n】` and
  `【n†Lx-Ly】` styles, citation range check, API-key redaction). `rag.ask(guarded=True)`
  is the default; `guarded=False` keeps the Phase 3 pipeline for the "before" row. API
  returns `status` + `timings_ms`, never the rule that fired (logged server-side).
  `config.BLOCKED_PHRASE`. Red team: `evals/redteam/attacks.jsonl` (18 attacks, 6
  categories, deterministic markers), `evals/run_redteam.py` (cached LLM replies, poisoned
  chunk forced to rank 1). Generation eval `--guarded` (own cache file). +51 tests (252).
- **Numbers (`81e119d+dirty`; RT-v1 re-run clean on `9d3b85d` 2026-10-23, identical counts):** attack success 2/18 (0.111) before ->
  0/18 after; after-run stops: input guard 8, prompt/model 10, output guard 0. False
  blocks: input guard 0/84 golden questions, output guard 0/10 cached good answers. Guard
  time p50 0.012 ms (input), 0.042 ms (output). G-guard (dev, 10 + 5): faithfulness 1.0,
  correctness 1.0 (9 judged), **1 false refusal** (q-003, the model refused under the
  stricter prompt; old prompt answered "422 [3]"), abstention 0.933, LLM p50 998 ms.
- **Why plain Python:** Rule 8 (raw first); zero new dependencies; microseconds per check;
  every rule explainable in an interview.
- **Alternatives, why not now:** NeMo Guardrails / Guardrails AI (extra LLM calls per
  request on a free quota, more config to learn in 3 days); Llama Guard (a model to host
  on a CPU laptop); Presidio (spaCy model; our corpus is public docs, users do not paste
  personal data in this demo); topic-scope embeddings (off-topic was already refused by
  the prompt, 0/3 before); tool guards (no tools: agents were dropped, D-058). All are
  future work, never "done".
- **Long-file exception:** the learner asked for `docs/teaching/phase_6_guardrails_explained.md`
  as one file whatever its length; added to `ALLOWED` in `scripts/check_file_lengths.py`.
