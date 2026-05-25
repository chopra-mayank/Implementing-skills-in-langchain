"""
Docs-faithful Deep Agents demo — multi-skill, ALL skill scripts, NO custom tools.

Three Type-C skills (text-stats, csv-summarizer, base64-codec) each
bundle their own Python script. The agent runs them via the backend's
shell. No @tool functions are defined; no `tools=` parameter is passed.

WARNING: LocalShellBackend is NOT a real security sandbox — scripts
run as your local user. For production, swap that one line to
langchain-sandbox (Pyodide + Deno) or E2B (hosted Docker).
"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_groq import ChatGroq

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend


def _content_to_str(content) -> str:
    """Coerce LangChain message content (str or list-of-parts) to a string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict):
                parts.append(p.get("text") or p.get("content") or "")
            else:
                parts.append(str(p))
        return "\n".join(s for s in parts if s)
    return str(content) if content else ""


def extract_final_answer(result: dict) -> str:
    """Walk backwards through messages and return the last non-empty AI text."""
    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage):
            text = _content_to_str(msg.content)
            if text.strip():
                return text
    return "(no assistant text in result)"


def trace_messages(result: dict) -> None:
    """Diagnostic: print every message's type and a content preview."""
    print("\n--- MESSAGE TRACE ---")
    for i, msg in enumerate(result.get("messages", [])):
        kind = type(msg).__name__
        text = _content_to_str(msg.content)
        preview = text.replace("\n", " ")[:120]
        tool_calls = getattr(msg, "tool_calls", None)
        tc = f"  tool_calls={[t.get('name') for t in tool_calls]}" if tool_calls else ""
        print(f"  [{i:>2}] {kind:14s} content='{preview}'{tc}")
    print("--- END TRACE ---\n")


SAMPLE_TEXT = (
    "LangGraph is a framework for building stateful agents. "
    "It uses graphs of nodes and edges. State flows through the graph. "
    "Each node can be a function or a tool call. LangGraph supports "
    "streaming, persistence, and human-in-the-loop. LangGraph is great."
)


def main():
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

    root = Path(__file__).parent
    backend = LocalShellBackend(root_dir=str(root))

    # Qwen 3 has a strong reputation for reliable tool calling, which
    # matters here because Deep Agents puts 8+ tools in scope and
    # Llama-3.3-70B mis-formats under that load. gpt-oss-20b's 8K TPM
    # is too small for one Deep Agents call.
    model = ChatGroq(
        model="qwen/qwen3-32b",
        api_key=os.environ["GROQ_API_KEY"],
        temperature=0,
    )

    agent = create_deep_agent(
        model=model,
        backend=backend,
        skills=[str(root / "skills")],
        system_prompt=(
            "You are a deterministic-computation assistant. When the "
            "user's request matches a configured skill, follow that "
            "skill exactly and run any bundled scripts via the shell."
        ),
    )

    # Pre-create a sample CSV so the csv-summarizer skill has data to work with.
    sample_csv = root / "_sample.csv"
    sample_csv.write_text(
        "name,age,city,score\n"
        "Alice,30,Mumbai,87.5\n"
        "Bob,42,Delhi,92.1\n"
        "Carol,29,Mumbai,78.3\n"
        "Dan,35,Bangalore,88.0\n",
        encoding="utf-8",
    )

    queries = [
        f"Give me text statistics for the following text:\n\n{SAMPLE_TEXT}",
        f"Summarize the CSV file at {sample_csv.name} in this folder.",
        "Encode the string 'Hello, Deep Agents!' as base64.",
    ]

    # Short safety pause between queries. With llama-3.3-70b's 30K TPM
    # cap this is mostly precautionary.
    PAUSE_SECONDS = 10

    for i, q in enumerate(queries, start=1):
        print(f"\n>>> User ({i}/{len(queries)}): {q[:90].strip()}...\n")
        result = agent.invoke({"messages": [{"role": "user", "content": q}]})
        trace_messages(result)
        print(">>> Agent:\n")
        print(extract_final_answer(result))
        print("=" * 72)
        if i < len(queries):
            print(f"\n[sleeping {PAUSE_SECONDS}s to dodge Groq TPM cap]\n")
            time.sleep(PAUSE_SECONDS)


if __name__ == "__main__":
    main()
