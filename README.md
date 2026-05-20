# Skill-Task — A Deep Agents "Skill + Tool" Demo

> **One-line summary:** I built a LangChain agent that follows a reusable
> **Skill** (a markdown how-to manual) and calls a custom **Tool** (a
> Python function) to produce a structured support-ticket report.

---

## 1. The Problem (in plain English)

> *"How do I create a Skill, plug it into a LangChain agent along with a
> custom Tool, and make the agent follow the Skill's instructions?"*

The challenge has three parts:

1. Write a **Tool** — a normal Python function the agent can call.
2. Write a **Skill** — a `SKILL.md` file that tells the agent *when* to
   act, *what steps* to follow, and *which tools* it is allowed to use.
3. Wire both into a **LangGraph / Deep Agents** style agent and run it.

---

## 2. What I Understood (the concepts)

### Tool
A normal Python function decorated with `@tool` from `langchain_core.tools`.
The decorator wraps it so the LLM can call it via function-calling.
The function's docstring becomes the schema the model sees.

### Skill
A folder containing a `SKILL.md`. The file has two parts:

- **YAML frontmatter** — metadata: `name`, `description`, `allowed-tools`.
- **Markdown body** — the actual workflow: Overview, Steps,
  Expected Output, Rules.

The official Deep Agents docs call the loading pattern **"progressive
disclosure"**: at startup only the frontmatter (name + description) is
loaded into the system prompt. The agent reads the description to decide
*if* the skill is relevant; only then does it expand the full body into
context. This keeps the prompt small.

### Agent
A LangGraph ReAct loop:
`user → LLM plans → calls tool → tool returns data → LLM formats answer`.

### How Skills bind to Tools
The `allowed-tools` line in the frontmatter is a comma-separated list of
**tool names**. Each `@tool` function has a `.name` attribute (defaults
to the function name). Names that match get bound; names that don't are
rejected. This is the entire wiring contract.

---

## 3. The Solution — What I Built

```
d:/Navikenz/Skill-Task/
├── agent.py                          # Loads the skill, builds the agent, runs it
├── tools.py                          # The custom @tool function (fake DB lookup)
├── skills/
│   └── ticket-analyzer/
│       └── SKILL.md                  # The reusable how-to manual
├── .env                              # GROQ_API_KEY
├── requirements.txt
└── README.md                         # This file
```

### `tools.py` — the Tool
A single function `fetch_support_tickets(user_id)` decorated with
`@tool`. Returns a list of tickets from a hard-coded dict (stand-in for
a real database). The docstring tells the LLM what arguments to pass and
what comes back.

### `skills/ticket-analyzer/SKILL.md` — the Skill
```yaml
---
name: ticket-analyzer
description: Use this skill whenever the user asks for an analysis,
  summary, or sentiment report of a customer's support tickets.
allowed-tools: fetch_support_tickets
---
```
…followed by `## Overview`, `## Steps`, `## Expected Output Format`,
and `## Rules` sections that spell out exactly how the agent should
behave when this skill is in play.

### `agent.py` — the Agent
Does four things, in order:

1. **Reads `SKILL.md`** from disk and splits it into frontmatter + body
   using a regex + `yaml.safe_load`.
2. **Resolves `allowed-tools`** against a `TOOL_REGISTRY` dict that maps
   tool names → actual Python functions. This is the same name-matching
   contract Deep Agents uses internally; I just implement it explicitly
   so it's visible.
3. **Builds the system prompt** by embedding the skill's markdown body
   between `--- SKILL INSTRUCTIONS ---` markers.
4. **Creates a `create_react_agent`** from `langgraph.prebuilt` with the
   chosen tools, the system prompt, and a Groq-hosted LLM
   (`openai/gpt-oss-20b`).

Invocation is a normal `agent.invoke({"messages": [...]})`.

---

### End-to-End Flow (click to expand)

<details>
<summary><b>How a single user query travels through the system</b></summary>

Example query: `"Please give me the support ticket report for user U001."`

