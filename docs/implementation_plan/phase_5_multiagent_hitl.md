# Phase 5: Multi-Agent, Tools, MCP, Human-in-the-Loop (Implementation Plan)

**Goal of the phase:** give DocPilot tools, a team of specialists with a supervisor, a
standard MCP interface, and a human reviewer whose pause survives a server restart.
Keep multi-agent only if the evals say it beats the single graph.

**Teaching companion:** `docs/teaching/phase_5_multiagent_hitl.md`

**Ablation row:** C10 (+ multi-agent / tools), plus a separate agent-eval table (routing
accuracy, tool-call correctness).

Order matters: tools first (small, testable), then specialists that use them, then the
supervisor, then HITL, then MCP, then evals.

---

## Step 5.1: Tools with strict schemas

**Folder:** `src/docpilot/tools/`. Each tool = a Pydantic input model + a plain function +
a timeout. `tools/registry.py` holds the allowlist: only tools in this dict can be called.

### 5.1.1 `tools/calculator.py` (safe, no `eval`)

```python
"""Evaluate arithmetic safely by walking the syntax tree. Never uses eval()."""
import ast
import operator

from pydantic import BaseModel, Field

ALLOWED_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg,
}


class CalculatorInput(BaseModel):
    expression: str = Field(max_length=200)


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_OPERATORS:
        if isinstance(node.op, ast.Pow) and abs(_evaluate(node.right)) > 100:
            raise ValueError("exponent too large")      # stops 9**9**9 freezing the server
        return ALLOWED_OPERATORS[type(node.op)](_evaluate(node.left), _evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_OPERATORS:
        return ALLOWED_OPERATORS[type(node.op)](_evaluate(node.operand))
    raise ValueError(f"not allowed: {type(node).__name__}")   # names, calls, imports...


def calculate(tool_input: CalculatorInput) -> float:
    tree = ast.parse(tool_input.expression, mode="eval")
    return _evaluate(tree.body)
```

Why not `eval()`: `eval("__import__('os').system('...')")` runs any command. This is the
classic interview trap.

### 5.1.2 Other tools

| File | Input model | Key safety rule |
|---|---|---|
| `tools/sql_tool.py` | `SqlInput(sql: str)` | DuckDB opened `read_only=True`; one statement only; must start with `SELECT`; `LIMIT` added if missing; timeout. (Phase 6 adds a real SQL parser check.) |
| `tools/doc_section.py` | `DocSectionInput(doc: str, heading: str)` | `doc` must be in the list of indexed sources |
| `tools/web_search.py` | `WebSearchInput(query: str)` | **Off by default** (setting). Free DuckDuckGo-based library, VERIFY reliability and terms. Results marked untrusted |

**Tests:** `tests/test_tools.py`: calculator rejects names and calls; SQL tool rejects
`DROP`, `INSERT`, two statements; doc_section rejects an unknown doc.

---

## Step 5.2: Extract tables into DuckDB

**File:** `src/docpilot/ingestion/tables.py`

- Every `table` block from `blocks.py` becomes a DuckDB table `t_<n>`.
- A catalogue table `table_catalog(table_name, source, heading_path, columns)` lets the SQL
  analyst find the right table.
- File: `data/processed/tables.duckdb` (gitignored).
- Decision entry: DuckDB vs SQLite. DuckDB reads tabular data well and has a read-only
  mode; SQLite is everywhere and also fine. Record the actual reason you chose.

---

## Step 5.3: Specialists and the supervisor

**Folder:** `src/docpilot/agents/specialists/`

| File | Job | Uses |
|---|---|---|
| `researcher.py` | The Phase 4 graph, wrapped as a sub-graph | retrieval pipeline |
| `sql_analyst.py` | Reads `table_catalog`, writes one SQL query, runs it, explains the result | `sql_tool` |
| `code_helper.py` | Checks Python snippets with `ast.parse` (syntax only). Never runs user code | `ast` |
| `critic.py` | Compares final answer to its citations; flags unsupported claims | LLM judge prompt |

**File:** `src/docpilot/agents/supervisor.py`

- The supervisor reads the question and returns a structured decision:
  `{"next": "researcher" | "sql_analyst" | "code_helper" | "finish"}` (Pydantic-validated).
- Cap: max 4 specialist hand-offs per question.
- The router from Phase 4 gains the `tool` route for calculator / doc_section.

**Comparison:** run the dev set through single graph (C9) and supervisor graph (C10).
Same metrics as 4.6. Keep the supervisor only for question types where it wins.

---

## Step 5.4: Human-in-the-loop with a persistent checkpointer

**File:** `src/docpilot/agents/human_review.py`

