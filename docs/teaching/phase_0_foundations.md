# Teaching Notes, Phase 0: Foundations

Plan file: `docs/implementation_plan/phase_0_foundations.md`

---

## 1. Why a project skeleton before any code

**Like I'm five:** before you cook, you put out separate bowls for vegetables, spices, and
rubbish. If you throw everything on one plate, you cannot find anything, and the rubbish
ends up in the food.

**What it really is:** separate folders for product code (`src/`), run-once scripts
(`scripts/`), tests (`tests/`), evaluation (`evals/`), data (`data/`), learning experiments
(`labs/`), and documentation (`docs/`).

**Why it matters for interviews:** a reviewer opens your GitHub and judges you in 30
seconds. A clean layout says "this person has worked on real codebases".

---

## 2. `.gitignore` and `.env`: keeping secrets out

**Like I'm five:** your house key should never be taped to the front door, even if the
door is in a quiet street.

**What it really is:**

- `.env` holds secrets (API keys). Python reads it with `python-dotenv` at start-up.
- `.gitignore` tells git to never track certain files: `.env`, downloaded docs, model files,
  database files.
- `.env.example` has the same variable names with empty values, so others know what to set.

**What happens if you get it wrong:** bots scan public GitHub for keys within minutes.
A leaked key can be abused before you notice. Deleting the commit does not help; the key
must be revoked at the provider.

**Why not put keys in `config.py`:** `config.py` is committed. Code is public; secrets are not.

---

## 3. Virtual environments

**Like I'm five:** each project gets its own toolbox. If project A needs a size-10 spanner
and project B needs size 12, they do not fight over one shared box.

**What it really is:** `python -m venv .venv` creates a private copy of Python with its own
`site-packages`. Activate it and `pip install` puts packages there, not system-wide.

**Why pin versions (`package==1.2.3`):** libraries like LangGraph change their API often.
"It worked last week" usually means "a new version was installed this week". Pinned
versions make every machine (your laptop, CI, the server) install the exact same thing.

**Why not conda / poetry / uv:** all are fine. `venv` + `pip` is built in, so there is
nothing extra to learn or explain. (If a faster installer becomes worth it later, that is a
decision log entry.)

**Editable install (`pip install -e .`):** Python sees `src/docpilot` as an installed package
but reads the files directly from your folder, so code changes apply instantly. Scripts,
tests, and the API all `import docpilot` the same way. No `sys.path` hacks.

---

## 4. Embeddings

**Like I'm five:** imagine every sentence gets a spot on a giant map. Sentences that mean
similar things are placed near each other. "How do I validate input?" lives near
"Pydantic checks the request body", and far from "My cat sleeps in the sun". An embedding
is the **map coordinates** of a sentence.

**What it really is:** a neural network (here `BAAI/bge-small-en-v1.5`) reads text and
outputs a fixed-length list of numbers (384 for bge-small). The model was trained so that
texts with similar meaning get vectors pointing in similar directions.

**What is happening when `lab1_embeddings.py` runs:**

1. `SentenceTransformer(MODEL_NAME)` downloads the model once into the Hugging Face cache
   folder, then loads it into RAM.
2. `model.encode(sentences)` splits each sentence into **tokens** (word pieces), runs them
   through the network, and pools the result into one 384-number vector per sentence.
3. Our `cosine_similarity` compares pairs.

**Tokens, briefly:** models do not read words; they read word pieces. "unbelievable" might
become "un", "##believ", "##able". Models have a maximum number of tokens they read
(check the model card); anything longer is cut off silently. This matters a lot in Phase 2.

**Why `bge-small-en-v1.5` (D-002):**

| Option | Why not (now) |
|---|---|
| OpenAI / Cohere embeddings | Paid; your data leaves the machine |
| `bge-base`, `bge-m3`, `nomic-embed-text`, `e5` | Bigger or different; maybe better. We **measure** them in Phase 3 instead of guessing |
| Old `all-MiniLM-L6-v2` | Fine model; BGE is generally stronger for retrieval at a similar size (we can measure it too) |

bge-small is small (fast on CPU), free, and strong for its size. It is a **starting point**,
revisited with numbers.

---

## 5. Cosine similarity

**Like I'm five:** two arrows on paper. If they point the same way, they "agree" (score 1).
At right angles, unrelated (score 0). Opposite ways, -1.

**What it really is:**

```text
cosine(a, b) = (a · b) / (|a| × |b|)
   a · b  = multiply matching numbers and add them up (dot product)
   |a|    = length of arrow a = square root of the sum of squares
```

**Normalisation trick:** if every vector is scaled to length 1 (`normalize_embeddings=True`),
then `|a| = |b| = 1` and cosine is just the dot product. Faster, and that is why vector
databases ask which "distance" you want.

**Why cosine and not plain distance:** cosine ignores length and looks at direction.
For these models, direction carries the meaning.

**Common mistake:** reading cosine scores as probabilities. A score of 0.6 is not "60%
relevant". Scores are only useful for **ranking** within one model. Different models have
different typical score ranges.

---

## 6. Keyword search vs meaning search (Lab 2)

**Like I'm five:**

- Keyword search is a librarian who only checks whether your exact words are on the page.
  Ask for "max_length" and they find it instantly. Ask "how do I check data is correct?"
  and they look blank, because the page says "validate".
- Meaning search is a librarian who understands what you mean but is fuzzy on exact names.
  They understand "check data is correct" means validation, but may confuse `max_length`
  with `min_length` because both "mean" similar things.

**What it really is:**

- **Keyword (lexical):** score by shared words. BM25 (Phase 3) is the grown-up version:
  rare words count more ("max_length" is rare, "the" is common), and long documents are
  not unfairly favoured.
- **Meaning (dense / semantic):** score by embedding similarity.

**The lesson that drives Phase 3:** each method fails where the other succeeds. So we will
use both and merge them (hybrid search). You discover this in your own Lab 2 output; that
discovery is a real interview story.

---

## 7. The BGE query prefix

BGE v1.5 models were trained with an instruction added to the **question** side when
searching (the exact text is on the model card; verify it). Documents get no prefix.
Why: the model learned that "question-shaped" text and "answer-shaped" text should meet in
the middle of the map. Forgetting the prefix usually lowers retrieval quality a little
without any error message. In Phase 7, removing it is our planned "deliberately bad change"
to prove the CI gate works.

---

## 8. Self-check (answer without looking)

1. Why is `.env` gitignored, and what do you do if a key was pushed?
2. What does a virtual environment protect you from?
3. Explain an embedding using the map analogy, then precisely.
4. Write the cosine formula. Why does normalising make it a dot product?
5. Give one question where keyword search wins and one where meaning search wins.
6. What happens to text longer than the model's token limit?
7. Why is a cosine score of 0.6 not "60% relevant"?
