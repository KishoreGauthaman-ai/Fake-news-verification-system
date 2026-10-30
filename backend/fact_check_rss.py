"""
fact_check_rss.py

Modular utility that aggregates Indian fact-checking RSS feeds (Alt News,
BOOM Live, Factly) into a clean, deduplicated, JSON-serializable stream.

Design notes:
- RSS feeds only expose the *most recent* N articles, not a searchable
  archive. So "search" here means: pull recent entries, then keyword-score
  them against the claim to find relevant ones. This is NOT a full-text
  search engine — it's a fast, free relevance filter over recent fact-checks.
- Every feed fetch is isolated in its own try/except so one broken/slow
  feed never kills the others.
- Dedup is by URL first (canonical), then by a (title, source) fallback
  in case the same story is mirrored across feeds with tracking params
  in the URL.
- A small in-memory TTL cache avoids re-hitting the feeds on every
  agent tool call during a demo/dev session.

Usage as a module:
    from fact_check_rss import search_fact_check_feeds
    results = search_fact_check_feeds("Kangana Ranaut middle finger video")

Usage as a CLI:
    python fact_check_rss.py "some claim text"
"""

from __future__ import annotations

import json
import sys
import time
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional

import feedparser

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FEEDS: dict[str, str] = {
    "Alt News": "https://www.altnews.in/feed/",
    "BOOM Live": "https://www.boomlive.in/feed",
    "Factly": "https://factly.in/feed/",
}

FEED_TIMEOUT_SECONDS = 6
CACHE_TTL_SECONDS = 15 * 60  # 15 min — feeds don't change fast enough to need less
MAX_ENTRIES_PER_FEED = 40  # how many recent items to pull before filtering
MIN_RELEVANCE_SCORE = 1  # at least one meaningful keyword overlap to be considered a match


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FactCheckEntry:
    title: str
    source: str
    url: str
    published: Optional[str]  # ISO 8601 string, or None if unparseable
    summary: str
    relevance_score: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal cache (raw feed entries, keyed by feed name — not by query,
# since the expensive part is the network fetch, not the filtering)
# ---------------------------------------------------------------------------

_feed_cache: dict[str, tuple[float, list[FactCheckEntry]]] = {}


def _cache_get(feed_name: str) -> Optional[list[FactCheckEntry]]:
    cached = _feed_cache.get(feed_name)
    if cached is None:
        return None
    fetched_at, entries = cached
    if time.time() - fetched_at > CACHE_TTL_SECONDS:
        return None
    return entries


def _cache_set(feed_name: str, entries: list[FactCheckEntry]) -> None:
    _feed_cache[feed_name] = (time.time(), entries)


# ---------------------------------------------------------------------------
# Fetch + parse
# ---------------------------------------------------------------------------

def _parse_published(entry) -> Optional[str]:
    """Normalize whatever date field feedparser found into ISO 8601 UTC."""
    for field in ("published_parsed", "updated_parsed"):
        struct_time = getattr(entry, field, None)
        if struct_time:
            try:
                dt = datetime.fromtimestamp(time.mktime(struct_time), tz=timezone.utc)
                return dt.isoformat()
            except (ValueError, OverflowError):
                continue
    return None


def _fetch_single_feed(source_name: str, feed_url: str) -> list[FactCheckEntry]:
    """
    Fetch and parse one feed. Never raises — returns [] on any failure
    so a broken feed doesn't take down the others.
    """
    cached = _cache_get(source_name)
    if cached is not None:
        return cached

    entries: list[FactCheckEntry] = []
    try:
        parsed = feedparser.parse(feed_url, request_headers={
            "User-Agent": "Mozilla/5.0 (compatible; FactCheckAggregator/1.0)"
        })

        # feedparser sets bozo=1 on malformed XML but often still recovers
        # partial entries — only bail out if there's truly nothing usable.
        if getattr(parsed, "bozo", 0) and not parsed.entries:
            print(f"[fact_check_rss] '{source_name}' feed unparseable, skipping.",
                  file=sys.stderr)
            return []

        for raw_entry in parsed.entries[:MAX_ENTRIES_PER_FEED]:
            try:
                title = getattr(raw_entry, "title", "").strip()
                url = getattr(raw_entry, "link", "").strip()
                summary_raw = getattr(raw_entry, "summary", "") or getattr(raw_entry, "description", "")
                summary = _strip_html(summary_raw)[:400]

                if not title or not url:
                    continue  # broken entry, skip it — don't crash the whole feed

                entries.append(FactCheckEntry(
                    title=title,
                    source=source_name,
                    url=url,
                    published=_parse_published(raw_entry),
                    summary=summary,
                ))
            except Exception as e:
                # One malformed <item> should never kill the rest of the feed
                print(f"[fact_check_rss] skipped a broken entry in '{source_name}': {e}",
                      file=sys.stderr)
                continue

    except Exception as e:
        print(f"[fact_check_rss] failed to fetch '{source_name}' ({feed_url}): {e}",
              file=sys.stderr)
        return []

    _cache_set(source_name, entries)
    return entries


def _strip_html(text: str) -> str:
    """Cheap HTML tag stripper — avoids pulling in a full HTML parser for
    what's usually a one-paragraph RSS summary."""
    import re
    clean = re.sub(r"<[^>]+>", "", text)
    return " ".join(clean.split())


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------

def _dedupe(entries: list[FactCheckEntry]) -> list[FactCheckEntry]:
    seen_urls: set[str] = set()
    seen_fingerprints: set[str] = set()
    deduped: list[FactCheckEntry] = []

    for entry in entries:
        canonical_url = entry.url.split("?")[0].rstrip("/")
        if canonical_url in seen_urls:
            continue

        # fallback fingerprint: same title + source is almost certainly
        # the same story even if the URL differs (tracking params, mirrors)
        fingerprint = hashlib.md5(
            f"{entry.title.lower().strip()}|{entry.source}".encode()
        ).hexdigest()
        if fingerprint in seen_fingerprints:
            continue

        seen_urls.add(canonical_url)
        seen_fingerprints.add(fingerprint)
        deduped.append(entry)

    return deduped


# ---------------------------------------------------------------------------
# Relevance scoring (keyword overlap — cheap, no embeddings needed for this scale)
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "in", "on", "at",
    "to", "for", "and", "or", "did", "does", "has", "have", "had", "with",
    "claim", "claims", "claimed", "video", "photo", "image", "news",
}


