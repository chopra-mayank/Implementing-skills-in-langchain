# Docs-Faithful Demo — Sandbox-style (Type C Skill Scripts)

Demonstrates the second skill pattern from the official Deep Agents
docs (https://docs.langchain.com/oss/python/deepagents/skills): each
skill **bundles its own executable** and the agent runs it via the
backend's shell.

## Table of Contents

1. [What this folder demonstrates](#1-what-this-folder-demonstrates)
2. [Files](#2-files)
3. [What the script is actually for](#3-what-the-script-is-actually-for)
4. [How the multi-skill routing works](#4-how-the-multi-skill-routing-works)
5. [End-to-end flow with an example](#5-end-to-end-flow-with-an-example)
6. [Who-talks-to-whom — important mental model](#6-who-talks-to-whom--important-mental-model)
7. [Code differences vs the no-sandbox folder](#7-code-differences-vs-the-no-sandbox-folder)
8. [Backend choice — honest disclaimer](#8-backend-choice--honest-disclaimer)
9. [Portability — copying a skill into another project](#9-portability--copying-a-skill-into-another-project)
10. [When to use this pattern in real life](#10-when-to-use-this-pattern-in-real-life)
11. [Running the demo](#11-running-the-demo)
12. [TL;DR](#12-tldr)

---

## 1. What this folder demonstrates

The **Type C** (skill script) pattern: each skill folder contains a
`SKILL.md` **plus a `.py` script** that does the actual work. The
agent learns the script exists from `SKILL.md` and runs it through the
backend's shell.

Key properties:

- Real `create_deep_agent` — no hand-rolled router.
- `agent.py` does **not** pass a `tools=` argument and defines no
  custom `@tool` functions anywhere.
- Three skills auto-discovered from `./skills/`.
- Backend is `LocalShellBackend` — provides file ops AND shell access.
- Each skill folder is a fully self-contained, portable unit.

---

## 2. Files

```
docs-faithful-sandbox/
├── agent.py
├── skills/
│   ├── text-stats/
│   │   ├── SKILL.md
│   │   └── text_stats.py        # word / char / sentence / top-N stats
│   ├── csv-summarizer/
│   │   ├── SKILL.md
│   │   └── csv_summarizer.py    # row count, type inference, per-column stats
│   └── base64-codec/
│       ├── SKILL.md
│       └── base64_codec.py      # base64 encode / decode
└── README.md
```

Every `.py` script is pure-stdlib Python — no extra dependencies.

---

## 3. What the script is actually for

The script does the **deterministic work** that LLMs do poorly. Think
of the LLM and the script as a division of labor:

| Job | Who does it |
|---|---|
| Understand what the user wants | LLM |
| Pick the right skill | LLM |
| Read the SKILL.md to learn the procedure | LLM (via filesystem tool) |
| Decide which file to process / what args to pass | LLM |
| **Count the words / parse the CSV / encode base64** | **Script** |
| Take the script's raw output and present it nicely | LLM |

### Why use a script instead of letting the LLM do it?

LLMs are unreliable at:

- **Math** — even simple arithmetic over multi-digit numbers
- **Exact string transformations** — base64, hashing, regex, JSON parsing
- **Counting** — words, sentences, occurrences, frequencies
- **File parsing** — they confabulate column types and skip rows
- **Anything format-strict** — generating valid JSON, exact API shapes

A script does these things **exactly, every time, for free**. The LLM
doesn't have to "think" about them — it just runs the script and reads
the answer.

### Mental model

> The LLM is the **driver**. The script is the **calculator** in the
> glove box. The driver decides where to go and explains the route to
> the passenger, but pulls out the calculator whenever exact numbers
> are needed.

You don't replace the LLM with the script — you give the LLM a tool it
can use when accuracy matters more than fluency.

---

## 4. How the multi-skill routing works

Identical to the no-sandbox folder. Deep Agents' Skills middleware:

1. Scans `./skills/` at startup, finds every `SKILL.md`.
2. Injects a "Skills System" block into the system prompt containing
   only **name + description** of each skill.
3. For each user query, the LLM matches the request against the
   descriptions and picks one.
4. The chosen skill's full body is lazy-loaded only when picked
   (progressive disclosure).

The only difference from Type A: the skill's body tells the agent to
run a script via the shell, instead of doing the work in its head.

---

## 5. End-to-end flow with an example

Example query: **"Summarize the CSV file at _sample.csv in this folder."**

```
                           ┌──────────────────────────────────────┐
                           │ USER                                 │
                           │ "Summarize the CSV at _sample.csv"   │
                           └────────────────┬─────────────────────┘
                                            ▼
┌────────────────────────────────────────────────────────────────────────┐
│ create_deep_agent — startup (one-time)                                 │
│                                                                        │
│   LocalShellBackend(root_dir="./")                                     │
│   Provides agent: read_file, write_file, ls, execute_shell             │
│                                                                        │
│   Skills middleware scans ./skills/ and finds 3 SKILL.md files.        │
│   Injects "Skills System" block (only descriptions) into system prompt.│
└────────────────────────────────────┬───────────────────────────────────┘
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LLM call #1 — "match"                                                  │
│   reasons: CSV path detected -> csv-summarizer description matches     │
│   action:  call read_file(/skills/csv-summarizer/SKILL.md)             │
└────────────────────────────────────┬───────────────────────────────────┘
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Filesystem tool — read_file                                            │
│   returns: full body. body says:                                       │
│     "Run: python skills/csv-summarizer/csv_summarizer.py <path>"       │
│     "Parse the JSON. Format as <template>."                            │
└────────────────────────────────────┬───────────────────────────────────┘
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LLM call #2 — "execute the script"                                     │
│   sees:    skill body + CSV path from user                             │
│   action:  call execute_shell(                                         │
│              "python skills/csv-summarizer/csv_summarizer.py _sample.csv")│
└────────────────────────────────────┬───────────────────────────────────┘
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Shell — runs the bundled script                                        │
│   csv_summarizer.py:                                                   │
│     - reads _sample.csv                                                │
│     - infers column types (numeric vs text)                            │
│     - computes per-column stats (min/max/mean OR top value/count)      │
│     - prints JSON to stdout                                            │
│   captured stdout returned to the agent                                │
└────────────────────────────────────┬───────────────────────────────────┘
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LLM call #3 — "format the answer"                                      │
│   sees:    shell output (the JSON) + Expected Output Format from body  │
│   action:  emit final formatted summary                                │
└────────────────────────────────────┬───────────────────────────────────┘
                                     ▼
                  ┌──────────────────────────────────────┐
                  │ FINAL ANSWER (to user)               │
                  │                                      │
                  │ CSV Summary: _sample.csv             │
                  │ Rows: 4, Columns: 4                  │
                  │ - name (text):    top "Alice" (1)    │
                  │ - age  (numeric): 29-42, mean 34     │
                  │ ...                                  │
                  └──────────────────────────────────────┘

Cost: 3 LLM calls + 1 file read + 1 shell execution.
```

---

## 6. Who-talks-to-whom — important mental model

A common misconception: *"the script calls the SKILL.md"* — **it does
not.**

The script and the SKILL.md **never talk to each other**. They are
independent files. The agent is the intermediary that reads one and
runs the other.

```
┌──────────────┐   reads (1)    ┌──────────────┐               ┌──────────────┐
│  SKILL.md    │ ◄─────────────►│  THE AGENT   │◄─────────────►│  user        │
└──────────────┘                │              │               └──────────────┘
                                │              │   runs via shell (2)
                                │              │ ◄────────────────────┐
                                └──────────────┘                      │
                                                                      ▼
                                                              ┌──────────────┐
                                                              │  script.py   │
                                                              └──────────────┘

      No arrow connects SKILL.md ↔ script.py. They're independent files.
```

- **SKILL.md** is documentation **for the agent** about what the
  script does and how to invoke it.
- **The script** is a vanilla CLI program. It doesn't know SKILL.md
  exists. It just reads its arguments and prints output.

The relationship is one-way: **agent → reads SKILL.md → runs script**.
There is no script → SKILL.md edge.

---

## 7. Code differences vs the no-sandbox folder

The agent code is **nearly identical**. The differences live in three
places:

| | This folder (`sandbox/`) | Sibling (`no-sandbox/`) |
|---|---|---|
| Backend import | `from deepagents.backends import LocalShellBackend` | `from deepagents.backends import FilesystemBackend` |
| Backend instantiation | `LocalShellBackend(root_dir=str(root))` | `FilesystemBackend(root_dir=str(root), virtual_mode=False)` |
| Skill folder contents | each skill has `SKILL.md` + a `.py` script | each skill has only `SKILL.md` |
| Setup | pre-creates `_sample.csv` for the csv-summarizer skill | (nothing) |
| `tools=` parameter | not passed | not passed |
| Custom `@tool` functions | none | none |

**That's literally it.** One backend class, one extra file per skill
folder. The big difference between Type A and Type C lives entirely in
the **backend choice** (which decides what the agent can do) and the
**skill folder contents** (which decides what work is available).

### What `LocalShellBackend` gives the agent (and `FilesystemBackend` does not)

- `execute_shell` — the agent can run arbitrary shell commands inside
  `root_dir`. **This is what makes script-based skills possible.**

Without a shell-capable backend, a Type C skill's script would just sit
on disk untouched — the agent could read it but never run it.

---

## 8. Backend choice — honest disclaimer

This demo uses `LocalShellBackend`, which gives the agent shell access
inside `root_dir`. **It is NOT a real security sandbox** — the script
runs as your local user. An LLM choosing what shell commands to run is
a security risk on any machine you care about.

For production isolation, replace one line in `agent.py`:

| Replace | With |
|---|---|
| `LocalShellBackend(root_dir=str(root))` | `langchain-sandbox` (Pyodide in Deno, pure-Python only) |
| | E2B (hosted Docker containers, requires API key) |
| | Custom Docker / Modal / etc. |

The rest of the code is unchanged. The agent doesn't care which
backend it's using — it just calls `execute_shell` and the backend
decides where the command actually runs.

---

## 9. Portability — copying a skill into another project

This is the killer feature of the Type C pattern: **each skill folder
is fully self-contained**.

### Best case — stdlib-only script (this folder)

All three scripts in this folder use only the Python standard library.
To reuse `csv-summarizer` in any other Deep Agents project:

1. Copy the entire `skills/csv-summarizer/` folder into the target
   project's `skills/` directory.
2. Make sure the target's backend is shell-capable (or swap one line
   in its `agent.py`).
3. Done.

No tool registration. No import statements. No agent code changes.
**Folder drag-and-drop, instant compatibility.**

### Real-life caveat — scripts with external dependencies

If your script does `import pandas` or `import requests`, those
packages must be available in whatever environment the sandbox runs:

- For `LocalShellBackend`: add to the target's `requirements.txt`.
- For Pyodide (`langchain-sandbox`): only pure-Python deps work
  (no `numpy`, no `pandas` C extensions).
- For E2B / custom Docker: install in the image.

This is the same dependency story you'd have moving any Python script
between projects — nothing Deep Agents-specific. **Prefer the standard
library** when writing skill scripts to maximize portability.

### Comparison with Type A

| Skill shape | Files to copy | Target project edits |
|---|---|---|
| Type A, no tools (sibling folder) | 1 `.md` file | None |
| Type A, declares tools (real life) | 1 `.md` + tool definitions | Register tools in `agent.py` |
| **Type C, stdlib script (this folder)** | **Whole folder** | **None** (if target uses shell backend) |
| Type C, external-dep script (real life) | Whole folder | Install script's deps in target's sandbox |

For drag-and-drop portability, the two extremes win:
**Type A with no tools** (one file), and **Type C with stdlib script**
(one folder). Anything in between requires some target-project setup.

---

## 10. When to use this pattern in real life

### The decision rule (not "text vs math")

A common intuition is "text → no sandbox, math → sandbox". It's *close*
but not quite right. The cleaner rule is:

> **Exact, verifiable output → Type C (this pattern).
> Judgment-based output → Type A (the no-sandbox folder).**

The official Deep Agents docs frame the same choice in terms of
**determinism**, not arithmetic:

> *"Use [code-bearing] skills for code that should be:
> **Reusable** across prompts, agents, or projects.
> **Deterministic** enough that you want the same behavior every time.
> **Too detailed** to keep in the model context as instructions.
> **Useful inside larger workflows**, such as scoring search results,
> normalizing API responses, validating records, grouping rows, or
> converting data into a report-ready shape."*

Notice "math" doesn't appear in that list — it's covered by
**determinism**. And the example tasks they call out (*normalizing
API responses, validating records, grouping rows*) are all text-ish
operations that nevertheless need exact, repeatable output.

### Why LLMs can't replace a script for these tasks

LLMs *can* compute — but they generate tokens probabilistically, not
algorithmically. They pattern-match rather than calculate. So:

- `7 + 5 = 12` — almost always correct (seen millions of times)
- `374 × 89 = ?` — sometimes wrong; the model *guesses what the answer
  looks like*
- Counting words in a paragraph — often off by 5–15%
- Summing a column of 40 numbers — usually wrong, sometimes silently
- Base64-encoding a string — frequently mangles non-ASCII characters

This isn't a model-specific issue (it happens with Claude, GPT, Llama,
Kimi — all of them). It's fundamental to how LLMs work. A script
doesn't pattern-match; it runs `sum(numbers)`. **Exactly right, every
time, for free.**

### Use Type C when…

- The answer must match a spec exactly (parser, schema, regex).
- The answer must be the same across runs.
- The answer involves arithmetic over many items.
- A unit test could verify whether the output is correct.
- The work is too detailed to fit reliably in a prompt.

### Concrete Type C workflows from real projects

- Data processing pipelines (parsing, normalization, transformation)
- Numerical computation (statistics, financial math, conversion factors)
- Heavy regex / text parsing
- Format conversion (PDF → text, CSV → JSON, image → EXIF)
- API calls with strict argument shapes
- Validation / schema checking
- Cryptography (hashing, encoding, signing)

End-to-end production shapes:

- **Invoice processor** — script parses PDF invoices into JSON; the
  LLM decides which file to process and writes the human summary.
- **Financial calculator** — script does compound interest / NPV; the
  LLM gathers inputs from the user and presents the result.
- **Log analyzer** — script does heavy regex over nginx logs; the LLM
  directs which log file and which time window.
- **Image metadata extractor** — script uses PIL / exifread; the LLM
  picks which file and explains what's interesting about the result.

### Cases that *look* like Type C but are fine as Type A

These are math-looking tasks where approximation is acceptable — push
them back to the no-sandbox folder:

- "Roughly how many calories in a banana?"
- "Explain how compound interest works" (conceptual, no specific numbers)
- "Is 7 prime?" (small reasoning, reliable)
- "Which is bigger: 4/9 or 5/12?"

### Cases that *look* like Type A but actually belong here

These are text-looking tasks that still need a script because the
output must be **exact**:

- "Convert this string to base64" — text task, exact output required
- "Validate this JSON against a schema" — text task, strict correctness
- "Extract every IP address from this log file" — regex precision matters
- "Count occurrences of 'urgent' across 100 tickets" — exact count needed
- "Format this date from MM/DD/YYYY to ISO 8601" — format must be exact

### The clean mental check

> *Could a unit test verify the output?* If yes → Type C. If no → Type A.

### In real projects you use both

A mature project typically has **both Type A and Type C side-by-side**.
They compose naturally: a Type C skill computes deterministic numbers
(counts, parses, validations); a Type A skill consumes those numbers
to write the human-readable summary around them.

For pure language work (summarizing, classifying, drafting), use the
**Type A** pattern in the sibling `docs-faithful-no-sandbox/` folder.

---

## 11. Running the demo

`GROQ_API_KEY` is read from the parent `.env`. From this folder:

```powershell
python agent.py
```

The demo runs three queries:

1. Text statistics on a sample paragraph
   → routes to `text-stats` → runs `text_stats.py`
2. Summarize a CSV file `agent.py` creates on disk
   → routes to `csv-summarizer` → runs `csv_summarizer.py`
3. Base64-encode a short string
   → routes to `base64-codec` → runs `base64_codec.py`

**Note on the 65-second sleep between queries:** Groq's free tier for
`openai/gpt-oss-20b` is capped at 8K tokens per minute. Deep Agents'
middleware stack pushes each request to ~3K tokens; three queries
fired back-to-back blow the per-minute window. The pause keeps us
under the cap. Upgrade Groq to Dev Tier (or use any model with higher
TPM) and the loop runs continuously.

---

## 12. TL;DR

> This folder demonstrates the **Type C skill pattern**: each skill
> bundles its own Python script and the agent runs it via the backend's
> shell. Zero custom `@tool` functions, zero hand-rolled routing —
> Deep Agents auto-discovers skills from `skills/` and the
> `LocalShellBackend` provides the shell capability. The script does
> the deterministic computation (counting, parsing, encoding); the LLM
> orchestrates and presents. Each skill folder is a fully
> self-contained, drag-and-drop unit — copy the folder into any project
> with a shell-capable backend and it works. Use this pattern whenever
> the answer must be exact rather than fluent.

For pure language work (judgment-based outputs, no exact computation)
see the sibling `docs-faithful-no-sandbox/` folder.
