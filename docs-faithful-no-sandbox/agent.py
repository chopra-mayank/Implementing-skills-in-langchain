"""
Docs-faithful Deep Agents demo — multi-skill, NO custom tools.

Three pure instruction skills (Type A) are auto-discovered from
./skills/. The model performs all work in-context. This file defines
zero custom tools and passes no `tools=` parameter to create_deep_agent.

The Skills middleware handles:
  - reading every SKILL.md
  - injecting name + description into the system prompt
  - matching each user query against the descriptions (progressive disclosure)
  - lazy-loading the chosen skill's body before answering
"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_groq import ChatGroq

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend


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


SAMPLE_MEETING_NOTES = (
    "we shipped the new login flow today thanks to the design team. "
    "metrics are already up by 8 percent. however the sso integration "
    "is still flaky for enterprise customers and we expect to fix that "
    "next week. next quarter we will focus on mobile, which is where "
    "most signups come from."
)

SAMPLE_CUSTOMER_MESSAGE = (
    "Hi, my name is Priya Shah, you can reach me at priya@example.com "
    "or +91-98765-43210. I am writing because your billing page keeps "
    "crashing and I really need this fixed today."
)

SAMPLE_SQL = (
    "SELECT customer_id, COUNT(*) AS orders, SUM(amount) AS total "
    "FROM orders WHERE created_at >= '2025-01-01' GROUP BY customer_id "
    "HAVING SUM(amount) > 1000 ORDER BY total DESC;"
)


def main():
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

    root = Path(__file__).parent
    backend = FilesystemBackend(root_dir=str(root), virtual_mode=False)

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
            "You are a versatile assistant. When the user's request "
            "matches one of the configured skills, follow that skill "
            "precisely."
        ),
    )

    queries = [
        f"Please convert these meeting notes into clean markdown:\n\n{SAMPLE_MEETING_NOTES}",
        f"Extract the structured fields from this customer message:\n\n{SAMPLE_CUSTOMER_MESSAGE}",
        f"Explain this SQL query in plain English:\n\n{SAMPLE_SQL}",
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
