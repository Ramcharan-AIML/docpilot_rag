# DocPilot: The Interview Story

Written 2026-10-23. Everything here is true and measured; say numbers exactly as written.
Practise Section 1 aloud until it takes about 5 minutes. Section 2 is the 60-second version.

---

## Numbers card (memorise)

| What | Number |
|---|---|
| Corpus | 20 documents (FastAPI, Pydantic, Docker, Chain-of-Thought paper, 3 Wikipedia articles, my notes), 453 chunks |
| Golden set | 65 questions with evidence; dev / test / CI splits |
| Retrieval (dev, 41 questions) | Recall@5 **0.78 -> 0.88**, MRR **0.65 -> 0.73** |
| Unseen test split (17 questions) | top-1 **0.35 -> 0.65**, MRR **0.61 -> 0.77** |
| Reranker choice | MiniLM (91 MB) beat bge-reranker-base (1.1 GB), **13x faster** (0.49 s vs 6.4 s) |
| Query transforms | 4 tried, **0 gain**, +0.9 to 2.7 s each: none kept |
| Answer quality (LLM judge, 10 answers) | faithfulness **1.0**, **0** made-up claims, 5/5 correct refusals |
| Guardrails | attacks that worked **2/18 -> 0/18**, false blocks **0/84**, about 0.05 ms added |
| CI eval gate | caught an injected bug: MRR **0.87 -> 0.50**, build failed |
| Latency (p50) | search 12 ms, rerank 0.49 s, LLM 0.99 s |
| Uploads | 43-page PDF: answer to the upload in **0.10 s**, ready in **18.9 s**; reader 10.8 s vs 182 s |
| Tests | 305 automated tests |

---

## 1. The 5-minute story (speak it)

**(0:00) The problem.**
"I built DocPilot, a question-answering assistant for technical documentation. You ask a
question; it finds the right paragraphs and answers with citations like [1] and [2]. If
the answer is not in the documents, it says so instead of guessing. I built it as an
evaluation-driven RAG system: every design choice had to beat the previous one on a test
set before I kept it. It runs entirely on free tools: local models on a CPU laptop and
Groq's free LLM tier."

**(0:40) The foundation: measure first.**
"Before optimising anything, I built the measuring tape. I wrote a golden set of 65
questions, each with the exact evidence sentence, split into dev, test and CI sets, and
some questions deliberately unanswerable. I wrote the metrics by hand: Recall@k, MRR,
nDCG, abstention accuracy and per-stage latency. Every run is saved with its git commit
and logged in MLflow, and a GitHub Actions eval gate fails any pull request where
retrieval gets worse. I proved the gate works: an injected chunking bug dropped MRR from
0.87 to 0.50 and the build went red."

**(1:30) Ingestion and chunking.**
"The corpus has 20 documents in different shapes: Markdown docs, a PDF research paper and
Word notes. I used Docling for PDFs because it keeps tables as tables, a cleaner for HTML
noise, and a resolver that puts the real code examples into the FastAPI pages. Then I
compared 11 chunking strategies, from fixed sizes to semantic and hierarchical chunks.
The simplest won: 200-token chunks with 25 tokens of overlap. That raised Recall@5 from
0.78 to 0.81 and MRR from 0.65 to 0.70."

**(2:10) Retrieval.**
"For search I embed with BGE-small, a 384-dimension sentence-transformer, and store in
Qdrant. I added BM25 keyword vectors: alone they scored the same as dense search, but on
different questions, so I combined them with Reciprocal Rank Fusion. I wrote RRF by hand
first, then moved it into one Qdrant call and checked the scores matched. On top, a
cross-encoder reranker re-reads the top 20 and keeps 4. I compared two rerankers: the
small MiniLM was both better and 13 times faster than the 1.1 GB model, so I kept the
small one. I also tried four query transforms, including HyDE and multi-query. None
improved recall, and each added up to 2.7 seconds, so I left them out. On the held-out
test set, top-1 accuracy went from 0.35 to 0.65."