def _tokenize(text: str) -> set[str]:
    import re
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def _score_relevance(query_tokens: set[str], entry: FactCheckEntry) -> int:
    entry_tokens = _tokenize(entry.title) | _tokenize(entry.summary)
    return len(query_tokens & entry_tokens)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_fact_check_feeds(query: str, max_results: int = 5) -> list[dict]:
    """
    Main entry point. Pulls recent entries from all configured feeds,
    dedupes, scores relevance against `query`, and returns the top matches
    as plain dicts (JSON-serializable) sorted by relevance then recency.

    Returns an empty list if nothing relevant was found — callers (e.g.
    an agent tool) should treat that as "no Indian fact-check coverage,
    fall back to general web search."
    """
    all_entries: list[FactCheckEntry] = []
    for source_name, feed_url in FEEDS.items():
        all_entries.extend(_fetch_single_feed(source_name, feed_url))

    deduped = _dedupe(all_entries)

    query_tokens = _tokenize(query)
    scored = []
    for entry in deduped:
        score = _score_relevance(query_tokens, entry)
        if score >= MIN_RELEVANCE_SCORE:
            scored.append(FactCheckEntry(**{**entry.to_dict(), "relevance_score": score}))

    scored.sort(
        key=lambda e: (e.relevance_score, e.published or ""),
        reverse=True,
    )

    return [e.to_dict() for e in scored[:max_results]]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    query_arg = " ".join(sys.argv[1:]) or "test claim"
    results = search_fact_check_feeds(query_arg)
    print(json.dumps(results, indent=2, ensure_ascii=False))