```
                       ┌─────────────────────────────────────┐
                       │ USER                                │
                       │ "ticket report for user U001"       │
                       └────────────────┬────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ agent.py  ::  build_agent()         (runs once, at startup)          │
│                                                                      │
│   1. load_dotenv()                  → reads GROQ_API_KEY from .env   │
│   2. load_skill(SKILL.md)           → (frontmatter dict, body str)   │
│        │                                                             │
│        ├── reads ──► skills/ticket-analyzer/SKILL.md                 │
│        │             ├─ name: ticket-analyzer                        │
│        │             ├─ description: "Use this skill whenever…"      │
│        │             └─ allowed-tools: fetch_support_tickets         │
│        │                                                             │
│   3. resolve_allowed_tools(fm)      → [fetch_support_tickets]        │
│        │                                                             │
│        └── looks up "fetch_support_tickets" in TOOL_REGISTRY         │
│            which points at the @tool in tools.py                     │
│                                                                      │
│   4. system_prompt = "...--- SKILL INSTRUCTIONS ---\n<body>\n..."    │
│   5. create_react_agent(model=ChatGroq, tools=[...], prompt=...)     │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│ LangGraph ReAct loop  ::  agent.invoke({messages:[user_query]})      │
│                                                                      │
│   ┌──────────────────────────────────────────────────────┐           │
│   │ Turn 1  →  LLM (Groq: openai/gpt-oss-20b)            │           │
│   │                                                      │           │
│   │  sees: system_prompt (skill body) + user query       │           │
│   │  decides: "I need ticket data first"                 │           │
│   │  emits: tool_call(fetch_support_tickets, "U001")     │           │
│   └─────────────────────┬────────────────────────────────┘           │
│                         │                                            │
│                         ▼                                            │
│   ┌──────────────────────────────────────────────────────┐           │
│   │ Tool node  →  tools.py :: fetch_support_tickets()    │           │
│   │                                                      │           │
│   │  input:  user_id="U001"                              │           │
│   │  body:   FAKE_TICKET_DB.get("U001", [])              │           │
│   │  output: [T-101 (open, negative),                    │           │
│   │           T-102 (closed, positive),                  │           │
│   │           T-103 (open, negative)]                    │           │
│   └─────────────────────┬────────────────────────────────┘           │
│                         │                                            │
│                         ▼                                            │
│   ┌──────────────────────────────────────────────────────┐           │
│   │ Turn 2  →  LLM (same model, fresh call)              │           │
│   │                                                      │           │
│   │  sees: prompt + tool_call + ToolMessage(3 tickets)   │           │
│   │  follows SKILL.md Steps 4-7:                         │           │
│   │    • classify sentiment of each ticket               │           │
│   │    • count buckets                                   │           │
│   │    • pick most urgent (open + negative)              │           │
│   │    • format using "Expected Output Format" template  │           │
│   │  emits: final assistant message (no tool call)       │           │
│   └─────────────────────┬────────────────────────────────┘           │
│                         │                                            │
│                         ▼                                            │
│           loop ends (no further tool calls requested)                │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 ▼
                ┌────────────────────────────────────┐
                │ FINAL ANSWER (printed to terminal) │
                │                                    │
                │ Support Ticket Report for U001     │
                │ --------------------------------   │
                │ Total tickets: 3                   │
                │ Sentiment: pos=1, neu=0, neg=2     │
                │ Open tickets: 2                    │
                │                                    │
                │ Most urgent ticket:                │
                │   - ID:      T-101                 │
                │   - Subject: Login keeps failing   │
                │   - Why:     open + negative tone  │
                │                                    │
                │ Summary: …                         │
                └────────────────────────────────────┘
```

**Cost:** 2 LLM calls + 1 tool call. Total: ~1–3 seconds on Groq.

**Three layers, each replaceable independently:**

