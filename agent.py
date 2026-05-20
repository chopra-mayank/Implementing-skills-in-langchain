"""
Lightweight ReAct agent — same Skill + Tool concept, no Deep Agents overhead.

Strategy:
  1. Read skills/ticket-analyzer/SKILL.md from disk.
  2. Parse the YAML frontmatter (name, description, allowed-tools)
     so we still demonstrate the "Skill" abstraction to the mentor.
  3. Inject the markdown body straight into the system prompt.
  4. Bind only the tools listed in `allowed-tools` to a vanilla
     LangGraph ReAct agent.

Result: identical user-facing behaviour, single LLM call per turn,
roughly 10x faster than create_deep_agent.
"""

import os
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from tools import fetch_support_tickets


# Registry of every tool the project exposes. The SKILL.md decides
# which of these the agent actually gets to use.
TOOL_REGISTRY = {
    "fetch_support_tickets": fetch_support_tickets,
}


def load_skill(skill_path: Path) -> tuple[dict, str]:
    """Split a SKILL.md file into (frontmatter dict, body string)."""
    text = skill_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError(f"{skill_path} is missing YAML frontmatter")
    frontmatter = yaml.safe_load(match.group(1)) or {}
    body = match.group(2).strip()
    return frontmatter, body


def resolve_allowed_tools(frontmatter: dict) -> list:
    """Turn the `allowed-tools` field into real Python tool objects."""
    raw = frontmatter.get("allowed-tools", "")
    if isinstance(raw, list):
        names = [str(n).strip() for n in raw]
    else:
        names = [n.strip() for n in str(raw).split(",") if n.strip()]
    missing = [n for n in names if n not in TOOL_REGISTRY]
    if missing:
        raise ValueError(f"Skill references unknown tools: {missing}")
    return [TOOL_REGISTRY[n] for n in names]


def build_agent():
    load_dotenv()

    skill_path = Path(__file__).parent / "skills" / "ticket-analyzer" / "SKILL.md"
    frontmatter, body = load_skill(skill_path)
    tools = resolve_allowed_tools(frontmatter)

    system_prompt = (
        f"You are following the '{frontmatter.get('name')}' skill.\n"
        f"Skill description: {frontmatter.get('description')}\n\n"
        f"--- SKILL INSTRUCTIONS ---\n{body}\n--- END SKILL ---\n\n"
        "Follow the steps above exactly. Use only the tools you have been given."
    )

    model = ChatGroq(
        model="openai/gpt-oss-20b",
        api_key=os.environ["GROQ_API_KEY"],
        temperature=0,
    )

    return create_react_agent(model=model, tools=tools, prompt=system_prompt)


def main():
    agent = build_agent()

    user_query = "Please give me the support ticket report for user U001."
    print(f"\n>>> User: {user_query}\n")

    result = agent.invoke({"messages": [{"role": "user", "content": user_query}]})

    final = result["messages"][-1]
    print(">>> Agent:\n")
    print(final.content if hasattr(final, "content") else final)


if __name__ == "__main__":
    main()
