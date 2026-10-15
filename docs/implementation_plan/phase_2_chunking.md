# Phase 2: Ingestion Quality and Chunking Experiments (Implementation Plan)

**Goal of the phase:** fix the data problems found in Phase 1, widen the corpus to three
domains (docs, learning material, interview prep; D-030), then compare the chunking
strategies on the same eval and pick a default **with evidence**.

**Teaching companion:** `docs/teaching/phase_2_chunking.md`

**Ablation rows filled here:** C1 recursive, C2 semantic, C3 parent-child, C4 hierarchical,
C5 contextual (plus size variants such as `C1-400`).
Note: `PROJECT_DOCUMENTATION.md` section 9 says "C1 to C6" for this gate, but the ablation
table in section 14.7 defines C6 as hybrid search (Phase 3). This plan follows the table.
Confirm with the learner.

```text
Phase 2 ingestion flow (each box is one file)

loader ─▶ cleaner ─▶ includes ─▶ blocks ─▶ metadata ─▶ chunkers/<strategy> ─▶ embed ─▶ store
                                                         │
                                         one Qdrant collection per strategy and size
```

---

## Step 2.0: MLflow experiment tracking (decision D-022)

**Goal:** every eval run from now on is recorded automatically in a searchable "lab
notebook", and `evals/ABLATION.md` is generated from it. Teaching: `teaching/primer_mlflow.md`.

1. Dependency: `mlflow` (VERIFY version on PyPI; consider `mlflow-skinny` if the full package
   is heavy; decision log entry; pin in `requirements-dev.txt`, since production does not
   need it).
2. `.gitignore`: add `mlflow.db`, `mlartifacts/`, `mlruns/`.
3. **File `evals/tracking.py`:** `log_eval_run(config_id, params, metrics, results_path, tags)`
   (sketch in the primer). Tracking URI from `config.MLFLOW_TRACKING_URI`
   (default `sqlite:///mlflow.db`).
4. `run_retrieval_eval.py` calls it at the end of every run. Params always include:
   `collection`, `strategy`, `chunk_size`, `overlap`, `embedding_model`, `model_revision`,
   `top_k`, `min_overlap`, `golden_version`, `split`. Tags: `config_id`, `git_commit`,
   `ablation` (`true` for runs that belong in the table).
5. **Re-log C0:** `scripts/relog_results_to_mlflow.py` reads `evals/results/*C0*.json` and
   logs it, so the baseline sits in the same notebook. Values are copied, never retyped.
6. Run `mlflow ui` and open `http://localhost:5000`. Sort runs by `recall_at_5`.

**Done when:** C0 appears in the MLflow UI with params, metrics, and the results JSON
attached, and its numbers equal the JSON exactly.

---

## Step 2.1: Refactor into packages (no behaviour change)

**Goal:** make room for six chunkers without breaking anything.

**Moves**

| From (Phase 1) | To |
|---|---|
| `src/docpilot/loader.py` | `src/docpilot/ingestion/loader.py` |
| `src/docpilot/chunker.py` | `src/docpilot/ingestion/chunkers/fixed.py` (+ `base.py` for `Chunk`) |
| `src/docpilot/embedder.py` | `src/docpilot/embedding/dense.py` |
| `src/docpilot/vector_store.py` | `src/docpilot/store/qdrant_store.py` |
| `src/docpilot/llm.py` | `src/docpilot/llm/client.py` |

**Done when:** all tests pass AND re-running the C0 eval gives **exactly** the same numbers.
A refactor that changes the numbers is a bug. This is your first regression test by hand.

---

## Step 2.2: `ingestion/cleaner.py`

**Goal:** remove HTML noise (colour tags from terminal screenshots, etc.) without touching
code blocks.

```python
"""Remove HTML noise from Markdown, leaving fenced code blocks untouched."""
import re

HTML_TAG = re.compile(r"</?(span|div|font|img|br)[^>]*>", re.IGNORECASE)
FENCE = "```"


def clean_markdown(text: str) -> str:
    cleaned_lines = []
    inside_code = False
    for line in text.splitlines():
        if line.strip().startswith(FENCE):
            inside_code = not inside_code    # entering or leaving a code block
            cleaned_lines.append(line)
            continue
        if inside_code:
            cleaned_lines.append(line)       # never edit code: it must stay exact
        else:
            cleaned_lines.append(HTML_TAG.sub("", line))
    return "\n".join(cleaned_lines)