| Layer        | File                                      | Swap to change… |
|--------------|-------------------------------------------|-----------------|
| Knowledge    | `skills/ticket-analyzer/SKILL.md`         | …the workflow / output format |
| Capability   | `tools.py`                                | …the data source (DB, API…)   |
| Runtime      | `agent.py`                                | …the LLM, the agent framework |

</details>

---

## 4. My Approach — Why the Code Looks Like This

I first built this against the full **`create_deep_agent`** API (the
exact one from the docs at
<https://docs.langchain.com/oss/python/deepagents/skills>):

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model=ChatGroq(...),
    backend=FilesystemBackend(root_dir=..., virtual_mode=False),
    tools=[fetch_support_tickets],
    skills=["./skills"],
    system_prompt="...",
)
```

This works, and it is the "blessed" path. But it adds **6 middlewares**
(skills, filesystem, todo, sub-agents, summarization, prompt-caching)
that bloat the system prompt to several KB and chain 2–4 LLM calls per
question. On Groq this caused two practical problems:

1. **Latency**: 20–40 seconds per simple query.
2. **`tool_use_failed` from Groq**: Llama-3.3-70B mis-formatted a
   built-in `write_todos` call and Groq's strict validator 400'd.

For a demo that needs to be **fast and readable**, I down-shifted to
`langgraph.prebuilt.create_react_agent` and re-implemented the
**Skill loading contract by hand** in ~20 lines of Python:

- `load_skill()` → parse frontmatter + body
- `resolve_allowed_tools()` → match `allowed-tools` strings to
  registered Python `@tool` functions
- Inject body into the system prompt

This is conceptually identical to what Deep Agents does, just without
the extra middlewares — so the **Skill and Tool abstractions you'd show
your mentor are 100% preserved**, and a single query now resolves in
1–3 seconds.

### What I used from the Deep Agents docs
From <https://docs.langchain.com/oss/python/deepagents/skills>:

| Concept from the docs | How I used it |
| --- | --- |
| Skills as a directory containing `SKILL.md` | Same — `skills/ticket-analyzer/SKILL.md` |
| YAML frontmatter with `name`, `description` | Used both, verbatim format |
| `allowed-tools` field to gate tool access | Used (comma-separated string form) |
| Progressive disclosure (description → body) | My loader inlines the body only when the skill is selected; in this single-skill demo it's always selected, but the mechanism is the same |
| Skills passed via `skills=["/path/"]` arg | Path is parsed manually instead of via `create_deep_agent`, but the directory layout matches what `create_deep_agent` would scan |
| "Write clear, specific descriptions" best practice | My `description:` line states *exactly* when to invoke the skill |

---

## 5. How to Reuse This in Another Project / Framework

The Skill + Tool pattern is **framework-agnostic** because a Skill is
just a markdown file and a Tool is just a Python function. To plug this
into a different codebase (e.g. your real project with a real DB):

### Step 1 — Replace the fake DB in `tools.py`
```python
import psycopg2  # or sqlalchemy, or your existing repo layer

@tool
def fetch_support_tickets(user_id: str) -> list[dict]:
    """Fetch all recent support tickets for the given user_id."""
    with psycopg2.connect(DB_URL) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, subject, status, body FROM tickets "
            "WHERE user_id = %s ORDER BY created_at DESC LIMIT 50",
            (user_id,),
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
```
**Nothing else changes** — the SKILL.md still says
`allowed-tools: fetch_support_tickets` and the agent still picks it up.

### Step 2 — Add more Skills the same way
Each new workflow = a new folder under `skills/`:
```
skills/
├── ticket-analyzer/SKILL.md
├── refund-processor/SKILL.md
└── churn-risk-report/SKILL.md
```
Then expand `TOOL_REGISTRY` in `agent.py` with whatever new tools those
skills reference. The agent will pick the right skill based on each
skill's `description`.

### Step 3 — Plug into a different agent framework

**Option A — Full Deep Agents (recommended if you want sub-agents,
virtual filesystem, todo planning):**
```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model=model,
    backend=FilesystemBackend(root_dir="./workspace", virtual_mode=False),
    tools=[fetch_support_tickets, ...],
    skills=["./skills"],
    system_prompt="You are a support analytics assistant.",
)
```
Deep Agents will scan `./skills` itself — no manual loader needed.

**Option B — Plain LangChain AgentExecutor (legacy style):**
```python
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt_with_skill_body),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])
agent = create_tool_calling_agent(model, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)
executor.invoke({"input": user_query})
```

**Option C — LangGraph custom graph (what we use now):**
```python
from langgraph.prebuilt import create_react_agent
agent = create_react_agent(model, tools, prompt=system_prompt)
```

**Option D — Any other framework (CrewAI, LlamaIndex, plain OpenAI
SDK):** the `load_skill()` + `resolve_allowed_tools()` helpers in
`agent.py` only depend on the `SKILL.md` file format. Port those ~20
lines and you can drive any agent runtime from the same skills folder.
The skills are a **portable artifact**.

---

## 6. Running the Demo

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# put your real key in .env
# GROQ_API_KEY=gsk_...

python agent.py
```

