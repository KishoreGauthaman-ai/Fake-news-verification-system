"""
backend/agent.py — LangChain agent setup for the Fact Check workflow.

Uses create_tool_calling_agent + AgentExecutor with the tool functions
from backend/tools.py. The agent system prompt enforces:
- Must use more than one tool before concluding
- Hard limit 5 tool calls
- Verdict rules: Unverified/Misleading if evidence conflicts/thin
- Return every tool call as agent_trace
"""

from __future__ import annotations

import json
from typing import Any, List, Dict, Optional

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_groq import ChatGroq
from langchain.schema import SystemMessage, HumanMessage
from langchain.tools import tool

try:
    from .tools import (
        rss_fact_check_search,
        google_fact_check,
        ddgs_web_search,
        fetch_article,
        score_source_trust,
        VerdictResult,
        TOOLS_REGISTRY,
    )
except ImportError:
    from tools import (
        rss_fact_check_search,
        google_fact_check,
        ddgs_web_search,
        fetch_article,
        score_source_trust,
        VerdictResult,
        TOOLS_REGISTRY,
    )


# ---- Tool wrappers for LangChain ----

@tool
def _rss_fact_check_search(query: str) -> str:
    """Wrapper for rss_fact_check_search — FIRST priority tool."""
    results = rss_fact_check_search(query)
    if results is None:
        return json.dumps({"found": False, "results": []})
    return json.dumps({"found": True, "results": results})


@tool
def _google_fact_check(query: str) -> str:
    """Wrapper for google_fact_check — SECOND priority tool."""
    results = google_fact_check(query)
    if results is None:
        return json.dumps({"found": False, "results": []})
    return json.dumps({"found": True, "results": results})


@tool
def _ddgs_web_search(query: str, max_results: int = 6) -> str:
    """Wrapper for ddgs_web_search — FALLBACK tool."""
    results = ddgs_web_search(query, max_results=max_results)
    return json.dumps({"found": True, "results": results})


@tool
def _fetch_article(url: str) -> str:
    """Wrapper for fetch_article — extract article content."""
    result = fetch_article(url)
    if result is None:
        return json.dumps({"found": False, "text": "", "title": "", "source_url": url})
    return json.dumps({"found": True, "text": result["text"], "title": result["title"], "source_url": result["source_url"]})


@tool
def _score_source_trust(url: str) -> str:
    """Wrapper for score_source_trust — static trust tier."""
    domain = extract_domain(url)
    tier = score_source_trust(domain)
    return json.dumps({"domain": url, "tier": tier})


def extract_domain(url: str) -> str:
    """Extract domain from URL for trust scoring."""
    from urllib.parse import urlparse
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


# ---- LangChain agent system prompt (compact — smaller prompt = faster LLM turns) ----

AGENT_SYSTEM_PROMPT = """You are a Fact Check AI agent verifying claims with multiple independent sources.

RULES:
1. Use MORE THAN ONE tool before concluding — never verdict off a single source.
2. Hard limit: 5 tool calls total.
3. Evidence thin or conflicting → verdict MUST be "Unverified" or "Misleading" with neutral explanation.
4. Never force True/False without solid multi-source agreement.
5. End with a Final Answer containing a JSON verdict.

EFFICIENCY — STOP AS SOON AS YOU HAVE ENOUGH:
- "Enough evidence" = 2+ sources that agree, or 1 tier-1 fact-check with a clear rating plus 1 corroborating source.
- The moment you have enough evidence, produce the Final Answer IMMEDIATELY. Do NOT call any more tools.
- If a tool returns nothing relevant, move to the next tool once — never retry the same tool with the same input.
- Never repeat a Thought or tool call you already made. Call score_source_trust at most once, at the end, on the single most important source.
- Do not call fetch_article unless a snippet is genuinely too short to judge stance.

TOOLS (priority order):
1. rss_fact_check_search(query) — Indian fact-check feeds. Try FIRST.
2. google_fact_check(query) — Google Fact Check API. SECOND.
3. ddgs_web_search(query) — web search, top 6. FALLBACK only.
4. fetch_article(url) — extract article text (~2000 chars). Only if a snippet isn't enough.
5. score_source_trust(url) — trust tier for a domain.

FINAL ANSWER format (JSON) — "sources" MUST be a list of objects, never bare URL strings:
{{"verdict": "True|False|Misleading|Unverified", "confidence": <0-100>, "reasoning": "<explanation>", "sources": [{{"title": "<title>", "url": "<url>", "stance": "supports|contradicts|neutral"}}]}}

Use exactly this ReAct format:
Thought: <reasoning>
Action: <tool name>
Action Input: <input>
Observation: <tool result>
(repeat only until you have enough evidence, then)
Thought: I have enough evidence
Final Answer: <the JSON verdict>"""


def create_agent(llm: Any) -> AgentExecutor:
    """
    Create and return a LangChain AgentExecutor with the fact-check tools.
    Uses create_react_agent with a custom prompt for better compatibility.
    """
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain.prompts import PromptTemplate

    tools = [
        _rss_fact_check_search,
        _google_fact_check,
        _ddgs_web_search,
        _fetch_article,
        _score_source_trust,
    ]

    # Prompt must include {tools}, {tool_names}, {input}, {agent_scratchpad}
    # for create_react_agent. Format rules live in the system prompt above.
    prompt_template = f"""{AGENT_SYSTEM_PROMPT}

Tools: {{tool_names}}

Tool descriptions:
{{tools}}

Claim: {{input}}
Agent Scratchpad: {{agent_scratchpad}}"""

    prompt = PromptTemplate.from_template(prompt_template)

    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=8,  # headroom so the final-answer turn always fits (prompt caps tool calls at 5)
        max_execution_time=110,  # stay under the frontend/API timeout
        handle_parsing_errors=True,  # recover when the model breaks ReAct format
        return_intermediate_steps=True,
    )

    return executor
