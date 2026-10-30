# HackMint — Fact Check AI

Full-stack fact-check verification application with a multi-source agent, persistent history, and an interactive web interface.

---

## Architecture

| Layer | Stack | Details |
|---|---|---|
| **Backend** | FastAPI + LangChain | `main.py` (routes), `agent.py` (agent executor), `tools.py` (5 priority tools) |
| **LLM** | ChatGroq — `llama-3.3-70b-versatile` | Temperature 0.1, max 5 tool calls |
| **Database** | SQLite (raw `sqlite3`, no ORM) | `database.py` provides `init_db()`, `save_verification()`, `get_history()`, `get_verification()`, `search_history()`, `delete_verification()` |
| **History DB** | `fact_check_history.db` | Gitignored, single-table JSON columns |
| **RSS Feeds** | `fact_check_rss.py` (provided, unmodified) | Alt News, BOOM Live, Factly feeds |
| **Frontend** | React + TypeScript + Vite + Tailwind CSS | Dark theme, single restrained accent (`emerald`), no `any` types |

---

## Tools (Priority Order — Explicitly Encoded in Agent System Prompt)

1. `rss_fact_check_search(query)` — Indian fact-check feeds (`search_fact_check_feeds()` from `fact_check_rss.py`). **FIRST**.
2. `google_fact_check(query)` — Google Fact Check Tools API (key from `.env`). **SECOND**.
3. `ddgs_web_search(query)` — `ddgs` library, top 6 results. **FALLBACK only**.
4. `fetch_article(url)` — `trafilatura` extraction, ~2000 char cap.
5. `score_source_trust(url)` — Static trust tier: `tier1_factcheck` (altnews.in, boomlive.in, factly.in, politifact.com, snopes.com), `tier1_news` (reuters.com, apnews.com, bbc.com, pib.gov.in, thehindu.com), `tier2_news`, `unknown`.

---

## Agent Rules (Explicitly in System Prompt)

- Must use **more than one tool** before concluding — never verdict off a single source.
- Hard limit: **5 total tool calls** per claim.
- If evidence conflicts or is thin, verdict **MUST** be `"Unverified"` or `"Misleading"` with neutral explanation.
- Never force `True`/`False` without solid, ideally multi-source agreement.
- Return every tool call as `agent_trace` (collapsible, monospace, shows sequence).

---

## API Routes (`backend/main.py`)

| Endpoint | Method | Description |
|---|---|---|
| `/verify` | POST | `body: { claim: string }` → runs agent → saves to DB → returns `VerifyResponse` |
| `/history` | GET | `?limit=50&offset=0` → newest first |
| `/history/{id}` | GET | Single verification by ID — instant, no agent re-run |
| `/history/search` | GET | `?q=...` → substring search over `claim_text` |
| `/history/{id}` | DELETE | Delete verification by ID |
| `/` | GET | Health check / API info |
| `/docs` | GET | Auto-generated OpenAPI docs |

---

## Configuration (`.env`)

```
GROQ_API_KEY=<your valid Groq key — the app fails with 401 "Invalid API Key" if wrong>
# Optional — override the LLM (default: qwen/qwen3-32b)
GROQ_MODEL=qwen/qwen3-32b
```

Both keys load automatically at backend startup via `load_dotenv()`.

---

## Running the Application

### Prerequisites

- Python 3.10+ with `pip`
- Node.js 18+ with `npm`
- (Optional) `python-dotenv`, `uvicorn`, `fastapi`, `langchain`, `langchain-groq`

### 1. Install Backend Dependencies

```bash
pip install -r backend/requirements.txt
```

Requirements: `fastapi`, `uvicorn`, `langchain`, `langchain-groq`, `feedparser`, `ddgs`, `trafilatura`, `beautifulsoup4`, `python-dotenv`, `pydantic`.

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 3. Start the Backend

```bash
cd backend
python3 -m uvicorn main:app --reload --port 8000
```

That's it — `main.py` handles everything: it adds `backend/` to `sys.path` itself, and auto-loads `.env` (Groq key, Google key, `GROQ_MODEL`). The SQLite history DB lives at `backend/fact_check_history.db`.

> When running from inside `backend/`, use the module reference `main:app` rather than the file path.

### 4. Start the Frontend

In a separate terminal:

```bash
cd frontend
npm run dev
```