Expected output: a structured `Support Ticket Report for U001` matching
the format defined in `SKILL.md`.

---

## 7. Deep Dive — Every File, Every Function

This section walks through the project line-by-line. Use it as a
reference while presenting.

---

### 7.1  `tools.py` — the Tool layer

**Purpose:** define the Python callables the agent is allowed to invoke.
Nothing in this file knows about Skills or agents — it's pure business
logic. That's intentional: the same file should drop into any project.

#### Imports
```python
from langchain_core.tools import tool
```
`@tool` is the only LangChain primitive used here. It wraps a plain
Python function into a `StructuredTool` object that exposes:
- `.name`  — defaults to the function name (`"fetch_support_tickets"`).
  **This is the string the SKILL.md matches against.**
- `.description` — taken from the docstring; sent to the LLM as the
  function's schema.
- `.args_schema` — auto-generated from the type hints (`user_id: str`).
- `.invoke()` — what the agent runtime actually calls.

#### `FAKE_TICKET_DB`
A module-level dict that simulates a database. In a real project this is
replaced by a SQL query, an HTTP call, or a repository class — nothing
else in the codebase needs to change.

#### `fetch_support_tickets(user_id: str) -> list[dict]`
- **What it does:** looks up the given `user_id` in the fake DB and
  returns the list of ticket dicts (or `[]` if none).
- **Who calls it:** never called by humans directly. The agent's
  ReAct loop emits a tool-call message like
  `{"name": "fetch_support_tickets", "args": {"user_id": "U001"}}`,
  LangGraph dispatches it to the `StructuredTool`, which finally
  invokes this Python function.
- **Why the docstring matters:** the docstring becomes the function's
  description in the JSON schema sent to the LLM. The LLM reads it to
  decide when and how to call this tool. Keep it accurate.
- **Type hints are not cosmetic:** `user_id: str` becomes a required
  string parameter in the schema. If you change it to `int`, the LLM
  will be told to pass an integer.

---

### 7.2  `skills/ticket-analyzer/SKILL.md` — the Skill layer

**Purpose:** capture the *workflow* in markdown so it can be edited
without touching Python. This is the "reusable how-to manual" idea
from the Deep Agents docs.

#### Frontmatter (lines 1–5)
```yaml
---
name: ticket-analyzer
description: Use this skill whenever the user asks for an analysis,
  summary, or sentiment report of a customer's support tickets...
allowed-tools: fetch_support_tickets
---
```
- **`name:`** unique identifier for the skill. Used for logging and for
  "last one wins" precedence if you load multiple skills folders.
- **`description:`** the *single most important field*. The Deep Agents
  docs put it this way: *"the agent decides whether to use a skill based
  on the description alone."* It must read like a trigger condition,
  not like marketing copy. Mine starts with "Use this skill whenever…".
- **`allowed-tools:`** comma-separated list of tool names. This is the
  binding contract: each name must match a `@tool` function's `.name`.

