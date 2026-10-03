# Phase 0: Foundations (Implementation Plan)

**Goal of the phase:** a clean project skeleton, a working Python environment, and a
hands-on feel for embeddings and cosine similarity, so every later phase stands on solid
ground.

**Teaching companion:** `docs/teaching/phase_0_foundations.md`

**Status note:** `PROJECT_DOCUMENTATION.md` says Phase 0 is done, but this repo has no code.
If the learner has the files elsewhere, we copy them in and review them. Otherwise we
rebuild them here. Either way, steps 0.1 and 0.2 are needed in this repo.

---

## Step 0.1: Project skeleton

**Goal:** folders and safety files exist before any code.

**Files created**

```text
docpilot_rag/
├── .gitignore
├── .env.example
├── README.md            (already exists; expanded in Phase 7)
├── labs/                # small learning experiments, not part of the product
├── src/docpilot/__init__.py
├── scripts/
├── tests/
├── evals/golden/
├── evals/results/
└── data/docs/           # gitignored
```

**`.gitignore` (key lines, with why)**

```gitignore
# secrets: API keys must never reach git
.env

# downloaded docs: license reasons, and the download script can recreate them
data/docs/
data/processed/

# local vector and database files: large, binary, and rebuilt by scripts
qdrant_local/
qdrant_storage/
*.sqlite
*.db

# models and caches
*.safetensors
*.bin
.cache/
hf_cache/

# python
.venv/
__pycache__/
*.egg-info/
.pytest_cache/
.ruff_cache/
```

**`.env.example`** (committed; the real `.env` is a copy with values filled in)

```dotenv
# Which LLM provider to use: groq | openrouter | ollama | gemini
LLM_PROVIDER=groq
GROQ_API_KEY=
OPENROUTER_API_KEY=
GEMINI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434/v1
```

**Done when:** `git status` shows `.gitignore`, `.env.example`, and folders; creating a
test `.env` file does **not** show up in `git status`.

---

## Step 0.2: Virtual environment and pinned dependencies

**Goal:** one isolated Python per project, with exact versions.

**Run**

```powershell
python --version                 # must be 3.11 or newer
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

**Files created**

- `pyproject.toml`: package name, Python version, `src` layout, ruff and pytest settings.
- `requirements.txt`: pinned versions. Each version is checked on PyPI on build day and
  recorded in `docs/decisions.md` (Rule 4, Rule 5).

```toml
# pyproject.toml (sketch)
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "docpilot"
version = "0.1.0"
requires-python = ">=3.11"

[tool.setuptools.packages.find]
where = ["src"]           # code lives in src/docpilot (decision D-013)

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
```

First dependencies (Phase 0 only): `sentence-transformers`, `numpy`, `pytest`, `ruff`.

```powershell
pip install -r requirements.txt
pip install -e .                 # editable install: src/docpilot importable everywhere
python -c "import docpilot; print('ok')"
```

**Done when:** `python -c "import docpilot"` prints `ok` from any folder in the project.

---

## Step 0.3: Lab 1, embeddings and cosine similarity

**Goal:** see with your own eyes that similar meaning gives similar vectors.

**File:** `labs/lab1_embeddings.py`

```python
"""Lab 1: what is an embedding, and what does cosine similarity measure?

Run: python labs/lab1_embeddings.py
"""
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"  # decision D-002


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """How much two vectors point the same way. 1.0 = same direction, 0 = unrelated."""
    # Written by hand on purpose, so you can see the formula.
    dot = float(np.dot(a, b))
    length_a = float(np.linalg.norm(a))
    length_b = float(np.linalg.norm(b))
    return dot / (length_a * length_b)


def main() -> None:
    model = SentenceTransformer(MODEL_NAME)  # downloads once (~130 MB), then cached

    sentences = [
        "How do I validate incoming request data?",
        "Pydantic models check the request body for you.",
        "My cat likes to sleep in the sun.",
    ]
    vectors = model.encode(sentences)  # one vector per sentence

    print("vector size:", len(vectors[0]))  # expect 384 for bge-small
    print("first 5 numbers:", vectors[0][:5])

    # Compare every pair, so you can see which sentences are "close"
    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences)):
            score = cosine_similarity(vectors[i], vectors[j])
            print(f"{score:.3f}  |  {sentences[i]}  <->  {sentences[j]}")


if __name__ == "__main__":
    main()
```

**Run:** `python labs/lab1_embeddings.py`

**Done when:** the learner can predict, before running, which pair scores highest, and
explain why the cat sentence scores lowest. (We record the real scores the learner sees;
we do not guess them here.)

**Break it on purpose:** change one sentence to a paraphrase with no shared words, run
again, and note what happens to the score.

---

## Step 0.4: Lab 2, keyword search vs meaning search

**Goal:** discover with your own data that each kind of search fails in a different place.
This is the reason hybrid search exists (Phase 3).

**File:** `labs/lab2_keyword_vs_meaning.py`

```python
"""Lab 2: keyword (word overlap) vs meaning (embeddings) on tiny examples."""
import numpy as np
from sentence_transformers import SentenceTransformer

DOCUMENTS = [
    "Use Query(max_length=50) to limit the length of a query parameter.",
    "Pydantic validates the request body and returns errors automatically.",
    "Docker images are built from a Dockerfile.",
]

QUESTIONS = [
    "what does max_length do",                 # exact identifier: keyword should win
    "how do I check incoming data is correct",  # paraphrase: meaning should win
]


def keyword_score(question: str, document: str) -> int:
    """Count shared lowercase words. A crude version of BM25 (no rare-word weighting)."""
    question_words = set(question.lower().split())
    document_words = set(document.lower().replace("(", " ").replace("=", " ").split())
    return len(question_words & document_words)


def main() -> None:
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    # BGE expects this prefix on questions only (see teaching notes). VERIFY on model card.
    prefix = "Represent this sentence for searching relevant passages: "
    doc_vectors = model.encode(DOCUMENTS, normalize_embeddings=True)

    for question in QUESTIONS:
        print("\nQUESTION:", question)
        q_vector = model.encode(prefix + question, normalize_embeddings=True)
        for doc, doc_vector in zip(DOCUMENTS, doc_vectors):
            meaning = float(np.dot(q_vector, doc_vector))  # normalized, so dot = cosine
            keyword = keyword_score(question, doc)
            print(f"  keyword={keyword}  meaning={meaning:.3f}  {doc[:60]}")


if __name__ == "__main__":
    main()
```

**Done when:** the learner writes two sentences in `docs/progress.md` describing which
question each method got right, in their own words, based on their own output.

---

## Phase 0 gate

- [ ] skeleton committed; `.env` proven ignored
- [ ] venv works; `pip install -e .` works; versions pinned and recorded
- [ ] lab 1 and lab 2 run; learner explains outputs
- [ ] D-002 (bge-small) entry has "verified on" date for the model card
- [ ] interview notes for Phase 0 written in own words
- [ ] `git tag phase-0`

No ablation row for Phase 0: there is no retrieval system yet.