The application runs at `http://localhost:5173`.

### 5. Verification

```bash
# Backend health
curl http://localhost:8000/
# Expected: {"message":"Fact Check AI API running","docs":"/docs","version":"1.0.0"}

# API docs
open http://localhost:8000/docs

# History endpoint
curl http://localhost:8000/history

# Submit a verification (test — may return 401 if Groq key is invalid for production)
curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d '{"claim":"COVID-19 vaccines contain microchips"}'
```



## Interface Layout

- **Sidebar** (collapses/hides on narrow viewports):
  - `+ New Verification` button (resets main panel to input state)
  - Search box (`GET /history/search`, debounced)
  - History list grouped by day (`Today`, `Yesterday`, date headers)
  - Each entry: colored verdict dot + truncated claim + relative time
- **Main panel**:
  - Empty state: centered logo/title, claim input, example claim buttons
  - Loading state: skeleton/spinner on submit
  - Result state: verdict badge with animated confidence bar, reasoning, source list (trust-tier badges, stance dots, links), agent trace (collapsible monospace tool sequence)
- On new verification success: entry prepended to sidebar locally (no full refetch)

---

## Design Rules (Enforced in Code)

- Dark theme (`#020617` base), single restrained accent (`emerald` / `#34d399`)
- Semantic verdict colors only on badges/dots (not backgrounds)
- Skeleton loading on submit
- Real error boundary with retry
- Fully typed TypeScript — no `any`
- Mobile responsive (`md:` breakpoints for sidebar)
- Sidebar collapses to hidden (`-translate-x-full`) on mobile until toggled

---

## Security & Audit

- `sentry` scan performed: no `eval`, `exec`, `os.system`, or dangerous patterns found in backend
- `.env` is gitignored (`.gitignore` excludes `.env` and `fact_check_history.db`)
- CORS configured for `localhost:5173` → `localhost:8000`

---

## Verification & Testing

- Backend runs successfully: `main.py` handles routes, CORS, and startup DB initialization
- `/docs` endpoint accessible for OpenAPI documentation
- `/verify` executes through the agent pipeline (multi-source evidence gathering)
- `/history` and `/history/search` return correct results; `/history/{id}` provides instant cached responses
- Frontend loads at `http://localhost:5173`; build passes with 0 TypeScript errors
- Agent reference documentation (`AGENTS.md`, `BUILD_PROMPT.md`, `BUILD_ARCHICTURE.md`) maintained

---

## File Map

```
HACKMINT/
├── AGENTS.md              # Architecture, workflows, skills, checklist
├── BUILD_PROMPT.md        # Original core idea
├── BUILD_ARCHICTURE.md    # Schema, workflow, UI layout
├── .env                   # GROQ_API_KEY, GOOGLE_FACT_CHECK_API_KEY
├── .gitignore             # Excludes fact_check_history.db, .env, node_modules
├── backend/
│   ├── __init__.py
│   ├── main.py            # FastAPI app (6 routes + CORS + startup DB init)
│   ├── agent.py           # LangChain agent (create_react_agent + AgentExecutor)
│   ├── tools.py           # 5 priority tool functions
│   ├── requirements.txt
│   ├── database.py        # SQLite persistence (provided, unmodified)
│   └── fact_check_rss.py  # RSS feed aggregator (provided, unmodified)
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   ├── components.json    # shadcn/ui config
│   ├── src/
│   │   ├── App.tsx        # Layout shell (sidebar + main panel)
│   │   ├── main.tsx
│   │   ├── index.css      # Tailwind + dark base
│   │   ├── types/
│   │   │   └── index.ts   # Shared interfaces (no any)
│   │   ├── api/
│   │   │   └── client.ts  # Typed fetch wrapper (5 endpoints)
│   │   ├── components/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── HistoryItem.tsx
│   │   │   ├── ClaimInput.tsx
│   │   │   ├── VerdictCard.tsx
│   │   │   ├── SourceList.tsx
│   │   │   ├── AgentTrace.tsx
│   │   │   └── ExampleClaims.tsx
│   │   └── lib/
│   │       └── utils.ts    # shadcn cn() helper
```

---

## Commands Summary

```bash
# Backend
PYTHONPATH=backend python3 -m uvicorn backend/main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
npm --prefix frontend run dev

# Verify
curl http://localhost:8000/
curl http://localhost:5173/
```
