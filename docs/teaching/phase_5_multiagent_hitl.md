# Teaching Notes, Phase 5: Tools, Multi-Agent, Human-in-the-Loop, MCP

Plan file: `docs/implementation_plan/phase_5_multiagent_hitl.md`

---

## 1. Tools and function calling

**Like I'm five:** an LLM is a very well-read person locked in a room. It cannot use a
calculator or look at a database. A **tool** is a slot in the door: the person writes a
request on a note ("calculate 240 × 0.15"), **your code** does the work, and slides the
result back.

**What it really is:**
1. You describe each tool to the LLM: name, purpose, argument schema (JSON).
2. The LLM replies with a **tool call**: `{"tool": "calculator", "args": {"expression": "240*0.15"}}`.
3. **Your code** validates the arguments, runs the function, returns the result.
4. The LLM uses the result in its answer.

**The LLM never runs anything itself.** That is why the safety of tools is entirely your
code's job. Many providers support native tool calling (VERIFY per provider); where they
do not, we ask for JSON and validate it (Phase 4 structured output).

**Why strict schemas:** a Pydantic model per tool rejects bad arguments before anything
runs. Free small models often produce wrong argument names or types; the schema catches it.

---

## 2. Safe tools: the classic traps

| Tool | Trap | Our defence |
|---|---|---|
| Calculator | `eval(expression)` runs **any** Python, e.g. deleting files | Walk the syntax tree (`ast`) and allow only numbers and arithmetic; cap exponents |
| SQL | LLM writes `DROP TABLE` (or is tricked into it) | Read-only connection + single `SELECT` only + row limit + timeout (Phase 6 adds a parser) |
| Web search | Results may contain injected instructions | Off by default; results marked untrusted (Phase 6) |
| Doc section | Path tricks like `../../.env` | Only names in the indexed allowlist |

**Defence in depth:** two independent walls (string checks **and** a read-only database).
If one wall has a hole, the other still holds.

---

## 3. Tables as a database

Some questions are about tables ("which options does this table list?", "which setting has
default 30?"). Vector search over a table flattened into text is weak at exact lookups and
counting. So we load each Markdown table into DuckDB and let a specialist write SQL.

**Why DuckDB (or SQLite):** both are embedded databases (a file, no server). DuckDB is
built for analytical queries and has a read-only mode. SQLite is everywhere and also fine.
Choose, and record the reason.

---

## 4. Multi-agent: supervisor and specialists

**Like I'm five:** a hospital front desk (supervisor) sends you to the right specialist:
the researcher for "how does X work", the data analyst for table questions, the code
checker for "is this snippet valid?". A senior doctor (critic) reviews the final report.

**What it really is:** the supervisor is an LLM call with a structured output
`{"next": "researcher" | "sql_analyst" | "code_helper" | "finish"}`. Each specialist is a
node or a sub-graph with its own prompt and tools.

**Why it might help:** each specialist has a short, focused prompt and only the tools it
needs, so small models make fewer mistakes than one giant prompt with every tool.

**Why it might not help:** more LLM calls, more latency, more places to go wrong (the
supervisor can route badly). **"More agents" is not automatically better.** We compare C9
(single graph) vs C10 (supervisor) and keep the supervisor only where it wins.

**Code helper safety:** it only **checks syntax** with `ast.parse`. Running user code needs
a proper sandbox (separate container, no network, time and memory limits); we do not do
that unless the risk is justified and written in the decision log.

---

## 5. Human-in-the-loop (HITL)

**Like I'm five:** a junior employee drafts a reply to an important customer, puts it in
the manager's tray, and goes home. The manager reads it next morning, approves or fixes it,
and the reply goes out. Nothing was lost overnight because the draft was **on paper**, not
in the junior's head.

**What it really is in LangGraph:**

1. **Checkpointer:** after every node, the full state is saved to a database (SQLite in
   dev, Postgres in production). That is the "paper".
2. **Thread id:** each conversation/run has an id. Saved state is stored under it.
3. **`interrupt(payload)`:** inside `human_review`, execution stops and the payload (draft,
   citations, confidence) is returned to the caller. The run is now paused, saved.
4. **Resume:** later (seconds or days, even after a server restart), call the graph again
   with the same thread id and `Command(resume=decision)`. LangGraph loads the state and
   continues; `interrupt(...)` now returns the reviewer's decision.

(VERIFY exact API names in current LangGraph docs.)

**Important detail:** when resumed, the interrupted node **runs again from its start**, and
`interrupt` returns the decision this time. So code **before** `interrupt` in that node
must be safe to run twice (no side effects like sending emails before the pause).

**When to ask a human (triggers):** low confidence from the groundedness check; nothing
relevant after max rewrites; high-risk topics (deleting data, production changes,
credentials); any tool with side effects.

**Why a persistent checkpointer and not memory:** in-memory state dies with the process.
A deploy or crash would lose every pending review. The restart demo proves we handled it.

**Trigger rate matters:** if 60% of questions go to a human, the system is useless. Measure
the rate, and check how many flagged answers were actually wrong (are the triggers smart?).

**The flywheel:** answers a human approved or corrected become candidate golden items.
After a human check they join the dev set, so the evals grow from real usage.

---

## 6. MCP (Model Context Protocol)

**Like I'm five:** USB for AI tools. Before USB, every device needed its own special port.
MCP is a standard plug: write your tool once as an MCP server, and any MCP-compatible AI
app (desktop assistants, IDEs, agents) can use it.

**What it really is:** a protocol (JSON-RPC messages) where a **server** lists tools (name,
description, input schema) and a **client** (the AI app) calls them. Transport can be
stdio (local process) or HTTP.

**Our server exposes:** `search_docs` and `get_doc_section`, both read-only, both reusing
`retrieval/pipeline.py`. No duplicated logic, nothing with side effects.

**Why add it:** it makes DocPilot reusable outside its own API, and MCP is a skill many AI
job descriptions now mention. **Why not more tools over MCP:** every exposed tool is attack
surface. Read-only and minimal first.

---

## 7. Evaluating agents

Final-answer metrics are not enough: an agent can get the right answer by luck after wrong
steps. So we also measure:

| Metric | Catches |
|---|---|
| Routing accuracy | Supervisor sends table questions to the researcher |
| Tool selection accuracy | Wrong tool chosen |
| Argument validity | Malformed arguments |
| Tool-call correctness | Right tool, wrong numbers |
| Hand-offs per question | Wasted supervisor loops |
| HITL trigger rate | Over-cautious (or under-cautious) system |

`routing.jsonl` holds the expected route, tool, and arguments per question. Write these by
hand, like the golden set.

---

## 8. Self-check

1. Explain tool calling; who actually executes the tool?
2. Why is `eval()` dangerous, and how does the AST calculator avoid it?
3. What is defence in depth? Give the SQL example.
4. When can multi-agent hurt? What did your C9 vs C10 comparison show?
5. Explain checkpointer, thread id, interrupt, and resume. What happens after a restart?
6. Why must code before `interrupt` be safe to run twice?
7. What is MCP and why only read-only tools?
8. Name three agent metrics beyond answer quality.