```

**Test:** `tests/test_cleaner.py`: tags removed from prose; same tags inside a code fence
kept.

**Measure:** re-index with fixed chunking + cleaner, run eval. Record as `C0+clean` so we
know what cleaning alone did.

---

## Step 2.3: `ingestion/includes.py` (resolve code includes)

**Goal:** replace `{* ../../docs_src/first_steps/tutorial001_py310.py *}` with the real
code, so "show me a minimal app" can be answered.

1. Update `scripts/01_download_docs.py` to also download every referenced `docs_src` file
   (scan pages for markers, fetch each path from the same repo). VERIFY repo paths.
2. Resolver:

```python
"""Replace FastAPI include markers with the code they point to."""
import re
from pathlib import Path

# Matches {* path/to/file.py *} and also {* path hl[3] *} (extra options after the path)
INCLUDE_MARKER = re.compile(r"\{\*\s*(?P<path>\S+)[^*]*\*\}")


def resolve_includes(text: str, code_root: Path) -> tuple[str, list[str]]:
    """Return (new_text, missing_paths). Missing files are reported, not hidden."""
    missing: list[str] = []

    def replace(match: re.Match) -> str:
        relative = match.group("path").replace("../../", "")
        code_file = code_root / relative
        if not code_file.exists():
            missing.append(relative)
            return match.group(0)            # keep the marker so we can see it failed
        code = code_file.read_text(encoding="utf-8")
        return f"```python\n{code}\n```"

    return INCLUDE_MARKER.sub(replace, text), missing
```

**Done when:** `02_ingest.py` prints "includes resolved: N, missing: 0", and a question about
a minimal FastAPI app retrieves a chunk containing real code. Measure as `C0+clean+incl`.

---

## Step 2.4: `ingestion/blocks.py` (structure-aware parser)

**Goal:** turn a Markdown document into a list of `Block`s that later chunkers can respect.

```python
"""Split Markdown into blocks: heading, paragraph, code, table, list."""
from dataclasses import dataclass, field


@dataclass
class Block:
    kind: str                                  # heading | paragraph | code | table | list
    text: str
    heading_path: list[str] = field(default_factory=list)


def parse_blocks(text: str) -> list[Block]:
    blocks: list[Block] = []
    heading_path: list[str] = []
    buffer: list[str] = []
    buffer_kind = "paragraph"
    inside_code = False

    def flush() -> None:
        if buffer and "".join(buffer).strip():
            blocks.append(Block(buffer_kind, "\n".join(buffer), list(heading_path)))
        buffer.clear()

    for line in text.splitlines():
        if line.strip().startswith("```"):
            if not inside_code:
                flush()
                buffer_kind = "code"
            buffer.append(line)
            if inside_code:
                flush()                         # closing fence ends the code block
                buffer_kind = "paragraph"
            inside_code = not inside_code
            continue
        if inside_code:
            buffer.append(line)
            continue
        if line.startswith("#"):
            flush()
            level = len(line) - len(line.lstrip("#"))      # "## Title" -> 2
            title = line.lstrip("#").strip()
            heading_path[:] = heading_path[: level - 1] + [title]
            blocks.append(Block("heading", title, list(heading_path)))
            continue
        kind = "table" if line.lstrip().startswith("|") else "paragraph"
        if line.strip() == "" or kind != buffer_kind:
            flush()
            buffer_kind = kind
        if line.strip():
            buffer.append(line)
    flush()
    return blocks
```

Why hand-written and not `markdown-it-py`: Rule 8 (see it raw first), and our docs use a
small subset of Markdown. If edge cases pile up (nested lists, HTML tables), we switch and
log the decision. Lists are treated as paragraphs in v1; record that as a known limit.

**Tests:** a code block containing a `#` comment line is **not** treated as a heading; a
table stays one block; heading path is `["A", "B"]` under `## B` inside `# A`.

---

## Step 2.5: `ingestion/metadata.py`

**Goal:** every chunk knows where it came from, so we can filter (Phase 3) and cite.

| Field | How we get it |
|---|---|
| `domain` | `docs`, `learning` or `interview` (D-030), from the corpus register entry |
| `technology` | first folder under `data/docs/` (`fastapi`, `docker`, ...) |
| `doc_type` | path rules: `tutorial/` -> tutorial, `reference/` -> reference, else guide |
| `version` | from a per-technology setting in the download script (docs version downloaded) |
| `heading_path` | from `Block` |
| `has_code`, `has_table` | from block kinds inside the chunk |
| `content_hash` | `sha256(chunk.text)` |

The `Chunk` dataclass in `chunkers/base.py` grows these fields (see architecture section 7.2).

---

## Step 2.6: The chunking strategies (six general + Q&A pairs for interview files)

All live in `src/docpilot/ingestion/chunkers/`. Each exposes the same function shape:

```python
# chunkers/base.py
from typing import Protocol


class Chunker(Protocol):
    name: str
    def chunk(self, document: "Document", blocks: list["Block"]) -> list["Chunk"]: ...
```

**Size unit:** we switch from characters to **tokens** of the embedding model
(`get_model().tokenizer`), because models read tokens. VERIFY the model's maximum input
length on its card: if it is 512 tokens, an 800-token chunk is **silently truncated** when
embedded. Test sizes 200, 400, and (only if within the limit) larger.

| File | Strategy | Key logic | Settings recorded |
|---|---|---|---|
| `fixed.py` | 1 Fixed + overlap | Phase 1 code, token-based now | size, overlap |
| `recursive.py` | 2 Recursive | Try separators in order `["\n## ", "\n### ", "\n\n", "\n", ". ", " "]`; split on the first one that makes pieces fit; recurse on pieces still too big; merge small neighbours up to size | size, overlap, separators |
| `semantic.py` | 3 Semantic | Split into sentences (blocks for code/tables); embed each; cosine between neighbours; start a new chunk where similarity is below the Nth percentile; cap max size | percentile, max size |
| `parent_child.py` | 4 Parent-child | Parent = one section (heading + its blocks). Child = small pieces of the parent. Index **children**; store parents in `data/processed/parents_<collection>.json`; search children, return parent text | child size, parent max size |
| `hierarchical.py` | 5 Hierarchical | Walk blocks; group blocks under the same heading until size is reached; **never split code or table blocks**; prepend `heading_path` to chunk text ("FastAPI > Query Parameters > Optional") | size, prefix on/off |
| `qa_pairs.py` | 7 Q&A pairs (D-030) | For interview-prep files (group C): one chunk = one question **plus** its whole answer, found by headings like `### Q3.` or `**Q:**`; never split a pair; long answers keep the question as a prefix on every piece | pattern, max size |
| `contextual.py` | 6 Contextual | Take chunks from the best of 2-5; for each, LLM writes 1-2 sentences placing it in its document; prepend before embedding; keep `display_text` without context | base strategy, prompt version, LLM model |

### 2.6.1 Recursive sketch

```python
def recursive_split(text: str, max_tokens: int, separators: list[str],
                    count_tokens) -> list[str]:
    """Split on the biggest natural boundary that works; go smaller only when needed."""
    if count_tokens(text) <= max_tokens:
        return [text]
    if not separators:                          # nothing left: hard cut as a last resort
        return hard_cut(text, max_tokens, count_tokens)
    first, rest = separators[0], separators[1:]
    pieces = text.split(first)
    if len(pieces) == 1:                        # this separator is not in the text
        return recursive_split(text, max_tokens, rest, count_tokens)
    results: list[str] = []
    for piece in pieces:
        results.extend(recursive_split(piece, max_tokens, rest, count_tokens))
    return merge_small_pieces(results, max_tokens, count_tokens)
```

Why our own and not LangChain's `RecursiveCharacterTextSplitter`: Rule 8. After ours works,
we run LangChain's on the same docs and compare chunk counts; that comparison is a nice
interview story either way.

### 2.6.2 Contextual chunking: cost control

- Prompt: whole document (or the section, if the document is too long for the model) +
  the chunk, asking for "1-2 sentences that situate this chunk within the document".
- **Cache** results in `data/processed/context_cache.jsonl`, keyed by
  `sha256(prompt_version + chunk_text)`. A re-run costs zero calls.
- Sleep between calls to respect the free-tier rate limit (VERIFY current limit).
- Record total LLM calls and minutes taken. That cost is part of the result.

### 2.6.3 Parent-child and the eval

`run_retrieval_eval.py` gets a `--parent-store` option: when set, a hit is checked against
the **parent** text (the text the LLM will actually see), as the doc requires (section 14.2).

---

## Step 2.7: Docling for PDF/HTML (`ingestion/pdf_loader.py`)

**Goal:** learn layout-aware parsing on at least one PDF or HTML source with tables.

- VERIFY Docling's current API, its CPU speed, and its install size (it downloads layout
  models) before adding it. Decision log entry with "why not PyMuPDF" (faster, weaker on
  tables).
- Convert to Markdown, then feed the same `blocks.py` pipeline. One pipeline, many inputs.
- Add 3-5 golden questions that need that table.

---

## Step 2.8: More corpora and golden set v1