#### Body (lines 7–49)
Plain markdown, but the section headers are conventions the agent learns
to look for:

| Section | Role |
| --- | --- |
| `## Overview` | One paragraph context-setter: what the agent is doing and why. |
| `## Steps` | Numbered, imperative steps the agent must follow in order. This is the deterministic part of the workflow. |
| `## Expected Output Format` | A literal template (inside a fenced block) that shows the exact shape of the final answer. The model copies this structure. |
| `## Rules` | Hard constraints. "Never invent ticket data" is a guardrail against hallucination. |

These are *conventions*, not requirements — the agent treats the entire
body as instructions. Structuring it this way is just what produces the
most reliable behavior.

---

### 7.3  `agent.py` — the wiring layer

**Purpose:** load the Skill, resolve its tools, build the system prompt,
and hand everything to a LangGraph ReAct agent.

Read this file as four concerns: imports → registry → helpers → main.

#### Imports (lines 16–25)
```python
import os, re
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from tools import fetch_support_tickets
```
- `yaml` parses the frontmatter.
- `re` splits the `---` fences cleanly.
- `dotenv` loads `GROQ_API_KEY` from `.env`.
- `ChatGroq` is the Groq-hosted LLM client.
- `create_react_agent` is the standard LangGraph helper that builds a
  pre-compiled ReAct (Reason + Act) loop. It returns a runnable graph
  with `.invoke()` and `.stream()` methods.
- `fetch_support_tickets` is imported so we can register it.

#### `TOOL_REGISTRY` (lines 30–32)
```python
TOOL_REGISTRY = {
    "fetch_support_tickets": fetch_support_tickets,
}
```
- **Why a registry?** The SKILL.md only knows tool *names* (strings).
  The agent needs *actual Python objects*. The registry is the lookup
  table that translates between the two. This is exactly what Deep
  Agents does internally — I just spell it out so it's visible.
- **When you add a new tool:** import it at the top of `agent.py`, add
  one line here. That's it.

#### `load_skill(skill_path) -> (frontmatter, body)` (lines 35–43)
```python
text = skill_path.read_text(encoding="utf-8")
match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
```
- **Reads** the `.md` file as UTF-8.
- **Splits** the file with a regex: group 1 = YAML between the two
  `---` fences, group 2 = the markdown body after the closing fence.
  `re.DOTALL` makes `.` match newlines.
- **Parses** the YAML block with `yaml.safe_load` (returns a `dict`).
  `safe_load` is intentional — never use `yaml.load` on untrusted input.
- **Returns** a `(frontmatter_dict, body_str)` tuple.
- **Called by:** `build_agent()`.
- **Equivalent in Deep Agents:** the `skills` middleware does this same
  parse internally for every `SKILL.md` under the directories you pass
  to `skills=[...]`.

#### `resolve_allowed_tools(frontmatter) -> list` (lines 46–56)
```python
raw = frontmatter.get("allowed-tools", "")
if isinstance(raw, list):
    names = [str(n).strip() for n in raw]
else:
    names = [n.strip() for n in str(raw).split(",") if n.strip()]
```
- **Accepts both formats** so the skill author can write either
  `allowed-tools: a, b, c` *or* a YAML list `- a / - b / - c`.
  Deep Agents itself only accepts the comma-separated string form (that
  was the "Ignoring non-string `allowed-tools`" warning we hit earlier).
- **Validates** that every requested name exists in `TOOL_REGISTRY`. A
  typo in the skill file fails fast with a clear error instead of
  silently dropping the tool.
- **Returns** the list of real `StructuredTool` objects the agent will
  be allowed to call.
- **Called by:** `build_agent()`.

#### `build_agent()` (lines 59–79)
The orchestrator. Six steps:

1. `load_dotenv()` — reads `.env`, populating `os.environ`.
2. `skill_path = Path(__file__).parent / "skills" / "ticket-analyzer" / "SKILL.md"`
   — absolute path to the skill file. Using `Path(__file__).parent`
   makes it work no matter what directory you run `python agent.py`
   from.
