# DocPilot Progress (part 3)

Continues the session log of [2_progress.md](2_progress.md) ("Right now" and the phase
checklist stay in [progress.md](progress.md)). Newest session on top.

---

## Session log

### 2026-10-23, session 43: Phase 7 Stage A1 private chats (D-063)

- New mentor session takes over from "Phase_Guardrails". PR #6 merged; branch `production`.
- Learner keeps personal notes off GitHub later (cleanup on main before sharing the link;
  `.gitignore` lines written but commented out by the learner for now).
- Primer `production/02_teach_public_app_safety.md` (moved from teaching/) (all of Stage A) written before building.
- A1 built: `chats.owner` + migration, `X-Visitor-Id` on every chat call, 404 for others,
  400 for a bad id. 313 tests pass (8 new), ruff clean, React build OK.
- Learner's check: predicted Incognito would show the same chats (wrong: own localStorage =
  new id = new visitor); predicted cleared site data = chats gone from view (right; rows
  stay in the db). First run showed the same 3 old chats in both windows: the API on :8000
  was the previous session's server started 11:00, BEFORE the change (lesson: restart after
  a code change). After a restart: two separate visitors, old owner-less chats hidden. PASS.
- A2: Groq console (learner) for gpt-oss-120b: 30 RPM, 1K RPD, 8K TPM, 200K TPD.
  `scripts/measure_tokens.py` (learner run, n=5 dev): 1,094-1,272 tokens per answer,
  median 1,149. Learner did not predict ("go with your assumption"). Limits set from it
  (plan's 10/min would exceed 8K TPM): visitor 3/min 20/day, IP 3/min 40/day, site 3/min
  80/day, uploads 10/day/IP, 3 files/chat. 322 tests. Live check skipped by the learner.
- A3+A4: 2 answer seats (BoundedSemaphore), "Waiting in line" stage event, Groq 429 =
  busy message (stream) / 503 (`/ask`). 326 tests pass, React build OK.
- Learner asked for `docs/production/01_production_log.md`: one simple tracking file for
  every production step (picture, files, small words, results, commands; no add/commit/
  push). Written for A0-A4, kept up to date from now on.
- A5 (uploads collection `memory=cold` + payload indexes; verified on Docker Qdrant
  1.19.1 with a temp collection), A6 (`chat/cleanup.py`, hourly, public mode, 7 days), A7
  (`/ready`). 332 tests pass. The running :8000 server was old code (404 on /ready).

### 2026-10-23, session 42: React chat app (D-061)

- Learner rejected Streamlit; wanted ChatGPT/NotebookLM experience; chose React + chats,
  memory, per-chat files, streaming, fast uploads; Phase 7 cut to Docker + Prometheus.
- Measured first: fast reader 10.8 s vs Docling 182 s (43 pages) -> 500-page limit.
- Built chat/ (store, jobs, memory, service), chat_api.py, chat_stream, Qdrant chat
  filter, web/ (React 19 + Vite 8.3.4). 305 tests. Live: upload 0.10 s -> ready 18.9 s;
  memory and "what was my first question?" worked; streaming works through the proxy.
- Learner liked it; asked for a light premium theme (done: indigo accent, shadows, dark
  switch), keep Streamlit (kept; its upload panel no longer works), rename the branch to
  frontend-ui (commands given). Production (small Phase 7) starts on the learner's word.

### 2026-10-23, session 41: Phase 6 closed; Streamlit UI with PDF uploads (D-060)

- Learner re-ran RT-v1 on the clean commit `9d3b85d`: identical counts; merged PR #5,
  tagged `phase-6`. Explained the red-team output and RAGAS (decision: not now, own
  judge already covers faithfulness/correctness/relevancy; future work).
- Learner chose Streamlit + a SEPARATE uploads library. Built: `ui/` (app + api_client),
  API `/upload`, `/uploads`, `/health`, `library` on `/ask`, `ingestion/uploads.py`,
  store helpers, `sources.UPLOADS` (local_only). +33 tests (285), incl. AppTest of the page.
- Caught by tests: uploads had no licence-register entry (metadata raised KeyError).
- Smoke test (real API): upload 16.5 s first (Docling load) then 3.4 s; fake PDF refused;
  handbook fact answered with [1]; poisoned PDF ignored; main library said not found;
  attack blocked. Scale question answered honestly: only 20 docs tested.

### 2026-10-22, session 40: Phase 6 light guardrails, built and measured (D-059)

- Learner asked for the whole of Phase 6 at once, then ONE explanation file (any length)
  plus an interview file, written only after the runs. No commits by the mentor.
- Built `guardrails/` (input, context, output), `rag.ask(guarded=True)`, API `status` +
  `timings_ms`, red-team set (18) + `evals/run_redteam.py`, generation eval `--guarded`;
  +51 tests (252). Fixed during build: first input pattern blocked "What is the system
  prompt in an LLM app?" (and would block "override the default rules"); gpt-oss cites
  as `【1】` and `【1†L1-L4】` (seen in cache); stacked-poison bug in the runner.
- RT-v1 (`81e119d+dirty`): attacks 2/18 -> 0/18; input 8, model 10, output 0; false
  blocks 0/84 + 0/10; guard p50 0.012 / 0.042 ms. G-guard: faithfulness 1.0, correctness
  1.0, 1 false refusal (q-003, model under the stricter prompt), LLM p50 998 ms.
- Docs: phase_6_guardrails_explained.md (one file, allowed long), phase_6_interview.md
  rewritten with real numbers, ABLATION safety table, USER_GUIDE section 53.

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