**(3:10) Answers and safety.**
"The LLM is GPT-OSS-120B on Groq, with a strict 'cite or refuse' prompt. A second model,
Qwen, from a different family, judges the answers claim by claim: faithfulness was 1.0
with zero made-up claims on 10 answers, and all 5 out-of-scope questions were refused.
Then I added guardrails in plain Python: an input guard for prompt injection with Unicode
normalisation, a context guard that puts every chunk in a document box so text inside a
document is treated as data, and an output guard that checks citations and a canary token.
I red-teamed it with 18 attacks: without guards, 2 worked, including a poisoned document
that sent users to a fake website. With guards, 0 of 18, with 0 of 84 real questions
wrongly blocked."

**(4:10) The product.**
"Finally I built a React chat app on FastAPI, like a small NotebookLM: saved chats in
SQLite, files per chat filtered in Qdrant by chat id, answers streamed word by word with
Server-Sent Events, and memory: follow-up questions are rewritten with the last six
messages, so 'what about the second one?' works. Uploads index in the background; I
switched uploads from Docling to a fast text reader, so a 43-page PDF is ready in about 19
seconds instead of over three minutes."

**(4:40) What I learned.**
"The biggest lesson: measure, don't assume. Several 'smart' ideas, like a bigger reranker
and query rewriting, lost to simpler ones on real numbers. Next I am adding Docker and
Prometheus with Grafana to watch latency under load, and later agents and cloud
deployment."

---

## 2. The 60-second version

"DocPilot is an evaluation-driven RAG assistant over technical documentation, built with
free tools on a CPU laptop. I built a 65-question golden set and hand-written retrieval
metrics first, plus a CI gate that fails pull requests when retrieval drops. Then I improved
step by step: 200-token chunks out of 11 strategies, hybrid BM25 plus dense search with
Reciprocal Rank Fusion in Qdrant, and a MiniLM cross-encoder reranker that beat a 13x
slower model. Recall@5 went from 0.78 to 0.88; on unseen test questions top-1 accuracy
nearly doubled, 0.35 to 0.65. An LLM judge measured faithfulness 1.0. I added plain-Python
guardrails, red-teamed with 18 attacks, and went from 2 successful attacks to 0 with no
false blocks. The front end is a React chat with streaming answers, memory and per-chat
file uploads."

---

## 3. Every model and library, and its job

| Model / library | Job in DocPilot | One-line reason |
|---|---|---|
| `BAAI/bge-small-en-v1.5` (sentence-transformers) | Dense embeddings, 384 dims | Fast on CPU, strong retrieval; query prefix added by hand |
| BM25 (`Qdrant/bm25`, FastEmbed) | Sparse keyword vectors | Exact words: error codes, flags, function names |
| Qdrant v1.19.1 | Vector DB: dense + sparse + RRF + filters | Hybrid search in one call; chat filter for uploads |
| `cross-encoder/ms-marco-MiniLM-L6-v2` | Reranker, top 20 -> 4 | Better and 13x faster than bge-reranker-base |
| `openai/gpt-oss-120b` (Groq) | Writes answers; rewrites follow-ups | Free tier, about 1 s, follows "cite or refuse" |
| `qwen/qwen3.8-27b` (Groq) | Judge in the generation eval | Different family: no self-grading bias |
| Docling | PDF/DOCX -> Markdown for the main library | Keeps tables |
| pypdfium2 | Fast text reader for uploads | 10.8 s vs 182 s on 43 pages |
| FastAPI, Pydantic, uvicorn | API, validation, server | Typed, fast, automatic docs |
| SQLite | Chats, messages, file status | Built into Python, zero setup |
| React 19, Vite, react-markdown | Chat UI | Streaming text, citations, file chips |
| MLflow | Experiment tracking | Every run tied to a commit |
| SeaweedFS + boto3 | S3-compatible storage for backups | Same code as Amazon S3 |
| GitHub Actions, GitGuardian | CI: tests, lint, eval gate, secret scan | Quality on every pull request |

---

## 4. Challenges and how I fixed them (short S-P-F-L stories)

Pick 2 or 3 in an interview. Situation, Problem, Fix, Lesson.

