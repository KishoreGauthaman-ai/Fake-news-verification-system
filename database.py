"""
database.py

SQLite persistence layer for the Fact Check Assistant's verification
history. One table, JSON columns for nested structures (sources,
agent_trace) — deliberately not normalized further, since those fields
are always read/written whole alongside their parent row.

Usage:
    from database import init_db, save_verification, get_history, get_verification

    init_db()  # call once at app startup
    row_id = save_verification(claim_text, verdict, confidence, reasoning, sources, agent_trace)
    recent = get_history(limit=50)
    one = get_verification(row_id)
"""

from __future__ import annotations

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "fact_check_history.db"


# ---------------------------------------------------------------------------
# Connection handling
# ---------------------------------------------------------------------------

@contextmanager
def _get_connection():
    """
    Context manager so every caller gets a connection that's guaranteed
    to close, even on exception. check_same_thread=False is safe here
    because FastAPI's default sync route handlers run in a threadpool —
    each call still gets its own connection instance, we're not sharing
    one connection across threads.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create the table and index if they don't exist yet. Call once at startup."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS verifications (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_text        TEXT NOT NULL,
                verdict           TEXT NOT NULL,
                confidence        INTEGER NOT NULL,
                reasoning         TEXT NOT NULL,
                sources_json      TEXT NOT NULL,
                agent_trace_json  TEXT NOT NULL,
                created_at        TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at
            ON verifications(created_at DESC)
        """)


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

def save_verification(
    claim_text: str,
    verdict: str,
    confidence: int,
    reasoning: str,
    sources: list[dict],
    agent_trace: list[dict],
) -> int:
    """Insert a completed verification result. Returns the new row id."""
    created_at = datetime.now(timezone.utc).isoformat()
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO verifications
                (claim_text, verdict, confidence, reasoning,
                 sources_json, agent_trace_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim_text,
                verdict,
                confidence,
                reasoning,
                json.dumps(sources, ensure_ascii=False),
                json.dumps(agent_trace, ensure_ascii=False),
                created_at,
            ),
        )
        return cursor.lastrowid


def delete_verification(row_id: int) -> bool:
    """Delete a single history entry. Returns True if a row was actually deleted."""
    with _get_connection() as conn:
        cursor = conn.execute("DELETE FROM verifications WHERE id = ?", (row_id,))
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "claim_text": row["claim_text"],
        "verdict": row["verdict"],
        "confidence": row["confidence"],
        "reasoning": row["reasoning"],
        "sources": json.loads(row["sources_json"]),
        "agent_trace": json.loads(row["agent_trace_json"]),
        "created_at": row["created_at"],
    }


def get_history(limit: int = 50, offset: int = 0) -> list[dict]:
    """
    Sidebar listing — newest first. Deliberately returns full rows (not a
    lightweight projection) since the frontend caches the click-through
    detail view from this same payload structure; keep it simple at this scale.
    """
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM verifications
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def get_verification(row_id: int) -> Optional[dict]:
    """Fetch a single past verification by id, or None if it doesn't exist."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM verifications WHERE id = ?", (row_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None


def search_history(query: str, limit: int = 20) -> list[dict]:
    """
    Simple substring search over claim_text for the sidebar search box.
    LIKE is plenty for a hackathon-scale table (hundreds to low thousands
    of rows) — FTS5 would be overkill here.
    """
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM verifications
            WHERE claim_text LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (f"%{query}%", limit),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
