"""
backend/main.py — FastAPI app + routes for Fact Check AI.

Routes:
  POST /verify    → runs agent, saves to DB, returns verdict JSON
  GET  /history   → list last 50 verifications
  GET  /history/{id} → single verification by id
  GET  /history/search?q=... → search claim_text
  DELETE /history/{id} → delete verification

Calls init_db() on startup via lifespan context manager.
Includes CORS for localhost:5173 → localhost:8000.
"""

from __future__ import annotations

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure backend/ is on sys.path no matter how uvicorn launches this app:
# - from inside backend/ with --reload (reload spawns a subprocess that
#   does NOT inherit the cwd path entry)
# - from the project root with PYTHONPATH=backend
# - as a package: uvicorn backend.main:app
BACKEND_DIR = str(Path(__file__).resolve().parent)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Load .env from cwd AND from the backend/ directory (works no matter
# where uvicorn is started from: project root or backend/)
load_dotenv()
load_dotenv(Path(__file__).parent / ".env")

# LLM config — Groq-hosted Qwen (change via GROQ_MODEL in .env)
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

try:
    from .database import init_db, save_verification, get_history, get_verification, search_history, delete_verification
except ImportError:
    from database import init_db, save_verification, get_history, get_verification, search_history, delete_verification

# Import agent setup (lazy to avoid loading LLM at import time)


class VerifyRequest(BaseModel):
    claim: str


class VerifyResponse(BaseModel):
    id: int
    verdict: str
    confidence: int
    reasoning: str
    sources: List[Dict[str, Any]]
    agent_trace: List[Dict[str, Any]]
    created_at: str


def _normalize_sources(
    raw: Any, agent_trace: List[Dict[str, Any]], max_sources: int = 6
) -> List[Dict[str, Any]]:
    """
    The model's Final Answer JSON may provide sources as dicts, as bare URL
    strings, or not at all. Always emit clean dicts so the pydantic response
    model and the frontend can rely on the shape. Falls back to mining the
    agent trace (tool observations) when the model gave nothing usable.
    """
    normalized: List[Dict[str, Any]] = []
    seen: set = set()

    def add(title: Any, url: Any, source: Any, stance: Any, tier: Any = "", score: Any = None) -> None:
        if len(normalized) >= max_sources:
            return
        url = str(url or "").strip()
        title = str(title or "").strip()
        key = url or title[:120]
        if not key or key in seen:
            return
        seen.add(key)
        item: Dict[str, Any] = {
            "title": title[:300],
            "url": url,
            "source": str(source or "")[:100],
            "stance": str(stance or "neutral"),
            "tier": str(tier or ""),
        }
        if score is not None:
            item["relevance_score"] = score
        normalized.append(item)

    # 1) Model-provided sources
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                add(
                    item.get("title") or item.get("source"),
                    item.get("url") or item.get("href"),
                    item.get("source"),
                    item.get("stance") or item.get("rating"),
                    item.get("tier"),
                    item.get("relevance_score"),
                )
            elif isinstance(item, str) and item.strip().startswith("http"):
                # bare URL string -> promote to a dict
                add("", item.strip(), "", "neutral")

    # 2) Nothing usable from the model -> mine the tool trace
    if not normalized:
        for step_info in agent_trace:
            try:
                step_json = json.loads(step_info.get("result", ""))
            except (json.JSONDecodeError, TypeError):
                continue
            for item in (step_json.get("results") or []):
                if isinstance(item, dict):
                    add(
                        item.get("title"),
                        item.get("url") or item.get("href"),
                        item.get("source"),
                        "neutral",
                        item.get("tier"),
                        item.get("relevance_score"),
                    )

    return normalized


# Create FastAPI app
app = FastAPI(
    title="Fact Check AI",
    description="AI-powered claim verification using LangChain agent with multi-source evidence.",
    version="1.0.0",
)

# CORS — allow any localhost/127.0.0.1 port (Vite dev server falls back to
# 5174, 5175… when 5173 is taken)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB at startup
@app.on_event("startup")
async def on_startup():
    init_db()


@app.post("/verify", response_model=VerifyResponse)
async def verify_claim(req: VerifyRequest):
    """
    Main verification endpoint.
    Runs the LangChain agent, saves result to SQLite, returns verdict JSON.
    """
    claim_text = req.claim.strip()
    if not claim_text:
        raise HTTPException(status_code=400, detail="Claim text is required")

    # Import agent lazily to avoid loading LLM at module import time
    try:
        from agent import create_agent
        from langchain_groq import ChatGroq
        from langchain.schema import SystemMessage, HumanMessage
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Failed to import agent modules: {e}")

    # Initialize LLM (Groq-hosted Qwen model)
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key or groq_api_key == "your_groq_key_here":
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not set in .env")

    try:
        llm = ChatGroq(
            groq_api_key=groq_api_key,
            model=GROQ_MODEL,
            temperature=0.1,
            max_tokens=900,  # Groq free tier: 1000 output tokens/min cap
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize LLM: {e}")

    # Create agent executor
    try:
        agent_executor = create_agent(llm)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {e}")

    # Build agent input with claim
    input_text = f"Claim to verify: {claim_text}\nPlease use the available tools in priority order to verify this claim. Provide a verdict with reasoning, sources used, and an agent trace of all tool calls made."

    # Run agent
    try:
        result = agent_executor.invoke({"input": input_text})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")

    # ---- Build agent_trace from intermediate steps (AgentAction objects) ----
    agent_trace: List[Dict[str, Any]] = []
    for action, observation in result.get("intermediate_steps", []):
        agent_trace.append({
            "name": getattr(action, "tool", "unknown"),
            "args": getattr(action, "tool_input", {}),
            "result": str(observation)[:500],
        })

    # ---- Parse the agent's final answer (ReAct wraps it in "Final Answer: ...") ----
    output = result.get("output", "")
    text = ""
    parsed: Dict[str, Any] = {}
    if isinstance(output, str):
        text = output.strip()
        if text.lower().startswith("final answer:"):
            text = text[len("final answer:"):].strip()
        # try to find a JSON object embedded in the text
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                parsed = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                parsed = {}
    else:
        parsed = output if isinstance(output, dict) else {}

    # ---- Fallback: agent loop stopped early without a Final Answer ----
    # (iteration/time limit, unrecoverable parse error) → make one direct
    # LLM call over the collected trace to produce the verdict JSON.
    if not parsed.get("verdict"):
        try:
            trace_lines = [
                f"- {s.get('name')}({s.get('args')}): {str(s.get('result'))[:400]}"
                for s in agent_trace
            ]
            fallback_prompt = (
                f"Claim: {claim_text}\n\n"
                f"Tool results from the fact-checking agent:\n" + "\n".join(trace_lines) +
                "\n\nBased ONLY on these results, respond with ONLY a JSON verdict:\n"
                '{"verdict": "True|False|Misleading|Unverified", "confidence": <0-100>, '
                '"reasoning": "<explanation>", "sources": []}'
            )
            fallback_resp = llm.invoke([HumanMessage(content=fallback_prompt)])
            fb_text = fallback_resp.content if isinstance(fallback_resp.content, str) else str(fallback_resp.content)
            fb_start, fb_end = fb_text.find("{"), fb_text.rfind("}")
            if fb_start != -1 and fb_end > fb_start:
                try:
                    fb_parsed = json.loads(fb_text[fb_start:fb_end + 1])
                    if fb_parsed.get("verdict"):
                        parsed = fb_parsed
                        if not parsed.get("reasoning"):
                            parsed["reasoning"] = fb_text[:500]
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"[verify] fallback verdict failed: {e}")

    verdict = parsed.get("verdict", "Unverified")
    # Normalize verdict casing to the four allowed values
    verdict_norm = str(verdict).strip().capitalize()
    if verdict_norm not in ("True", "False", "Misleading", "Unverified"):
        low = str(verdict).lower()
        if "true" in low or "correct" in low:
            verdict_norm = "True"
        elif "false" in low or "fake" in low:
            verdict_norm = "False"
        elif "misleading" in low:
            verdict_norm = "Misleading"
        else:
            verdict_norm = "Unverified"

    reasoning = parsed.get("reasoning") or (text if isinstance(output, str) and text else "No reasoning provided.")

    try:
        confidence = int(parsed.get("confidence", 50))
    except (TypeError, ValueError):
        confidence = 50
    confidence = max(0, min(100, confidence))

    # Sources: normalize whatever the model returned (dicts, bare URL
    # strings, or nothing) into clean dicts; fall back to mining the trace
    sources = _normalize_sources(parsed.get("sources"), agent_trace)

    # Save to database
    try:
        row_id = save_verification(
            claim_text=claim_text,
            verdict=verdict_norm,
            confidence=confidence,
            reasoning=str(reasoning),
            sources=sources,
            agent_trace=agent_trace,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save verification: {e}")

    # Return structured response
    response = VerifyResponse(
        id=row_id,
        verdict=verdict_norm,
        confidence=confidence,
        reasoning=str(reasoning),
        sources=sources,
        agent_trace=agent_trace,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    return response


@app.get("/history")
async def get_verification_history(limit: int = 50, offset: int = 0):
    """Get last N verifications, newest first."""
    try:
        results = get_history(limit=limit, offset=offset)
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {e}")


# NOTE: /history/search MUST be declared BEFORE /history/{id} — FastAPI
# matches routes in declaration order, and "/history/search" would
# otherwise be captured by the {id} path param (int parse → 422).
@app.get("/history/search")
async def search_verifications(q: str = Query(..., description="Search query for claim text"), limit: int = 20):
    """Search history by claim_text substring."""
    try:
        results = search_history(query=q, limit=limit)
        return {"results": results, "count": len(results), "query": q}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search history: {e}")


@app.get("/history/{id}")
async def get_single_verification(id: int):
    """Get a single verification by id — instant, no agent re-run."""
    try:
        result = get_verification(id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Verification {id} not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch verification: {e}")


@app.delete("/history/{id}")
async def delete_history_item(id: int):
    """Delete a verification by id."""
    try:
        deleted = delete_verification(id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Verification {id} not found")
        return {"deleted": True, "id": id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete verification: {e}")


@app.get("/")
async def root():
    return {"message": "Fact Check AI API running", "docs": "/docs", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)