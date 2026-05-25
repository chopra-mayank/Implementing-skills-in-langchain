"""
Multi-skill, multi-tool agent.

Demonstrates the scenario the mentor asked about:
how does the agent pick the right skill when you have several?

Architecture (router-then-executor, two LLM stages):

    USER QUERY
        │
        ▼
    [Router LLM]  ── sees skill index (name + description only) ──► picks ONE skill name
        │
        ▼
    [Skill loader] ── reads that skill's SKILL.md body + allowed-tools
        │
        ▼
    [Executor agent] ── create_react_agent with ONLY that skill's tools
        │                and the skill body as the system prompt
        ▼
    FINAL ANSWER

This mirrors the "progressive disclosure" model from the Deep Agents
docs without bringing in the full deepagents middleware stack.
"""

import os
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

# Reuse the original single-skill tool.
from tools import fetch_support_tickets
# Plus the new tools.
from tools_extra import process_refund, get_customer_profile


# Project-wide tool registry. Every tool a SKILL.md could reference must
# be listed here. The skill's `allowed-tools` field decides which ones
# are actually exposed for any given turn.
TOOL_REGISTRY = {
    "fetch_support_tickets": fetch_support_tickets,
    "process_refund":        process_refund,
    "get_customer_profile":  get_customer_profile,
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


def discover_skills(skills_dir: Path) -> dict[str, dict]:
    """Scan skills/ for every SKILL.md and return a name -> info dict."""
    discovered = {}
    for skill_md in skills_dir.glob("*/SKILL.md"):
        frontmatter, body = load_skill(skill_md)
        name = frontmatter.get("name")
        if not name:
            continue
        discovered[name] = {
            "frontmatter": frontmatter,
            "body":        body,
            "path":        skill_md,
        }
    return discovered


def build_skill_index(skills: dict[str, dict]) -> str:
    """Format the lightweight skill catalog the router LLM sees."""
    lines = []
    for name, info in skills.items():
        desc = info["frontmatter"].get("description", "(no description)")
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines)


def resolve_allowed_tools(frontmatter: dict) -> list:
    """Translate the skill's `allowed-tools` field into real tool objects."""
    raw = frontmatter.get("allowed-tools", "")
    if isinstance(raw, list):
        names = [str(n).strip() for n in raw]
    else:
        names = [n.strip() for n in str(raw).split(",") if n.strip()]
    missing = [n for n in names if n not in TOOL_REGISTRY]
    if missing:
        raise ValueError(f"Skill references unknown tools: {missing}")
    return [TOOL_REGISTRY[n] for n in names]


def route_to_skill(model, skill_index: str, user_query: str) -> str:
    """Stage 1 — ask the LLM which skill best matches the user's query."""
    router_system = (
        "You are a router. Given a user query, pick the single most "
        "appropriate skill from the catalog below. Reply with ONLY the "
        "skill name on its own line (no quotes, no explanation). "
        "If no skill applies, reply with the single word `none`.\n\n"
        f"Skill catalog:\n{skill_index}"
    )
    response = model.invoke([
        {"role": "system", "content": router_system},
        {"role": "user",   "content": user_query},
    ])
    return response.content.strip().splitlines()[0].strip()


def run_skill(model, skill_info: dict, user_query: str) -> str:
    """Stage 2 — build a focused agent for the chosen skill and run it."""
    frontmatter = skill_info["frontmatter"]
    body        = skill_info["body"]
    tools       = resolve_allowed_tools(frontmatter)

    system_prompt = (
        f"You are following the '{frontmatter.get('name')}' skill.\n"
        f"Skill description: {frontmatter.get('description')}\n\n"
        f"--- SKILL INSTRUCTIONS ---\n{body}\n--- END SKILL ---\n\n"
        "Follow the steps above exactly. Use only the tools provided."
    )
    agent = create_react_agent(model=model, tools=tools, prompt=system_prompt)
    result = agent.invoke({"messages": [{"role": "user", "content": user_query}]})
    return result["messages"][-1].content


def handle(user_query: str) -> str:
    """End-to-end: router → executor → final answer."""
    load_dotenv()
    model = ChatGroq(
        model="openai/gpt-oss-20b",
        api_key=os.environ["GROQ_API_KEY"],
        temperature=0,
    )

    skills_dir = Path(__file__).parent / "skills"
    skills = discover_skills(skills_dir)
    skill_index = build_skill_index(skills)

    print(f"\n>>> User: {user_query}")
    print(f"\n[router] Available skills:\n{skill_index}")

    chosen = route_to_skill(model, skill_index, user_query)
    print(f"\n[router] Chose: {chosen}")

    if chosen == "none" or chosen not in skills:
        return "Sorry, no skill in this project handles that request."

    return run_skill(model, skills[chosen], user_query)


def main():
    queries = [
        "Give me the support ticket report for user U001.",
        "Please refund $25.50 against ticket T-102.",
        "What's the profile and lifetime value for user U001?",
    ]
    for q in queries:
        answer = handle(q)
        print(f"\n>>> Agent:\n{answer}\n")
        print("=" * 70)


if __name__ == "__main__":
    main()
