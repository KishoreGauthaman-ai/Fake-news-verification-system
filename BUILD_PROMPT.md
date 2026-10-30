Build a "Fact Check AI" — full-stack app, senior-engineer quality, that
looks and behaves like a real AI product (ChatGPT/Claude/Perplexity-style
layout), not a hackathon form.

STACK: FastAPI + LangChain (ChatGroq, model "llama-3.3-70b-versatile") on
the backend. React + TypeScript + Vite + Tailwind on the frontend. SQLite
for history — no ORM, raw sqlite3.

I'm providing two working, tested backend files as-is — do NOT rewrite
their internals, just import and use them:
  - fact_check_rss.py  → search_fact_check_feeds(query) -> list[dict]
  - database.py         → init_db(), save_verification(...), get_history(...),
                           get_verification(id), search_history(query), delete_verification(id)

BACKEND STRUCTURE:
  backend/
    main.py            — FastAPI app + routes
    agent.py            — LangChain agent (create_tool_calling_agent + AgentExecutor)
    tools.py             — @tool functions
    fact_check_rss.py     — provided
    database.py            — provided
    requirements.txt

TOOLS (backend/tools.py), in this priority order — encode explicitly in
the agent's system prompt:
1. rss_fact_check_search(query) — calls search_fact_check_feeds() from the
   provided module. Try this FIRST for any claim.
2. google_fact_check(query) — Google Fact Check Tools API, key from .env
   as GOOGLE_FACT_CHECK_API_KEY. Try SECOND if #1 returns nothing relevant.
3. ddgs_web_search(query) — ddgs library, top 6 results. FALLBACK only —
   the agent must not skip straight here without trying the fact-check
   tools first.
4. fetch_article(url) — trafilatura extraction, ~2000 char cap. Only when
   a snippet isn't enough to judge stance.
5. score_source_trust(domain) — static dict: tier1_factcheck (altnews.in,
   boomlive.in, factly.in, politifact.com, snopes.com), tier1_news
   (reuters.com, apnews.com, bbc.com, pib.gov.in, thehindu.com), tier2_news,
   unknown.

Agent rules: must use more than one tool before concluding — never verdict
off a single source. Hard limit 5 tool calls. If evidence conflicts or is
thin, verdict MUST be "Unverified" or "Misleading" with a neutral
explanation — never force True/False without solid, ideally multi-source
agreement. Return every tool call as agent_trace.

API ROUTES (backend/main.py):
  POST /verify
    body: { "claim": str }
    → runs the agent → on success, call save_verification() to persist
      the result → return { id, verdict, confidence, reasoning, sources,
      agent_trace, created_at }
  GET /history?limit=50&offset=0
    → returns get_history() — sidebar listing, newest first
  GET /history/{id}
    → returns get_verification(id), 404 if not found — instant, no agent
      re-run, this is how clicking a past sidebar entry works
  GET /history/search?q=...
    → returns search_history(q) — for the sidebar search box
  DELETE /history/{id}
    → returns delete_verification(id)
  Call init_db() once on FastAPI startup (@app.on_event("startup") or
  lifespan context manager).

FRONTEND — this MUST look like a real AI product, not a form. Layout:
  Fixed left sidebar (like ChatGPT/Claude):
    - "+ New Verification" button at top, clears main panel to input state
    - Search box (calls GET /history/search as the user types, debounced)
    - History list below, grouped by day ("Today", "Yesterday", older dates
      as actual date headers), each entry shows: small colored dot for
      verdict (green/red/amber/gray), truncated claim text (1 line,
      ellipsis), relative time. Clicking an entry calls GET /history/{id}
      and renders it in the main panel — instantly, no loading spinner
      needed since there's no agent call involved.
  Main panel:
    - Empty state: centered logo/title, ClaimInput (textarea + submit),
      3 example claim buttons below it
    - Result state: VerdictCard (colored badge, animated confidence bar,
      reasoning), SourceList (trust-tier badges, stance dots, links),
      AgentTrace (collapsible, monospace, shows tool-call sequence)
  On successful new verification: prepend the new entry to the sidebar
  history list locally (don't refetch the whole list from the server).

  Structure:
    src/api/client.ts        — typed fetch wrapper for all 5 endpoints
    src/types/index.ts         — shared types matching backend response shapes
    src/components/Sidebar.tsx
    src/components/HistoryItem.tsx
    src/components/ClaimInput.tsx
    src/components/VerdictCard.tsx
    src/components/SourceList.tsx
    src/components/AgentTrace.tsx
    src/components/ExampleClaims.tsx
    src/App.tsx               — layout shell, holds current view state
                                 (empty | loading | result), history state

  Design: dark theme, single restrained accent color, semantic verdict
  colors used only on badges/dots (not backgrounds). Skeleton loading
  state on submit. Real error boundary with retry on failed requests.
  Sidebar collapses to icon-only or hides on narrow viewports. Fully typed,
  no `any`.

CONFIG: .env with GROQ_API_KEY, GOOGLE_FACT_CHECK_API_KEY (placeholders).
requirements.txt: fastapi, uvicorn, langchain, langchain-groq, feedparser,
ddgs, trafilatura, beautifulsoup4, python-dotenv, pydantic. Frontend via
Vite React-TS + tailwindcss. CORS for localhost:5173 → localhost:8000.
fact_check_history.db should be gitignored. Give exact run commands and
ports for both.

Build backend first (verify /verify and /history routes work via /docs),
then frontend.