| # | Challenge | Fix | Lesson |
|---|---|---|---|
| 1 | **The "fresh" index was not fresh.** Deleting and re-creating a Qdrant collection in local mode loaded the old points back (`assert 3 == 0`) | After creating, delete every point with an empty filter, then assert the count is 0 | Test the infrastructure layer, not only your logic |
| 2 | **Silent embedding bug.** A library helper looked like it added BGE's query prefix, but the model's stored prompt was empty, so it added nothing | Inspected `model.prompts`, added the prefix by hand, pinned the model revision | Silent bugs are the dangerous ones: nothing crashes |
| 3 | **Numbers differed across machines.** Windows sorts paths ignoring case; `\n` became `\r\n`; docs downloaded from `master` kept changing | Sort by path string, write bytes, pin the corpus to one commit | Reproducibility is designed, not hoped for |
| 4 | **The LLM provider did not match its docs.** The documented model returned 404; the reasoning model sometimes returned an empty answer silently | Chose models from the live `/models` list; empty answers now raise an error | Verify against the live API; fail loudly |
| 5 | **Qdrant was 2 seconds slow.** `localhost` on Windows tried IPv6 first | Use `127.0.0.1`: search 2,062 ms -> 7.6 ms | Measure every stage, not just the total |
| 6 | **Qdrant's RRF was not my RRF.** Its default k is 2 and its formula is 1/(k + rank - 1) | Send k+1 = 61; checked the scores match my hand-written version | Understand the library by building it raw first |
| 7 | **Bigger was not better.** The 1.1 GB reranker lost to the 91 MB one and was 13x slower | Kept MiniLM | Pick by measurement, not by model size |
| 8 | **Clever ideas gave nothing.** 4 query transforms: 0 recall gain, up to +2.7 s | None kept; the misses were about tables, not wording | A negative result is still a result |
| 9 | **My first guard blocked a real question:** "What is the system prompt in an LLM app?" | Narrowed the patterns; re-checked all 84 golden questions: 0 blocked | Always report false blocks next to attack success |
| 10 | **The LLM cites in 3 styles:** `[2]`, `【1】`, `【1†L1-L4】` | Found it in cached answers before writing the citation check | Look at real outputs before writing validators |
| 11 | **The eval cache would lie.** Answers were cached by question only, so a new prompt would reuse old answers | A separate cache file per prompt version | A cache key must include everything that changes the result |
| 12 | **Uploads felt slow.** Docling took 182 s for 43 pages | Fast reader (10.8 s) plus background indexing; the upload answers in 0.10 s | Speed is also about what the user waits for |
| 13 | **No memory.** "What was my question?" said "not found" | Condense step with the last 6 messages; questions about the chat answered from history | Conversational RAG needs a query-rewrite step |

---

## 5. Likely follow-up questions (short answers)

**"Why hybrid search?"** "BM25 and dense search scored the same Recall@5, 0.805, but missed
different questions. Fusing them with RRF gave 0.829, and the reranker took it to 0.878."

**"Why RRF and not adding scores?"** "Dense scores are cosine similarities, BM25 scores are
unbounded; adding them mixes scales. RRF uses only the rank positions."

**"Why a reranker on top of hybrid search?"** "Search embeds the question and each chunk
separately, which is fast but rough. A cross-encoder reads both together, which is more
accurate but slow, so it only sees the top 20."

**"How do you know the answers are not hallucinated?"** "Three ways: the prompt forces cite
or refuse; the output guard rejects answers with no valid citation; and an LLM judge from a
different model family checked claims: faithfulness 1.0 on 10 answers, with human spot
checks."

**"How does memory work?"** "The server keeps the chat in SQLite. For a follow-up, one small
LLM call rewrites it into a standalone question using the last six messages; the answer
prompt never contains the history, so it stays small. Questions about the chat itself are
answered from the history."

**"How do uploads stay private to a chat?"** "Each uploaded chunk carries the chat's id in
its Qdrant payload, and search in that chat filters on it. Deleting the chat deletes its
vectors, rows and files."

**"What would you do with more time?"** "Prometheus and Grafana for live latency, a load
test, Docker deployment, then agents with LangGraph, and a library guardrail comparison
on the same 18 attacks."

**"Is it safe?"** "Safer against the 18 attacks I tested, by a measured amount. No system is
fully safe against prompt injection. The model has no tools or secrets it can reach, so the
worst case is a wrong text answer, not an action."

**"What went wrong?"** Pick challenge 2, 9 or 12 from Section 4.

---

## 6. Be honest about these

- Agents, multi-agent and AWS deployment are **planned, not built** (deadline cut).
- Sample sizes are small (41 dev questions, 17 test, 18 attacks). Say "on my test set".
- End-to-end latency under load is not measured yet (next: Prometheus).
- Uploads use a fast reader that flattens tables; the main library uses Docling.
