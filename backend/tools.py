"""
backend/tools.py — Fact Check tool functions in priority order.

These are @tool-decorated functions used by the LangChain agent.
Order matters: rss_fact_check_search → google_fact_check → ddgs_web_search → fetch_article → score_source_trust
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
import ddgs
import trafilatura
from pydantic import BaseModel


# ---- Data models for tool outputs ----

class ToolStep(BaseModel):
    name: str
    args: Dict[str, Any]
    result: Any
    success: bool
    error: Optional[str] = None


class VerdictResult(BaseModel):
    verdict: str  # "True" | "False" | "Misleading" | "Unverified"
    confidence: int  # 0-100
    reasoning: str
    sources: List[Dict[str, Any]]
    agent_trace: List[ToolStep]


# ---- 1. rss_fact_check_search ----

def rss_fact_check_search(query: str) -> Optional[List[Dict[str, Any]]]:
    """
    Search Indian fact-check RSS feeds for the claim.
    Calls search_fact_check_feeds() from fact_check_rss.py.
    Try this FIRST for any claim.
    Returns list of relevant fact-check entries or None/nothing if no coverage.
    """
    from fact_check_rss import search_fact_check_feeds

    try:
        results = search_fact_check_feeds(query, max_results=5)
        if results:
            return results
        return None
    except Exception as e:
        # Log but don't crash — fall through to next tool
        print(f"[tool] rss_fact_check_search error: {e}")
        return None


# ---- 2. google_fact_check ----

def google_fact_check(query: str) -> Optional[List[Dict[str, Any]]]:
    """
    Google Fact Check Tools API query.
    Key from .env as GOOGLE_FACT_CHECK_API_KEY.
    Try SECOND if #1 returns nothing relevant.
    Returns list of fact-check claims or None if key missing/no results.
    """
    import requests

    api_key = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
    if not api_key or api_key == "your_google_key_here":
        print("[tool] google_fact_check: GOOGLE_FACT_CHECK_API_KEY not set in .env")
        return None

    try:
        resp = requests.get(
            "https://factchecktools.googleapis.com/v1alpha1/claims:search",
            params={"key": api_key, "query": query, "pageSize": 10},
            timeout=8,
        )
        if resp.status_code != 200:
            print(f"[tool] google_fact_check: HTTP {resp.status_code}")
            return None

        data = resp.json()
        claims = []
        for c in data.get("claims", []):
            claim_review = (c.get("claimReview") or [{}])[0]
            review = claim_review.get("textualRating", "")
            publisher = (claim_review.get("publisher") or {}).get("name", "")
            url = claim_review.get("url", "")
            claims.append({
                "title": c.get("text", "")[:200],
                "url": url,
                "source": publisher,
                "stance": review.lower() or "neutral",
                "rating": review,
            })
        return claims
    except Exception as e:
        print(f"[tool] google_fact_check error: {e}")
        return None


# ---- 3. ddgs_web_search ----

def ddgs_web_search(query: str, max_results: int = 6) -> List[Dict[str, Any]]:
    """
    ddgs library web search, top N results.
    FALLBACK only — the agent must not skip straight here without trying
    the fact-check tools first.
    Returns list of search results with title, body, href.
    """
    results: List[Dict[str, Any]] = []
    try:
        from ddgs import DDGS
        for r in DDGS().text(
            query,
            max_results=max_results,
            region="us-en",
            backend="duckduckgo, google, bing",
        ):
            results.append({
                "title": r.get("title", ""),
                "body": r.get("body", ""),
                "href": r.get("href", ""),
            })
        return results
    except Exception as e:
        print(f"[tool] ddgs_web_search error: {e}")
        return []


# ---- 4. fetch_article ----

def fetch_article(url: str) -> Optional[Dict[str, str]]:
    """
    Fetch and extract article content using trafilatura.
    ~2000 char cap on extracted text.
    Only when a snippet isn't enough to judge stance.
    Returns dict with 'title', 'text', 'source_url' or None on failure.
    """
    try:
        # Download and extract main text
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None

        extracted = trafilatura.extract(downloaded, include_comments=False, include_images=False)
        if not extracted:
            return None

        # Cap at ~2000 characters
        cap_text = extracted[:2000]

        # Get title from document metadata
        title = ""
        try:
            metadata = trafilatura.extract_metadata(downloaded)
            if metadata and getattr(metadata, "title", None):
                title = str(metadata.title)
        except Exception:
            title = ""

        return {
            "title": title,
            "text": cap_text,
            "source_url": url,
        }
    except Exception as e:
        print(f"[tool] fetch_article error for {url}: {e}")
        return None


# ---- 5. score_source_trust ----

TIER1_FACTCHECK = [
    "altnews.in",
    "boomlive.in",
    "factly.in",
    "politifact.com",
    "snopes.com",
]

TIER1_NEWS = [
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "pib.gov.in",
    "thehindu.com",
]


def score_source_trust(domain: str) -> str:
    """
    Static trust tier lookup for a domain.
    Returns: "tier1_factcheck", "tier1_news", "tier2_news", or "unknown"
    """
    domain = domain.lower().strip()
    if domain in TIER1_FACTCHECK:
        return "tier1_factcheck"
    for news in TIER1_NEWS:
        if domain.endswith(news) or news in domain:
            return "tier1_news"
    # tier2_news is a catch-all for known news outlets not in tier1
    # For this app, anything not tier1_factcheck or tier1_news is tier2
    return "tier2_news"


def extract_domain(url: str) -> str:
    """Extract domain from URL for trust scoring."""
    from urllib.parse import urlparse
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


# ---- Tool registry for LangChain ----

TOOLS_REGISTRY = {
    "rss_fact_check_search": rss_fact_check_search,
    "google_fact_check": google_fact_check,
    "ddgs_web_search": ddgs_web_search,
    "fetch_article": fetch_article,
    "score_source_trust": score_source_trust,
}