# Phase 4: Agentic RAG with LangGraph (Implementation Plan)

**Goal of the phase:** let an LLM manage the steps (decide, check, retry) and prove with
numbers where that helps and where it only costs time and LLM calls.

**Teaching companion:** `docs/teaching/phase_4_agents.md` (includes the LangGraph primer)

**Ablation row:** C9 (+ agentic loop). Compared against C8 (best non-agentic pipeline).

```text
Phase 4 graph (single agent)

START ─▶ router ─┬─▶ direct ───────────────────────────────┐
                 └─▶ retrieve ─▶ grade ─┬─(none relevant, rewrites < 2)─▶ rewrite ─▶ retrieve
                                        └─(some relevant)─▶ generate ◀─┘
                                                              │
                              check_groundedness ─(low, regen < 1)─▶ generate
                                                              │
                                                             END
(guard_input / guard_output are added in Phase 6; human_review in Phase 5)
```

New dependencies (decision log + VERIFY current APIs first): `langgraph`; RAGAS and/or
DeepEval in step 4.5. We do **not** add LangChain unless a step needs it.

---

## Step 4.1: Hand-made agent loop (no framework)

**Goal:** understand the idea of an agent before any library hides it.

**File:** `src/docpilot/agents/manual_loop.py`

```python
"""A plain-Python agentic RAG loop. Teaching version: LangGraph replaces it in 4.4."""
from docpilot import config
from docpilot.agents import prompts
from docpilot.retrieval.pipeline import retrieve

MAX_REWRITES = 2
MAX_REGENERATIONS = 1


def answer_with_loop(question: str, llm) -> dict:
    trace: list[str] = []            # human-readable record of every decision
    search_query = question
    relevant: list[dict] = []

    for attempt in range(MAX_REWRITES + 1):          # 1 normal try + up to 2 rewrites
        hits = retrieve(search_query)
        relevant = [hit for hit in hits if prompts.grade_chunk(llm, question, hit)]
        trace.append(f"try {attempt}: query={search_query!r}, relevant={len(relevant)}")
        if relevant:
            break
        if attempt < MAX_REWRITES:
            search_query = prompts.rewrite_query(llm, question, search_query)

    if not relevant:                                  # gave up: abstain, do not guess
        return {"answer": config.NOT_FOUND_PHRASE, "status": "not_found", "trace": trace}

    answer = prompts.generate_answer(llm, question, relevant)
    for _ in range(MAX_REGENERATIONS):
        if prompts.is_grounded(llm, answer, relevant):
            break
        trace.append("answer not grounded: regenerating")
        answer = prompts.generate_answer(llm, question, relevant, strict=True)

    return {"answer": answer, "status": "answered", "sources": relevant, "trace": trace}
```

**Run:** on 5 golden questions; print `trace` and read it. Find one question where the
rewrite helped and one where it wasted calls.

Note: one grading call per chunk is expensive. In 4.3 we grade all chunks in **one** call.

---

## Step 4.2: LangGraph primer (toy graph)

**File:** `labs/lab4_langgraph_toy.py`: a two-node graph on a counter, with one
conditional edge, so you see state, nodes, edges, and `END` with nothing else in the way.

```python
# VERIFY: imports and method names in the current LangGraph docs before running
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class CounterState(TypedDict):
    count: int


def add_one(state: CounterState) -> dict:
    return {"count": state["count"] + 1}   # a node returns only the fields it changes


def should_continue(state: CounterState) -> str:
    return "again" if state["count"] < 3 else "stop"


builder = StateGraph(CounterState)
builder.add_node("add_one", add_one)
builder.add_edge(START, "add_one")
builder.add_conditional_edges("add_one", should_continue, {"again": "add_one", "stop": END})
graph = builder.compile()
print(graph.invoke({"count": 0}))          # expect {'count': 3}
```

Exercises: remove the stop condition and see the recursion limit error (that is LangGraph's
built-in loop guard); print the graph as Mermaid text (VERIFY method name).

---

## Step 4.3: State, prompts, nodes

**Files**

| File | Contents |
|---|---|
| `agents/state.py` | `AgentState` TypedDict (architecture section 9.1) |
| `agents/prompts.py` | Every prompt as a constant with a version string, e.g. `GRADE_PROMPT_V1` |
| `llm/structured.py` | `ask_json(llm, prompt, schema)`: ask for JSON, validate with Pydantic, on failure retry **once** with the validation error included; then give up safely |
| `llm/budget.py` | `LLMBudget(max_calls)`: counts calls per question; raises `BudgetExceeded` |
| `agents/nodes_retrieval.py` | `router`, `retrieve_node`, `grade_documents`, `rewrite_query` |
| `agents/nodes_generation.py` | `generate`, `check_groundedness` |

