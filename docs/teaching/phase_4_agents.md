# Teaching Notes, Phase 4: Agentic RAG with LangGraph

Plan file: `docs/implementation_plan/phase_4_agents.md`

---

## 1. What an "agent" really is

**Like I'm five:** a normal program is a train: it always follows the same tracks. An agent
is a taxi driver: you say where you want to go, and the driver decides the turns, and
takes a detour if a road is blocked.

**What it really is:** an LLM placed inside a loop, where at some steps the **LLM's output
decides what happens next** (search again? rewrite? answer? give up?). No magic. Code still
runs every step; the LLM only picks between options we allow.

**The spectrum:**

```text
fixed pipeline ──────────── workflow with LLM decisions ──────────── fully autonomous agent
(Phase 1-3)                 (Phase 4: router, grader, rewriter)       (LLM invents its own plan)
predictable, cheap          controlled flexibility                    flexible, expensive, risky
```

We sit in the middle on purpose. Fully autonomous agents are hard to test, slow, and burn
free-tier calls. A **controlled graph** gives most of the benefit with caps and tests.

---

## 2. Agentic RAG: the specific ideas

| Idea | Name in papers | What it fixes |
|---|---|---|
| Grade retrieved chunks before answering | Corrective RAG (CRAG) | Answering from irrelevant chunks |
| Rewrite the query and retry if chunks are bad | CRAG / query rewriting | Badly phrased questions |
| Check the answer against the chunks | Self-RAG style self-check | Hallucinated claims |
| Route: retrieve, answer directly, or use a tool | Adaptive RAG | Wasting search on "hi" |

**Hybrid vs agentic (they are different axes):** hybrid is **how we search**. Agentic is
**who controls the steps**. You can have one without the other.

---

## 3. Why build the loop by hand first

`manual_loop.py` is 40 lines of plain Python: a `for` loop with a rewrite counter and a
regenerate counter. After writing it, LangGraph stops being magic: it is the same idea,
plus state management, checkpoints, pausing, streaming, and a picture of the flow.
In an interview, "I first wrote the loop by hand to understand it" shows depth.

**What you will notice in the trace:** sometimes the rewrite rescues a question; sometimes
it wastes two LLM calls and gives the same chunks. Agents are not free improvements.

---

## 4. LangGraph primer

**Like I'm five:** a board game. The **board** is the graph. Each **square** is a node (a
step). **Arrows** are edges (where you can go next). Some squares have a **fork** with a
rule ("if you rolled a 6, go left"): those are conditional edges. Everyone shares one
**scoreboard**: the state.

| Concept | In code | Meaning |
|---|---|---|
| State | `AgentState(TypedDict)` | The shared scoreboard every node reads and updates |
| Node | `builder.add_node("grade", grade_documents)` | A plain function: takes state, returns **only the fields it changed** |
| Edge | `builder.add_edge("retrieve", "grade")` | Always go from A to B |
| Conditional edge | `add_conditional_edges("grade", after_grading, {...})` | A function looks at state and returns which path to take |
| `START` / `END` | special nodes | Where the run begins and stops |
| Compile | `builder.compile()` | Checks the graph and makes it runnable |
| Recursion limit | runtime setting | Built-in guard: stops if too many steps run (an infinite loop) |
| Checkpointer | `compile(checkpointer=...)` | Saves state after each step (Phase 5: pause and resume) |

**Merging updates:** by default a node's returned field **replaces** the old value. For
lists you sometimes want **append** instead; LangGraph supports "reducers" for that
(VERIFY current syntax). In our plan we append manually (`state["trace"] + [...]`) to keep
it visible.

**Why LangGraph:**

| Option | Why not (for this project) |
|---|---|
| Plain Python loop | Fine for one loop; but pausing for a human, saving state across restarts, and streaming steps would all be hand-written |
| LlamaIndex | Excellent for RAG pipelines; less direct control over agent state and human-in-the-loop |
| CrewAI / AutoGen | Higher-level "agent teams"; less control over exact steps and checkpoints |
| LangChain agents (older style) | Less explicit; LangGraph is now the recommended way in that ecosystem for controlled agents |

The key reasons: **explicit state**, **checkpoints**, and **`interrupt`** for
human-in-the-loop (Phase 5).

---

## 5. Structured output: making LLM answers machine-readable

The grader must return something code can use: `{"relevant": [true, false, true]}`, not a
paragraph. Small free models often break JSON (missing bracket, extra text, wrong length).

**Our approach (`llm/structured.py`):**
1. Ask for JSON matching a Pydantic model; show the exact shape in the prompt.
2. Validate with Pydantic.
3. If invalid, retry **once**, including the validation error message ("field
   `relevant` missing"). Models often fix it when told what was wrong.
4. If still invalid, return `None` and let the node apply its **safe default**.

Some providers offer "JSON mode" or native tool/function calling that enforces a schema.
Use it where available (VERIFY per provider), but keep the validation: never trust model
output blindly.

---

## 6. Fail open vs fail closed

When a check itself breaks, what should happen?

| Node | If the check breaks | Why |
|---|---|---|
| Grader | **Fail open:** keep all chunks | Throwing away good chunks guarantees a bad answer |
| Groundedness check | **Fail closed:** low confidence -> abstain or human review | Letting an unchecked answer through with high confidence is worse |
| Input guard (Phase 6) | Usually fail closed | Safety first |

There is no universal answer; there is a **reasoned** answer per node. Write it down.

---

## 7. Caps and budgets

Every loop needs a stop: max 2 rewrites, max 1 regeneration, max N LLM calls per question,
timeouts per call, plus LangGraph's recursion limit as a final safety net.

**Why so strict:** free tiers have per-minute and per-day limits. One question stuck in a
loop can eat the quota for every other user. Caps protect quality, availability, and money
(if you ever move to paid).

---

## 8. Testing agents without spending tokens

Agents are hard to test because LLM outputs vary. Solution: a **fake LLM** that returns
scripted answers ("irrelevant", "irrelevant", "relevant"). Then you test the **control
logic** (routing, caps, counters) exactly and for free. Quality is measured separately by
evals with the real LLM. Two different questions, two different tools.

---

## 9. Was it worth it? Agentic vs non-agentic

Agents add LLM calls (router, grader, rewriter, checker) and latency. They can improve
faithfulness and abstention on hard questions, and do nothing for simple lookups.

**Decide the rule before you look at the numbers** ("keep agentic for a question type only
if faithfulness improves by at least X with p95 under Y"). Otherwise you will be tempted to
justify whatever you already built. This is how real teams avoid fooling themselves.

The great interview answer is not "I used agents". It is: **"I used the agentic path only
for the question types where the evals showed a gain, and sent simple lookups down the
cheap path."**

---

## 10. RAGAS and DeepEval

Both are open-source libraries that compute generation metrics (faithfulness, answer
relevancy, context precision/recall, and more) using a judge LLM. Benefits: standard
definitions others recognise, less code. Risks: they change often (pin versions), defaults
may assume a paid judge (configure a free one), and you must still spot-check.

We run them on the **same items** as our own judge and compare. Where they disagree, read
the item and decide who was right. That comparison itself is a strong interview story.

---

## 11. Self-check

1. Define an agent precisely, without hype.
2. Hybrid vs agentic: different how?
3. Draw your graph from memory with every cap.
4. What does a node return in LangGraph, and how does state get updated?
5. How do you make a small model return valid JSON reliably?
6. Grader fails open, groundedness fails closed: explain why.
7. How do you test routing logic without calling an LLM?
8. Where did the agentic path help on your data, and what did it cost?
