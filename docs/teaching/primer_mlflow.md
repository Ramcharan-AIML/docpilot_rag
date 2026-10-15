# Primer: MLflow (experiment tracking) and how it differs from tracing

Used from: Phase 2 step 2.0 onward. Server mode: Phase 3 step 3.1. Decision: D-022.

---

## 1. Like I'm five

A scientist doing many experiments keeps a **lab notebook**. For every experiment they write:
what they tried (the recipe), what came out (the results), and they staple in the photos.
Weeks later they can flip back and say "experiment 14 was the best, and here is exactly how I
did it."

**MLflow is that lab notebook, kept automatically by your code.** Every eval run writes its
settings and scores into it, and a web page lets you sort, compare, and chart all runs.

Why we need it: by Phase 3 you will have 30+ eval runs (6 chunkers x sizes x embedders x
hybrid x rerankers...). A folder of JSON files becomes impossible to compare by eye.

---

## 2. The words

| MLflow word | Child meaning | DocPilot example |
|---|---|---|
| **Experiment** | one notebook | `docpilot-retrieval`, `docpilot-generation`, `docpilot-redteam` |
| **Run** | one page: one experiment you tried | "hierarchical chunking, size 400, bge-small, dev split" |
| **Params** | the recipe (inputs, do not change during the run) | `strategy=hierarchical`, `chunk_size=400`, `golden_version=v1` |
| **Metrics** | the results (numbers) | `recall_at_5`, `mrr`, `ndcg_at_5`, `p95_ms` |
| **Tags** | sticky labels for finding pages | `config_id=C4-400`, `git_commit=5924b95`, `ablation=true` |
| **Artifacts** | stapled files | the full results JSON, per-question CSV of failures |
| **Tracking server** | the library where all notebooks live | `mlflow server` (Phase 3, in Docker) |
| **Backend store** | where params/metrics/tags are saved | SQLite file (`mlflow.db`) |
| **Artifact store** | where the stapled files are saved | local folder (Phase 2), SeaweedFS bucket (Phase 3), S3 (optional, Phase 7) |
| **UI** | the web page to browse | `http://localhost:5000` |

---

## 3. What the code looks like

```python
# evals/tracking.py (sketch; VERIFY the MLflow API on the installed version)
import mlflow


def log_eval_run(config_id: str, params: dict, metrics: dict, results_path: str,
                 tags: dict) -> None:
    """Record one eval run in MLflow: recipe, scores, labels, and the full results file."""
    mlflow.set_experiment("docpilot-retrieval")
    with mlflow.start_run(run_name=config_id):
        mlflow.set_tags({"config_id": config_id, **tags})   # git commit, split, ablation=true
        mlflow.log_params(params)                           # strategy, chunk_size, model ...
        mlflow.log_metrics(metrics)                         # recall_at_5, mrr, ndcg_at_5 ...
        mlflow.log_artifact(results_path)                   # the full JSON with per-question rows
```

`run_retrieval_eval.py` calls this at the end of every run. The results JSON is still saved
in `evals/results/` (committed, so the history lives in git too). MLflow is the searchable
notebook on top.

**Generating `evals/ABLATION.md` from MLflow:**

```python
# evals/make_ablation.py (sketch)
runs = mlflow.search_runs(experiment_names=["docpilot-retrieval"],
                          filter_string="tags.ablation = 'true'")
# one row per config_id: newest run on the current golden version -> Markdown table
```

So the ablation table is never typed by hand. Numbers cannot be "remembered wrong".

---

## 4. How MLflow grows with the project

| Phase | Setup | Why |
|---|---|---|
| 2.0 | Local: `mlflow.set_tracking_uri("sqlite:///mlflow.db")`, artifacts in `./mlartifacts/` (both gitignored). UI: `mlflow ui` | Simplest start, nothing to run in the background |
| 2.0 | **Re-log C0** (from its saved JSON) so the baseline is in the notebook too | Every comparison starts from C0 |
| 3.1 | MLflow server in Docker Compose; artifacts in a SeaweedFS bucket via the S3 API | Learn client/server and object storage; several scripts can log at once |
| 3.9, 4.5, 6.1 | Extra experiments: `docpilot-generation` (judge model as a param), `docpilot-agents`, `docpilot-redteam` | Same notebook for every kind of eval |
| 7 | Stays a **development** tool on your machine (or a small container). Production does not need it | Do not spend VM RAM on it unless useful |

---

## 5. MLflow vs tracing (Langfuse / Phoenix): the important difference

| | **MLflow experiment tracking** | **Runtime tracing (Langfuse / Phoenix)** |
|---|---|---|
| Question it answers | "Which **recipe** is best?" | "What happened inside **this one request**?" |
| Unit | one **eval run** (hundreds of questions, one score) | one **user request** (one question, many steps) |
| When | offline, while experimenting (Phases 2-6) | online, while users use the deployed system (Phase 7) |
| Records | settings + aggregate scores + result files | each node, retrieved chunks, LLM calls, tokens, latency |
| Who looks | you, deciding what to keep | you, debugging a slow or wrong answer |
| Child version | the **lab notebook** of experiments | the **dashcam** recording of one car trip |

They complement each other. An eval run tells you hybrid search is better on average;
a trace tells you why question 42 still failed.

**A fact worth knowing (checked 2026-10-08):** MLflow 3 also added GenAI tracing and
LLM-judge evaluation. So when we close decision D-009 in Phase 7 (which tracing tool), MLflow
tracing is a third candidate beside Langfuse and Phoenix. One tool for both jobs would mean
less to run; we decide with current docs and the VM's RAM.

---

## 6. Why MLflow and not something else

| Option | Why not (for us) |
|---|---|
| JSON files only | Fine for 5 runs; painful to compare 50; no UI, no search |
| Weights & Biases | Excellent, but a hosted service with plan limits; data leaves the machine |
| TensorBoard | Built for training curves, not for comparing configs with params |
| A spreadsheet | Typed by hand: mistakes, and breaks "numbers only from real runs" |

MLflow: open source, free, runs locally, widely listed in job descriptions, and the same API
works against a local file or a server.

---

## 7. Common mistakes

1. Logging a metric with a different name in different runs (`recall5` vs `recall_at_5`):
   the comparison chart breaks. Keep names in one constants list.
2. Forgetting the golden version as a param: then you compare different exams.
3. Logging secrets (API keys) as params. Never.
4. Committing `mlflow.db` or `mlartifacts/` to git (they are gitignored).
5. Treating MLflow as the only copy: the results JSON in git is the durable record.

---

## 8. Self-check

1. Explain experiment, run, param, metric, tag, artifact with the lab-notebook story.
2. Why re-log C0 into MLflow in Phase 2?
3. How is `ABLATION.md` produced, and why never by hand?
4. MLflow tracking vs Langfuse tracing: different questions, different units. Explain.
5. Where do params/metrics live, and where do artifacts live, in Phase 2 vs Phase 3?