1. `scripts/doc_sources.py`: the **corpus register** (D-030), a plain Python list of
   entries: `domain` (docs / learning / interview), `technology` or topic, URLs or local
   path, licence + licence link, version or commit, date checked, and `public` or
   `local_only`. A test fails if any entry has no licence or no visibility flag.
   - **Group A docs:** Pydantic and Docker first, then Qdrant, LangChain, LangGraph, Redis.
   - **Group B learning material:** only open-licence sources, each licence checked on the
     day (candidates: open textbooks, library user guides, free course notes). Start with
     2-3 sources on embeddings, RAG and evals.
   - **Group C interview prep:** the learner's own `docs/interview/*.md` (public, own work)
     plus any open-licence Q&A. Anything else the learner adds is `local_only`: indexed on
     the laptop only, never committed, never in the public deployment.
2. Grow golden set to about 60 questions; more code, table, and comparison questions, and
   **at least 10 per domain** (concept explanations for B, interview questions for C, plus
   out-of-scope questions per domain for abstention). Each question records its `domain`.
3. Bump `evals/golden/VERSION` (e.g. `v1`). **Every result JSON stores the golden version.**
4. Re-run C0 on golden v1. Rows in one ablation table must all use the same golden version,
   otherwise you compare different exams.

---

## Step 2.9: Run every strategy and compare

**Files:** `scripts/02_ingest.py` (gains `--strategy`, `--size`, `--collection`),
`scripts/run_chunking_matrix.py` (loops strategies x sizes, ingests, evaluates),
`evals/make_ablation.py` (MLflow runs tagged `ablation=true` -> `evals/ABLATION.md`;
falls back to the results JSON files if MLflow is unavailable).

```powershell
python scripts/02_ingest.py --strategy hierarchical --size 400 --collection docs_hier400_bgesmall_v1
python evals/run_retrieval_eval.py --collection docs_hier400_bgesmall_v1 --split dev --config-id C4-400
python evals/make_ablation.py
```

Output tables in `ABLATION.md`:

1. Main table: one row per config (Recall@5, MRR, nDCG@5, chunk count, ingest minutes).
2. **Per-type table:** rows = configs, columns = question types (Recall@5). Code questions
   may favour a different strategy than prose. A different winner per type is a finding,
   not a failure.
3. **Per-domain table (D-030):** rows = configs, columns = docs / learning / interview
   (Recall@5, MRR). Q&A-pair chunking is expected to matter for interview files; measure it,
   do not assume it. A per-domain winner may justify different strategies per domain.

Choosing the winner: best dev Recall@5 and MRR; ties broken by simplicity and ingest cost.
Then run the **test** split once for the winner and C0. Record both.

---

## Step 2.10: CI retrieval eval gate (decisions D-011, D-024)

**Goal:** a pull request that makes retrieval worse cannot be merged.

1. **Fixture corpus** `tests/fixtures/corpus/`: 5 to 10 short pages **we write ourselves**
   (so licensing is never an issue), covering code blocks, a table, exact identifiers, and
   prose. Plus `evals/golden/ci.jsonl`: about 15 questions on that corpus.
2. **`evals/check_gate.py`**: compares a run's Recall@5 and MRR with `evals/baseline_ci.json`;
   exits 1 if either is below `baseline - tolerance` (tolerance recorded with its reason).
3. **New CI job `eval-gate`** in `.github/workflows/ci.yml`: install -> ingest the fixture
   corpus into **in-memory / local-mode** Qdrant (no Docker service needed yet) -> run the
   retrieval eval on `ci.jsonl` -> `check_gate.py`. No LLM calls, no secrets.
4. Branch protection: add `ci / eval-gate` as a required check on `main` and the phase branch.
5. **Prove it:** a PR that removes the BGE query prefix (or swaps to a broken chunk size)
   must fail the gate. Screenshot it. Close the PR.
6. Updating the baseline is a deliberate act: a PR that changes `baseline_ci.json` must say
   why in its description (an improvement was kept).

---

## Phase 2 gate

- [ ] tests for cleaner, includes, blocks, each chunker (code blocks never split)
- [ ] C0+clean and C0+clean+incl rows recorded (what data quality alone did)
- [ ] C1 to C5 rows (with sizes) on golden v1, dev; winner + C0 on test
- [ ] per-type and per-domain breakdown tables; corpus register complete (licence + visibility)
- [ ] chosen default strategy written in `decisions.md` with the numbers
- [ ] contextual chunking cost recorded (LLM calls, minutes)
- [ ] versions pinned (Docling, any tokenizer extras), licenses linked for each corpus
- [ ] every run logged in MLflow (C0 re-logged); `ABLATION.md` generated, not typed
- [ ] CI `eval-gate` required on `main`; failing-gate PR demonstrated
- [ ] interview notes written; merged to `main` via PR; tag `phase-2` pushed