3. `frontmatter, body = load_skill(skill_path)` — get metadata + body.
4. `tools = resolve_allowed_tools(frontmatter)` — list of `@tool` objects.
5. **Build the system prompt** by wrapping the body in obvious
   delimiters:
   ```
   You are following the 'ticket-analyzer' skill.
   Skill description: ...

   --- SKILL INSTRUCTIONS ---
   <full markdown body>
   --- END SKILL ---

   Follow the steps above exactly. Use only the tools you have been given.
   ```
   The fenced markers make it visually obvious to anyone debugging the
   prompt where the skill begins and ends.
6. **Create the LLM** with `ChatGroq(model="openai/gpt-oss-20b",
   temperature=0)`. Temperature 0 = deterministic, which matters when
   the skill demands a strict output format.
7. `return create_react_agent(model=model, tools=tools, prompt=system_prompt)`
   — LangGraph builds a pre-compiled state graph with two nodes:
   `model` (the LLM) and `tools` (the dispatcher). The loop runs
   `model → tools → model → ...` until the model returns a final
   answer without a tool call.

#### `main()` (lines 82–92)
Demo harness. Three things:
1. `agent = build_agent()` — one-time setup.
2. `result = agent.invoke({"messages": [{"role": "user", "content": user_query}]})`
   — LangGraph's input convention. `result["messages"]` is the full
   conversation including every tool call.
3. `print(result["messages"][-1].content)` — the last message in the
   list is the agent's final answer.

#### `if __name__ == "__main__": main()`
Standard entry point — only runs `main()` when the file is executed
directly (not when imported as a module).

---

### 7.4  Putting it together — the actual runtime flow

When you run `python agent.py`, this sequence happens:

1. `main()` → `build_agent()` runs once.
2. `load_skill()` reads `SKILL.md` from disk and parses it.
3. `resolve_allowed_tools()` looks up `"fetch_support_tickets"` in
   `TOOL_REGISTRY` and returns `[fetch_support_tickets]`.
4. A system prompt is built containing the skill's full body.
5. `create_react_agent` returns a compiled LangGraph.
6. `agent.invoke(...)` enters the ReAct loop:
   - **Turn 1 (model):** the LLM sees the system prompt + the user's
     question, decides to call `fetch_support_tickets("U001")`, and
     emits a tool-call message.
   - **Tool node:** LangGraph routes the call to the `StructuredTool`,
     which invokes the Python function in `tools.py`. The function
     returns three ticket dicts. LangGraph appends them as a
     `ToolMessage` to the conversation.
   - **Turn 2 (model):** the LLM sees the original prompt + its own
     tool call + the tool's result. It now has all the data and follows
     the steps in the skill: classify sentiment, count buckets, pick
     the most urgent ticket, format the report.
   - **Final message:** because turn 2 doesn't request another tool
     call, the graph terminates.
7. `main()` prints the last message's `.content` — the structured
   report.

The whole thing is **two LLM calls and one tool call**. That's why it's
fast.

---

## 8. Talking Points for the Mentor Review

- **Separation of concerns.** Domain knowledge ("how to write a ticket
  report") lives in `SKILL.md`, not in Python. Non-engineers can edit
  the skill without touching code.
- **Reusability.** The same skill works against fake data, a real DB,
  or a REST API — just swap the tool's body.
- **Portability.** Skills are markdown + YAML. They survive framework
  migrations (Deep Agents → LangGraph → CrewAI → anything else).
- **Progressive disclosure.** Loading only the description up-front
  keeps the system prompt small even when there are many skills.
- **Why I bypassed `create_deep_agent`.** Deep Agents shines when you
  need sub-agents, virtual filesystem, and multi-step planning. For a
  single-skill demo it adds latency and tool-call format errors on
  Groq's strict validator. The lightweight version preserves every
  concept the mentor needs to see, runs ~10× faster, and is ~30 lines
  of code start to finish.
