# Primer: the React chat app, and how ChatGPT-style features work (from zero)

Simple English. Written 2026-10-23 with everything built and tested (D-061).

---

## 1. The big picture

```text
Browser (React app)  --HTTP-->  FastAPI (/api/...)  -->  guards, memory, search, LLM
   web/src/                     src/docpilot/chat_api.py      src/docpilot/chat/
                                SQLite (data/app.db): chats, messages, files
                                Qdrant: main library + "docpilot_uploads" (with chat_id)
```

**Real-life example:** a restaurant. React is the dining room (what guests see), FastAPI is
the waiter (takes orders, brings food), the chat folder is the kitchen, SQLite is the order
book, Qdrant is the pantry.

## 2. React in 5 ideas

| Idea | Meaning | In DocPilot |
|---|---|---|
| **Component** | A function that returns a piece of screen | `Sidebar`, `Message`, `Composer` |
| **Props** | Inputs passed into a component | `<Message message={m} />` |
| **State** (`useState`) | Data that, when changed, redraws the screen | the message list, the file chips |
| **Effect** (`useEffect`) | Code that runs after drawing, when something changes | load a chat when you click it; poll files |
| **Ref** (`useRef`) | A box that keeps a value without redrawing | the Stop button's AbortController |

**Vite** is the tool that runs the app while developing (`npm run dev`, port 5173) and
packs it into plain files for production (`npm run build` -> `web/dist/`, served by FastAPI).

**Why React over Streamlit:** full control of the look (chat bubbles, file chips, streaming
cursor), and React is what real products use. **Cost:** a second language (JavaScript)
and a build step.

## 3. How "fast like ChatGPT" really works

ChatGPT and NotebookLM also index your files. They FEEL instant because of 3 tricks, and
we now use all 3:

| Trick | What we did | Real number (this laptop) |
|---|---|---|
| **Background work** | Upload returns at once with a "processing" chip; a worker thread indexes | 43-page PDF: upload answered in 0.10 s, ready after 18.9 s |
| **A fast reader** | pypdfium2 text instead of Docling's layout AI models, for uploads | 43 pages: 10.8 s vs 182 s (Docling) |
| **Streaming** | Words appear as the LLM writes them (Server-Sent Events) | 310 small pieces arrived one by one, not in one block |

**Trade-off of the fast reader:** tables come out as plain lines. The curated main library
still uses Docling, where table quality was measured.

## 4. Chats and memory

**Chats** are saved in **SQLite**: a database in one file, built into Python. Tables:
`chats` (title, time), `messages` (question, answer, sources, timings), `files` (name,
status, pages, chunks).

**Files per chat (like a NotebookLM notebook):** every uploaded chunk carries its chat's
id. Search uses a Qdrant **filter**: "only points with chat_id = this chat". Another chat
never sees your file.

**Memory, the "condense" step:**

| You type | Problem | What DocPilot does |
|---|---|---|
| "Which model sizes did they test it on?" | "they" and "it" mean nothing to search | One small LLM call rewrites it with the last 6 messages into a full question |
| "What was my first question?" | Not in any document | The rewriter says `CHAT`, so we answer from the conversation itself |
| First message of a chat | No history | No extra LLM call |

Real result: "What was my first question?" was answered with "What is chain-of-thought
prompting?" (status "chat"). The follow-up about model sizes found the right pages.

## 5. Streaming and the guardrails

The output guard needs the WHOLE answer (to check the citations), but streaming shows the
answer piece by piece. So: stream the draft, run the guard at the end, and if it fails,
the final "done" event replaces the text. This is the usual trade-off (ChatGPT also
removes some answers after showing them).

The input guard still runs FIRST, and runs again on the rewritten follow-up question.

## 6. Server-Sent Events (SSE) in one minute

The server keeps the HTTP response open and writes lines like:

```text
data: {"type": "token", "text": "Docker "}

data: {"type": "done", "answer": "...", "status": "ok", "sources": [...]}
```

The browser reads them as they arrive (`response.body.getReader()` in `web/src/api.js`).
**Why not WebSockets:** we only need server -> browser, and SSE is plain HTTP.

## 7. Self-check

1. Why does an upload return in 0.1 s when indexing takes 19 s?
2. How does a chat search only its own files?
3. Why does the first message of a chat not need the "condense" LLM call?
4. Why does the output guard run after streaming, and what happens if it fails?
5. Why does the UI never import any RAG code?
