single-table SQLite file is the right call for this: zero setup, no server to run, file-based so it survives restarts, and it's genuinely production-reasonable for a read-light/write-light app like this. Skip SQLAlchemy too — for one table with four operations, raw sqlite3 with a thin wrapper class is less code, easier to debug live during judging, and has zero ORM magic to explain if a judge asks "walk me through your stack."

Schema
sql
CREATE TABLE verifications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_text    TEXT NOT NULL,
    verdict       TEXT NOT NULL,          -- True | False | Misleading | Unverified
    confidence    INTEGER NOT NULL,       -- 0-100
    reasoning     TEXT NOT NULL,
    sources_json  TEXT NOT NULL,          -- JSON-serialized list[Source]
    agent_trace_json TEXT NOT NULL,       -- JSON-serialized list[AgentStep]
    created_at    TEXT NOT NULL           -- ISO 8601 UTC
);

CREATE INDEX idx_created_at ON verifications(created_at DESC);

One table, JSON columns for the nested structures (sources, agent_trace) rather than normalizing into child tables — that's the correct tradeoff at this scale: you never query into those fields, you only ever read/write them whole alongside their parent row.

Updated end-to-end workflow
App loads
  → Sidebar: GET /history (last 50, newest first) → renders as clickable list
  → Main panel: shows ClaimInput (empty state)

User submits a claim
  → POST /verify
      → LangChain agent runs (rss_fact_check → google_fact_check → ddgs → fetch_article)
      → Verdict JSON produced
      → INSERT into SQLite → get new row id
      → Response returns { id, verdict, confidence, reasoning, sources, agent_trace }
  → Frontend renders VerdictCard in main panel
  → New entry PREPENDED to sidebar history (no full refetch needed)

User clicks a past entry in sidebar
  → GET /history/{id}
  → Main panel renders that stored result INSTANTLY (no agent re-run,
    no API calls — this is a great demo moment: "look, it's cached and
    instant for anything I've already checked")

User clicks "New Verification"
  → Main panel resets to empty ClaimInput, sidebar stays as-is
UI — "regular AI website" layout

This means the ChatGPT / Claude / Perplexity pattern: fixed left sidebar for history + a "New Verification" button, main content area that's either an empty input state or a result view. That's instantly recognizable to any judge as "a real AI product," not a hackathon form.

┌─────────────┬──────────────────────────────────────┐
│  + New       │                                      │
│  Verification│         [Logo] Fact Check AI         │
│─────────────│                                       │
│ 🔍 Search... │   ┌────────────────────────────────┐ │
│─────────────│   │  Paste a claim or headline...   │ │
│ Today        │   │                          [→]    │ │
│ ⚠ Claim A    │   └────────────────────────────────┘ │
│ ✅ Claim B    │                                      │
│              │   Try: [Example 1] [Example 2]       │
│ Yesterday    │                                      │
│ ❌ Claim C    │  ── or, after submit ──              │
│              │  ┌────────────────────────────────┐ │
│              │  │  ✅ TRUE          92% confident │ │
│              │  │  [reasoning...]                 │ │
│              │  │  ▸ Sources (4)                  │ │
│              │  │  ▸ How I checked this (3 steps)  │ │
│              │  └────────────────────────────────┘ │
└─────────────┴──────────────────────────────────────┘

Sidebar entries show a small verdict-colored dot + truncated claim text + relative date, grouped by day — exactly like chat history groupings in Claude/ChatGPT. That grouping-by-day detail is a small thing that reads as senior-level UI polish.
