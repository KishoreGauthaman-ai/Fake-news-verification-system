# HackMint - Fact Check AI Agent

## Overview
Full-stack "Fact Check AI" application looking and behaving like a real AI product (ChatGPT/Claude/Perplexity-style layout), built with senior-engineer quality.

## Architecture

### Backend (FastAPI + LangChain)
- **Framework**: FastAPI + LangChain
- **LLM**: ChatGroq model "llama-3.3-70b-versatile"
- **Database**: SQLite (raw sqlite3, no ORM)
- **History DB**: `fact_check_history.db` (gitignored)
- **Port**: 8000

### Frontend (React + TypeScript + Vite + Tailwind)
- **Framework**: React + TypeScript + Vite
- **Styling**: Tailwind CSS
- **Port**: 5173
- **CORS**: localhost:5173 → localhost:8000

## Core Workflows

### 1. Submit New Verification
1. User enters claim in ClaimInput textarea
2. Frontend calls `POST /verify` 
3. LangChain agent runs with tool execution priority:
   - **FIRST**: `rss_fact_check_search()` — calls `search_fact_check_feeds()` from `fact_check_rss.py`
   - **SECOND**: `google_fact_check()` — Google Fact Check Tools API (key from `.env`)
   - **THIRD**: `ddgs_web_search()` — ddgs library, top 6 results (FALLBACK)
   - **FOURTH**: `fetch_article()` — trafilatura extraction (~2000 char cap)
   - **FIFTH**: `score_source_trust()` — static trust tier dict
4. Agent produces Verdict JSON with `agent_trace`
5. Response returns `{ id, verdict, confidence, reasoning, sources, agent_trace, created_at }`
6. Frontend prepends new entry to sidebar history locally

### 2. Browse History
- **Sidebar loads on app start**: `GET /history?limit=50&offset=0` — renders as clickable list, newest first
- **Search**: `GET /history/search?q=...` — debounced as user types
- **Click entry**: `GET /history/{id}` — renders stored result INSTANTLY (no agent re-run)
- **Delete**: `DELETE /history/{id}`

### 3. UI Layout (ChatGPT/Claude/Perplexity pattern)
- **Fixed left sidebar**:
  - "+ New Verification" button at top (clears main panel to input state)
  - Search box (calls `GET /history/search` as user types, debounced)
  - History list below, grouped by day ("Today", "Yesterday", older dates as actual date headers)
  - Each entry shows: small colored dot for verdict (green/red/amber/gray), truncated claim text (1 line, ellipsis), relative time
- **Main panel**:
  - Empty state: centered logo/title, ClaimInput (textarea + submit), 3 example claim buttons
  - Result state: VerdictCard (colored badge, animated confidence bar, reasoning), SourceList (trust-tier badges, stance dots, links), AgentTrace (collapsible, monospace, shows tool-call sequence)
- **On successful new verification**: prepend the new entry to the sidebar history list locally (don't refetch the whole list)

## Agent Rules (explicitly in system prompt)
- Must use more than one tool before concluding — never verdict off a single source
- Hard limit 5 tool calls
- If evidence conflicts or is thin, verdict MUST be "Unverified" or "Misleading" with neutral explanation
- Never force True/False without solid, ideally multi-source agreement
- Return every tool call as `agent_trace`

## API Routes

| Endpoint | Method | Description |
|---|---|---|
| `/verify` | POST | Runs the agent on claim → returns verdict JSON |
| `/history` | GET | Returns last 50 verifications (newest first) |
| `/history/{id}` | GET | Returns single verification by id (404 if not found) |
| `/history/search` | GET | Search history by claim_text substring |
| `/history/{id}` | DELETE | Deletes verification by id |

## Configuration

### `.env` file
```
GROQ_API_KEY=your_groq_key_here
GOOGLE_FACT_CHECK_API_KEY=your_google_key_here
```

### `requirements.txt` (Backend)
```
fastapi
uvicorn
langchain
langchain-groq
feedparser
ddgs
trafilatura
beautifulsoup4
python-dotenv
pydantic
```

### Frontend dependencies (via Vite)
- React, TypeScript, Tailwind CSS

## Run Commands

```bash
# Start backend
cd backend
python -m uvicorn main:app --reload --port 8000

# Start frontend  
cd frontend
npm run dev
# App available at http://localhost:5173
```

## Skills & MCP Servers Usage

### Skills (to be used during development)

| Skill | When to Use |
|---|---|
| `context7-mcp` | Fetch current library/framework API docs (e.g., FastAPI, LangChain, React, Tailwind) |
| `serena` | Code intelligence: find symbols, references, implementations, navigate codebase |
| `playwright` | UI testing: browser flows, click user flows, capture screenshots, analyze UI regressions |
| `shadcn` | Add/shadcn/ui components when building React frontend |
| `graphify` | Codebase/architecture questions, code relationships, review impact on changed files |
| `headroom` | Compress large outputs to save context window |
| `ai-sdk` | Questions about AI SDK functions (generateText, streamText, tool calling, structured output) |
| `research` | Investigate topics against high-trust primary sources |

### MCP Servers (always enabled for this project)

| MCP Server | Purpose |
|---|---|
| `serena` | Symbol-aware code navigation, find declarations, references, implementations |
| `neo4j` | Graph database queries if needed for analyzing code relationships |
| `docker-mcp` | Docker container management (if running any services) |
| `context7-mcp` | Current library/API documentation fetching |
| `graphify` | Knowledge graph management and codebase understanding |
| `headroom` | Context window compression for large file outputs |

## Things to Complete (Checklist)

- [x] Backend structure (database.py, fact_check_rss.py provided)
- [ ] Create `backend/main.py` with FastAPI routes
- [ ] Create `backend/agent.py` with LangChain agent setup
- [ ] Create `backend/tools.py` with tool functions in priority order
- [ ] Create `.env` configuration file
- [ ] Create `requirements.txt` for backend
- [ ] Create frontend `src/` directory structure (Vite React-TS + Tailwind)
- [ ] Create all frontend components: Sidebar, HistoryItem, ClaimInput, VerdictCard, SourceList, AgentTrace, ExampleClaims
- [ ] Create `src/App.tsx` layout shell
- [ ] Create `src/api/client.ts` typed fetch wrapper
- [ ] Create `src/types/index.ts` shared types
- [ ] Implement `POST /verify` end-to-end flow
- [ ] Implement history browsing and search
- [ ] Implement instant click-through from sidebar (GET /history/{id})
- [ ] Add skeleton loading state on submit
- [ ] Add real error boundary with retry on failed requests
- [ ] Test backend runs and verify /verify and /history routes work via /docs
- [ ] Verify frontend renders correctly at localhost:5173
- [ ] Ensure fact_check_history.db is gitignored

## Code Standards
- No `any` types in TypeScript/frontend
- Fully typed — all interfaces defined
- Dark theme, single restrained accent color
- Semantic verdict colors used only on badges/dots (not backgrounds)
- Skeleton loading state on submit
- Error boundary with retry on failed requests
- Sidebar collapses to icon-only or hides on narrow viewports
- Mobile-responsive design