Structured output example:

```python
class Grades(BaseModel):
    # one entry per chunk, same order as given
    relevant: list[bool]


def grade_documents(state: AgentState) -> dict:
    """One LLM call grades all chunks together (cheaper than one call per chunk)."""
    result = ask_json(LLM, prompts.GRADE_PROMPT_V1.format(...), Grades)
    if result is None or len(result.relevant) != len(state["retrieved"]):
        grades = [True] * len(state["retrieved"])   # fail open: keep chunks, log it
    else:
        grades = result.relevant
    return {"grades": grades, "llm_calls": state["llm_calls"] + 1,
            "trace": state["trace"] + [f"grade: {sum(grades)}/{len(grades)} relevant"]}
```

Why "fail open" for grading but "fail closed" (abstain) for groundedness: a broken grader
should not throw away good chunks; a broken groundedness check should not let an unchecked
answer through with high confidence. Write this trade-off in `decisions.md`.

**Router** v1 has two routes, `retrieve` and `direct` (greetings, "what can you do?").
Tool routes arrive in Phase 5.

---

## Step 4.4: Build the graph

**File:** `src/docpilot/agents/graph.py`

```python
# VERIFY all LangGraph names on build day
def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("router", router)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("grade_documents", grade_documents)
    builder.add_node("rewrite_query", rewrite_query)
    builder.add_node("generate", generate)
    builder.add_node("check_groundedness", check_groundedness)

    builder.add_edge(START, "router")
    builder.add_conditional_edges("router", pick_route,
                                  {"retrieve": "retrieve", "direct": "generate"})
    builder.add_edge("retrieve", "grade_documents")
    builder.add_conditional_edges("grade_documents", after_grading,
                                  {"rewrite": "rewrite_query", "generate": "generate",
                                   "give_up": END})
    builder.add_edge("rewrite_query", "retrieve")
    builder.add_edge("generate", "check_groundedness")
    builder.add_conditional_edges("check_groundedness", after_check,
                                  {"regenerate": "generate", "done": END})
    return builder.compile()
```

Edge functions (`after_grading`, `after_check`) are plain functions with the caps inside:

```python
def after_grading(state: AgentState) -> str:
    if any(state["grades"]):
        return "generate"
    if state["rewrite_count"] < MAX_REWRITES and state["llm_calls"] < MAX_LLM_CALLS:
        return "rewrite"
    return "give_up"    # sets status not_found via a small finalise step
```

**Tests:** `tests/test_graph_routing.py` with a **fake LLM** that returns scripted answers:
1. relevant on first try -> 0 rewrites
2. irrelevant twice then relevant -> 2 rewrites
3. always irrelevant -> stops after 2 rewrites with `not_found`
4. budget of 3 calls -> stops early

These tests prove the caps work without spending a single real LLM call.

Export the graph picture to `docs/architecture/graph.md` (Mermaid) so the README can show it.

---

## Step 4.5: RAGAS and/or DeepEval

**Goal:** compare our hand-written judge (3.9) with a library.

1. VERIFY current metric names and how to use a **non-OpenAI** judge (free provider)
   in each library. Pin versions.
2. `evals/run_ragas_eval.py` (or `run_deepeval_eval.py`): same items, same answers as our
   harness.
3. Report: library scores, our scores, and how often they agree. If they disagree a lot,
   spot-check those items by hand and note who was right.
4. Decision: keep our harness, the library, or both. Record why.

---

## Step 4.6: Agentic vs non-agentic comparison

**File:** `evals/run_agent_comparison.py`

Run the dev set through (a) C8 plain pipeline + one generate call and (b) the C9 graph.

| Report column | Why |
|---|---|
| Faithfulness, answer relevancy, correctness | Did quality improve? |
| Abstention accuracy | Does the grader help it say "not found" correctly? |
| p50 / p95 latency | What did it cost the user? |
| LLM calls per question (mean, max) | What did it cost the free tier? |
| Per question type | Where exactly did it help? |

Decision rule (written **before** looking at the numbers, so you cannot cheat yourself):
keep the agentic path for a question type only if quality gains beat a threshold you set
now (e.g. "+0.05 faithfulness") at an acceptable latency. Otherwise the router sends that
type down the plain path.

---

## Phase 4 gate

- [ ] manual loop and graph both run; trace readable
- [ ] graph tests with fake LLM prove every cap
- [ ] C9 row and the per-type comparison table with latency and calls
- [ ] RAGAS/DeepEval vs own judge comparison recorded
- [ ] written decision: where the agentic path is used and where it is not
- [ ] versions pinned (langgraph, ragas/deepeval), verified dates
- [ ] interview notes; `git tag phase-4`
