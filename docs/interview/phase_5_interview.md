# Interview Questions, Phase 5: Tools, Multi-Agent, HITL, MCP

---

### Q1. "How does tool calling work? Who runs the tool?"

**Model answer:** "I describe each tool to the LLM: name, purpose, argument schema. The LLM
returns a tool call, a name plus JSON arguments. My code validates the arguments with
Pydantic, checks the tool is on the allowlist, runs it with a timeout, and gives the result
back to the LLM. The LLM never executes anything; all safety is in my code."

---

### Q2. "Your calculator tool: why not use `eval`?"

**Model answer:** "`eval` runs any Python, so an attacker or a confused model could run
`__import__('os').system(...)`. I parse the expression with `ast` and walk the tree,
allowing only numbers and arithmetic operators, with a cap on exponents so `9**9**9` cannot
freeze the server. Anything else raises an error."

---

### Q3. "How do you stop the SQL tool from damaging data?"

**Model answer:** "Defence in depth. The DuckDB connection is opened read-only, so writes fail
at the database level. On top, a SQL parser accepts only a single SELECT, I add a LIMIT and a
timeout, and the tool can only see the extracted-tables database. Two independent walls:
if one has a bug, the other still holds."

---

### Q4. "Describe your multi-agent design. Did it help?"

**Model answer:** "A supervisor with a structured output picks the next specialist:
researcher (the Phase 4 graph as a sub-graph), SQL analyst for table questions, code helper
that syntax-checks snippets, and a critic that compares the answer with its citations, with
a cap of 4 hand-offs. Compared with the single graph: [n/a]. I kept the supervisor only for
[types] because elsewhere it added [n/a] calls for no gain."

**Losing answer:** "More agents means better answers."

---

### Q5. "How does your human-in-the-loop work technically?"

**Model answer:** "When confidence is low, retrieval fails after max rewrites, or the topic is
high-risk, the graph reaches `human_review`, which calls `interrupt` with the draft,
citations, and confidence. A checkpointer (SQLite in dev, Postgres in production) has saved
state under a thread id. The API returns `pending_review` with that id. A reviewer calls
approve, edit, or reject; I resume the graph with the same thread id and the decision, and it
continues to output guards."

**Follow-up:** "What if the server restarts while waiting?" "State is in the database, not
memory. I demonstrated it: pause, kill the process, start a new one, resume, get the
answer. Also, the interrupted node re-runs from its start on resume, so code before
`interrupt` must have no side effects."

---

### Q6. "How do you decide when to involve a human? Isn't that just giving up?"

**Model answer:** "Triggers are confidence below a threshold, no relevant chunks after
retries, high-risk categories, and any side-effect tool. I measure the trigger rate
([n/a]) and how many flagged answers were actually wrong ([n/a]), so the triggers are tuned
rather than over-cautious. Approved and corrected answers become candidate golden items
after a human check, so the system improves from reviews."

---

### Q7. "What is MCP and why did you add it?"

**Model answer:** "Model Context Protocol, a standard way to expose tools to AI applications,
like USB for AI tools. My MCP server exposes `search_docs` and `get_doc_section`, read-only,
reusing the same retrieval pipeline as the API. Any MCP client can use DocPilot as a tool.
I kept it read-only because every exposed tool is attack surface."

---

### Q8. "How do you evaluate tool use?"

**Model answer:** "A hand-written routing set with expected route, tool, and arguments. I
measure routing accuracy, tool selection accuracy, argument validity, and tool-call
correctness, plus hand-offs per question. Results: [n/a]. Small free models were weak at
[n/a], and clearer tool descriptions / a stronger free router model improved it to [n/a]."

---

### Q9. "Why did you put tables in DuckDB instead of just embedding them?"

**Model answer:** "Vector search over flattened tables is weak at exact lookups and counting,
like 'which settings default to 30'. SQL answers those exactly. The SQL analyst finds the
table through a catalogue table with source and heading, writes one SELECT, and explains the
result with a citation to the table's source."

---

### Q10. Trap: "Why not let the code helper run the user's code to check it?"

**Model answer:** "Running untrusted code needs a real sandbox: separate container, no
network, CPU, memory, and time limits, and a read-only filesystem. That is a lot of risk for
a docs assistant. Syntax checking with `ast.parse` covers most of the value. If running code
became necessary, I'd add a sandboxed runner with its own threat model and decision entry."