```python
# VERIFY: interrupt / Command / checkpointer APIs in current LangGraph docs
from langgraph.types import interrupt


def human_review(state: AgentState) -> dict:
    """Pause the graph and wait for a reviewer. The state is saved by the checkpointer."""
    decision = interrupt({                       # execution stops here until resumed
        "question": state["question"],
        "draft_answer": state["draft_answer"],
        "citations": state["citations"],
        "confidence": state["confidence"],
    })
    # When resumed, `decision` is what the reviewer sent, e.g. {"action": "edit", "text": "..."}
    if decision["action"] == "approve":
        return {"status": "answered"}
    if decision["action"] == "edit":
        return {"draft_answer": decision["text"], "status": "answered"}
    return {"draft_answer": config.NOT_FOUND_PHRASE, "status": "rejected",
            "trace": state["trace"] + [f"rejected: {decision.get('reason', '')}"]}
```

Wiring:

1. `needs_review(state)` edge function: confidence below threshold, or high-risk keywords
   (delete, drop, production, credential, password), or grader gave up after max rewrites.
2. Compile with a **SQLite checkpointer** in dev (`data/processed/checkpoints.sqlite`,
   VERIFY package name, e.g. `langgraph-checkpoint-sqlite`). Postgres arrives in Phase 7.
3. Every run gets a `thread_id` (UUID). Resume = invoke again with the same `thread_id` and
   `Command(resume=decision)`.

**Demo script:** `scripts/06_hitl_restart_demo.py`
1. Ask a question that triggers review; print `thread_id`; process exits.
2. Start a **new** process; load pending threads; resume with "approve"; print the answer.

If step 2 works, the pause survived a restart. That is the gate requirement.

---

## Step 5.5: Reviewer endpoints

**File:** `src/docpilot/api/routes_review.py` (the Phase 1 `api.py` becomes the `api/`
package here: `app.py`, `schemas.py`, `routes_ask.py`, `routes_review.py`)

| Endpoint | Does |
|---|---|
| `GET /reviews/pending` | Lists rows from `review_queue` with status `pending` |
| `POST /reviews/{thread_id}/approve` | Resume with approve |
| `POST /reviews/{thread_id}/edit` | Body `{text}`; resume with edit |
| `POST /reviews/{thread_id}/reject` | Body `{reason}`; resume with reject |
| `GET /answers/{thread_id}` | Final answer once resumed |

`review_queue` table (SQLite now, Postgres later): `thread_id, question, draft, confidence,
status, reviewer_action, created_at, decided_at`.

**Flywheel:** approved or edited pairs are appended to `evals/golden/candidates.jsonl`.
A human checks each one before moving it into `dev.jsonl` (never automatic).

---

## Step 5.6: MCP server

**File:** `src/docpilot/mcp_server/server.py`

- Official MCP Python SDK (VERIFY package name and current server API).
- Two tools: `search_docs(query: str, technology: str | None)` calls
  `retrieval.pipeline.retrieve`; `get_doc_section(doc: str, heading: str)` calls the tool
  from 5.1. No logic is duplicated.
- Test with the MCP Inspector (VERIFY) or by adding it to an MCP client's config.
- Read-only tools only. Nothing with side effects is exposed.

---

## Step 5.7: Agent evals

**File:** `evals/golden/routing.jsonl`

```json
{"id": "r-001", "question": "What is 15% of 240?", "expected_route": "tool", "expected_tool": "calculator", "expected_args": {"expression": "240 * 0.15"}}
```

**File:** `evals/run_agent_eval.py` reports:

| Metric | Meaning |
|---|---|
| Routing accuracy | chosen route == expected route |
| Tool selection accuracy | right tool picked |
| Argument validity | arguments passed Pydantic validation |
| Tool-call correctness | tool result equals expected result |
| HITL trigger rate | share of questions sent to a human (too high = useless system) |
| Mean hand-offs per question | supervisor cost |

Free small models are often weak at tool calling. If correctness is low, try (1) clearer
tool descriptions, (2) the structured-output retry, (3) a stronger free model just for the
router. Record each attempt as its own row.

---

## Phase 5 gate

- [ ] tool tests pass (safety cases included)
- [ ] C10 row + agent-eval table; written decision single vs multi-agent per type
- [ ] HITL restart demo works and is recorded (script output saved in the progress log)
- [ ] reviewer endpoints tested
- [ ] MCP server called from a real MCP client
- [ ] versions pinned (duckdb, checkpoint package, mcp SDK, search library), verified dates
- [ ] agent-eval runs logged in MLflow (`docpilot-agents`)
- [ ] interview notes; merged via PR (CI green); tag `phase-5` pushed
