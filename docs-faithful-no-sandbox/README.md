# Docs-Faithful Demo — No-Sandbox (Type A Instruction Skills)

A clean, docs-faithful implementation of the Deep Agents Skills pattern
from https://docs.langchain.com/oss/python/deepagents/skills, using
**pure instruction skills only** — no custom tools, no scripts, no
sandbox needed.

## Table of Contents

1. [What this folder demonstrates](#1-what-this-folder-demonstrates)
2. [Files](#2-files)
3. [How the multi-skill routing works](#3-how-the-multi-skill-routing-works)
4. [End-to-end flow with an example](#4-end-to-end-flow-with-an-example)
5. [Code differences vs the sandbox folder](#5-code-differences-vs-the-sandbox-folder)
6. [Portability — copying a skill into another project](#6-portability--copying-a-skill-into-another-project)
7. [When to use this pattern in real life](#7-when-to-use-this-pattern-in-real-life)
8. [Running the demo](#8-running-the-demo)
9. [TL;DR](#9-tldr)

---

## 1. What this folder demonstrates

The **Type A** (instruction) skill pattern: each skill is just a
markdown file describing a workflow. The LLM does all the work
in-context. Nothing is computed by code outside the model.

Key properties:

- Real `create_deep_agent` — no hand-rolled router.
- `agent.py` does **not** pass a `tools=` argument and defines no
  custom `@tool` functions anywhere.
- Three skills auto-discovered from `./skills/`.
- Backend is `FilesystemBackend` — provides file read/write but **no
  shell**. The agent cannot execute scripts even if it wanted to.
- Progressive disclosure is handled entirely by Deep Agents.

---

## 2. Files

```
docs-faithful-no-sandbox/
├── agent.py
├── skills/
│   ├── markdown-formatter/SKILL.md   # raw text -> structured Markdown
│   ├── json-extractor/SKILL.md       # unstructured text -> fixed JSON schema
│   └── sql-explainer/SKILL.md        # SQL query -> plain-English explanation
└── README.md
```

Each `SKILL.md` is a single markdown file with YAML frontmatter
(`name`, `description`) and a body containing `## Overview`,
`## Steps`, `## Expected Output Format`, and `## Rules` sections.

---

## 3. How the multi-skill routing works

Deep Agents' Skills middleware does all the routing automatically. At
startup it scans `./skills/` and injects a "Skills System" block into
the agent's system prompt containing only the **name + description** of
every skill:

```
Available skills:
- markdown-formatter (at /skills/markdown-formatter/SKILL.md):
    "Use this skill when the user provides raw, unformatted text..."
- json-extractor (at /skills/json-extractor/SKILL.md):
    "Use this skill when the user provides unstructured text..."
- sql-explainer (at /skills/sql-explainer/SKILL.md):
    "Use this skill when the user provides a SQL query..."
```

For each user query:

1. **Match** — the LLM reads the descriptions and picks the one that
   best matches the request.
2. **Read** — the LLM calls the filesystem tool (`read_file`) to load
   the full body of the chosen `SKILL.md`. This is the "progressive
   disclosure" step — the body only enters context now.
3. **Execute** — the LLM follows the body's Steps and produces the
   final answer.

The other two skills' bodies are **never** loaded for this query. Add
50 skills and the system prompt grows by only ~150 tokens (one
description per skill). The executor prompt does not grow at all.

### Why descriptions are critical

The LLM picks the skill from the **description alone**. The official
docs are explicit:

> *"Write clear, specific descriptions in your SKILL.md frontmatter.
> The agent decides whether to use a skill based on the description
> alone."*

A vague description ("does text stuff") causes mis-routing. A specific
trigger sentence ("Use this skill when the user provides a SQL query
and wants a plain-English explanation...") routes reliably.

---

## 4. End-to-end flow with an example

Example query: **"Explain this SQL query in plain English: SELECT
customer_id, COUNT(*) ... GROUP BY customer_id ..."**

```
                           ┌──────────────────────────────────────┐
                           │ USER                                 │
                           │ "Explain this SQL: SELECT ... GROUP" │
                           └────────────────┬─────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────┐
│ create_deep_agent — startup (one-time)                                 │
│                                                                        │
│   FilesystemBackend(root_dir="./", virtual_mode=False)                 │
│   Skills middleware scans ./skills/ and finds 3 SKILL.md files.        │
│   Injects "Skills System" block (only descriptions) into system prompt.│
└────────────────────────────────────┬───────────────────────────────────┘
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LLM call #1 — "match"                                                  │
│   reasons: SQL keywords detected -> sql-explainer description matches  │
│   action:  call read_file(/skills/sql-explainer/SKILL.md)              │
└────────────────────────────────────┬───────────────────────────────────┘
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Filesystem tool — read_file                                            │
│   returns: full markdown body (Overview, Steps, Output Format, Rules)  │
│   ← progressive disclosure: body enters context only now               │
└────────────────────────────────────┬───────────────────────────────────┘
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LLM call #2 — "execute"                                                │
│   sees:    skill body + the SQL query                                  │
│   action:  follow Steps 1-6, emit final 5-7 sentence plain-English     │
│            explanation, no further tool call                           │
└────────────────────────────────────┬───────────────────────────────────┘
                                     ▼
                  ┌──────────────────────────────────────┐
                  │ FINAL ANSWER (to user)               │
                  │                                      │
                  │ "This query returns the customers    │
                  │  who placed orders above $1,000 in   │
                  │  2025 along with their order count   │
                  │  and total spend..."                 │
                  └──────────────────────────────────────┘

Cost: 2 LLM calls + 1 file read. No shell, no script, no sandbox.
```

---

## 5. Code differences vs the sandbox folder

The agent code is **nearly identical**. The differences live in three
places:

| | This folder (`no-sandbox/`) | Sibling (`sandbox/`) |
|---|---|---|
| Backend import | `from deepagents.backends import FilesystemBackend` | `from deepagents.backends import LocalShellBackend` |
| Backend instantiation | `FilesystemBackend(root_dir=str(root), virtual_mode=False)` | `LocalShellBackend(root_dir=str(root))` |
| Skill folder contents | each skill has only `SKILL.md` | each skill has `SKILL.md` + a `.py` script |
| `tools=` parameter | not passed | not passed |
| Custom `@tool` functions | none | none |

**That's literally it.** One backend class, one extra file per skill
folder. The big difference between Type A and Type C lives entirely in
the **backend choice** (which decides what the agent can do) and the
**skill folder contents** (which decides what work is available).

### What `FilesystemBackend` gives the agent

- `read_file`, `write_file`, `ls`, `glob`, `grep` — file operations
  scoped to `root_dir`.
- **No shell.** The agent cannot run commands or execute scripts.

That's why scripts are pointless in a Type A folder — even if you
dropped a `.py` next to a SKILL.md, the agent would have no way to run
it.

---

## 6. Portability — copying a skill into another project

This is the killer feature of the Type A pattern.

### Best case — pure-reasoning skill (this folder)

Each of our three skills declares **no `allowed-tools`** and has **no
runtime dependencies**. To use any of them in another Deep Agents
project:

1. Copy `skills/<skill-name>/SKILL.md` into the target project's
   `skills/` directory.
2. Done.

Zero edits to the target's `agent.py`. Zero new dependencies. **One
file, drag-and-drop, instant compatibility.**

### Real-life caveat — Type A skills that declare tools

In production, instruction skills often DO declare `allowed-tools`
(e.g. `allowed-tools: db_query, slack_post`). When that's the case the
target project must have tools named `db_query` and `slack_post`
registered. To port such a skill you'd need to:

1. Copy the `SKILL.md`.
2. Find the tool definitions in the source project.
3. Re-implement / register them in the target.

Still much easier than refactoring agent code, but not pure
drag-and-drop. **The pure-reasoning skills in this folder are the gold
standard for portability.**

---

## 7. When to use this pattern in real life

### The decision rule (not "text vs math")

A common intuition is "text → no sandbox, math → sandbox". It's *close*
but not quite right. The cleaner rule is:

> **Judgment-based output → Type A (this pattern).
> Exact, verifiable output → Type C (the sandbox folder).**

The official Deep Agents docs frame the same choice in terms of
**determinism**:

> *"Use [code-bearing] skills for code that should be:
> Reusable across prompts. **Deterministic enough that you want the
> same behavior every time.** Too detailed to keep in the model
> context as instructions."*

LLMs *can* do math (and they do it often), but they generate tokens
probabilistically — they pattern-match rather than compute. So even
the best Groq / Anthropic / OpenAI model is approximating, not
calculating. That's why "answer must be exactly correct" is the real
trigger for reaching past Type A.

### Use Type A when…

- The answer is "good enough" / "well-written" / "useful" rather than
  exactly right.
- Two different runs can both be acceptable outputs.
- The task is pure language work: reasoning, classifying, drafting,
  summarizing, explaining, reformatting.

### Concrete Type A workflows from real projects

- Customer-support triage (categorize → extract → draft response)
- Content moderation / classification
- Document summarization with a fixed structure
- Format conversion (markdown reformatter, JSON extractor, etc.)
- Code review against a written style guide
- Translating between writing styles
- Drafting templates (PRDs, status updates, RFCs)
- Explaining technical artifacts (SQL, code diffs, contracts)

### Cases that *look* like Type A but actually need Type C

These are text-looking tasks that still need a script because the
output must be **exact**:

- "Convert this string to base64" — text task, exact output required
- "Validate this JSON against a schema" — text task, strict correctness
- "Extract every IP address from this log file" — regex precision matters
- "Count occurrences of 'urgent' across 100 tickets" — exact count needed
- "Format this date from MM/DD/YYYY to ISO 8601" — format must be exact

For all of those, see the sibling `docs-faithful-sandbox/` folder.

### Cases that *look* like Type C but are fine as Type A

These are math-looking tasks where approximation is fine:

- "Roughly how many calories in a banana?"
- "Explain how compound interest works" (conceptual, no specific numbers)
- "Is 7 prime?" (small reasoning, reliable)
- "Which is bigger: 4/9 or 5/12?"

The cleanest mental check before picking a pattern is: **could a unit
test verify the output?** If yes, you probably want a script. If no,
the LLM is the right tool.

### In real projects you use both

A mature project typically has **both Type A and Type C side-by-side**
and they compose naturally: a Type C skill computes deterministic
numbers (counts, validations, parses) and a Type A skill consumes
those numbers to write the human-readable summary around them.

---

## 8. Running the demo

`GROQ_API_KEY` is read from the parent `.env`. From this folder:

```powershell
python agent.py
```

The demo runs three queries in sequence:

1. Convert meeting notes into clean Markdown → routes to
   `markdown-formatter`
2. Extract name / email / phone / intent / urgency from a customer
   message → routes to `json-extractor`
3. Explain a SQL query in plain English → routes to `sql-explainer`

**Note on the 65-second sleep between queries:** Groq's free tier for
`openai/gpt-oss-20b` is capped at 8K tokens per minute. Deep Agents'
middleware stack pushes each request to ~3K tokens, so three queries
fired back-to-back blow the per-minute window. The pause keeps us under
the cap. Upgrade Groq to Dev Tier (or use any model with higher TPM)
and the loop runs continuously.

---

## 9. TL;DR

> This folder is the **simplest possible expression** of the Deep
> Agents Skills pattern: pure instruction skills, no custom tools, no
> scripts, no sandbox. The agent code is generic and never changes
> when skills are added or removed — Deep Agents' Skills middleware
> auto-discovers everything in `skills/` and handles progressive
> disclosure (descriptions in the system prompt, full bodies loaded
> on-demand). Each skill is a single markdown file that can be copied
> verbatim into any other Deep Agents project. Use this pattern for
> any workflow expressible as LLM reasoning — anything judgment-based
> rather than number-based.

For deterministic computation (math, parsing, exact format conversions)
see the sibling `docs-faithful-sandbox/` folder.
