/**
 * src/App.tsx — Layout shell: sidebar + main content area.
 * GSAP-choreographed entrances for hero and result states.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Sidebar } from "./components/Sidebar";
import { ClaimInput } from "./components/ClaimInput";
import { VerdictCard } from "./components/VerdictCard";
import { SourceList } from "./components/SourceList";
import { AgentTrace } from "./components/AgentTrace";
import { ExampleClaims } from "./components/ExampleClaims";
import { ResultSkeleton } from "./components/ResultSkeleton";
import { api } from "./api/client";
import type { Verification } from "./types";

gsap.registerPlugin(useGSAP, ScrollTrigger);

type ViewState = "empty" | "loading" | "result";

export default function App() {
  const [view, setView] = useState<ViewState>("empty");
  const [history, setHistory] = useState<Verification[]>([]);
  const [currentResult, setCurrentResult] = useState<Verification | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastClaim, setLastClaim] = useState<string>("");

  const rootRef = useRef<HTMLDivElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getHistory(50, 0).then((res) => setHistory(res.results)).catch(console.error);
  }, []);

  const handleNewVerification = useCallback(() => {
    setView("empty");
    setCurrentResult(null);
    setError(null);
  }, []);

  const handleSelectHistory = useCallback(async (entry: Verification) => {
    setCurrentResult(entry);
    setView("result");
    setError(null);
    try {
      const full = await api.getVerification(entry.id);
      setCurrentResult(full);
    } catch (e) {
      console.error("Failed to refresh entry:", e);
    }
  }, []);

  const handleSubmit = useCallback(
    async (claim: string) => {
      setLoading(true);
      setView("loading");
      setError(null);
      setLastClaim(claim);
      try {
        const res = await api.verify({ claim });
        setCurrentResult(res);
        setHistory((prev) => [res, ...prev]);
        setView("result");
      } catch (e) {
        console.error("Verification failed:", e);
        setError(e instanceof Error ? e.message : "Verification failed. Is the backend running on port 8000?");
        setView("empty");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Hero entrance — staggered blur-rise cascade (Attention)
  useGSAP(
    () => {
      if (view !== "empty") return;
      gsap.fromTo(
        "[data-hero]",
        { y: 28, opacity: 0, filter: "blur(10px)" },
        {
          y: 0,
          opacity: 1,
          filter: "blur(0px)",
          duration: 1.1,
          stagger: 0.09,
          ease: "power3.out",
          clearProps: "filter",
        }
      );
    },
    { scope: rootRef, dependencies: [view, error] }
  );

  // Result entrance — cascading reveal as one timeline (Interest)
  useGSAP(
    () => {
      if (view !== "result" || !currentResult) return;
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
      tl.fromTo("[data-reveal]", { y: 32, opacity: 0 }, { y: 0, opacity: 1, duration: 0.9, stagger: 0.14 });
      const badge = resultRef.current?.querySelector("[data-reveal-badge]");
      if (badge) {
        tl.fromTo(
          badge,
          { y: -14, opacity: 0, scale: 0.92 },
          { y: 0, opacity: 1, scale: 1, duration: 0.6, ease: "back.out(1.6)" },
          0.1
        );
      }
    },
    { scope: resultRef, dependencies: [view, currentResult] }
  );

  return (
    <div ref={rootRef} className="min-h-dvh bg-[#050505] text-neutral-100 font-sans antialiased">
      {/* Ambient background — radial mesh + hairline horizon */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_75%_-10%,_rgba(52,211,153,0.06),_transparent_55%),radial-gradient(ellipse_at_-10%_110%,_rgba(255,255,255,0.025),_transparent_45%)]" />
      </div>

      {/* Film grain — fixed, pointer-events-none */}
      <div className="grain" aria-hidden="true" />

      <div className="relative z-10 flex min-h-dvh">
        <Sidebar
          history={history}
          onSelect={handleSelectHistory}
          onNew={handleNewVerification}
          selectedId={currentResult?.id}
        />

        <main className="flex-1 min-w-0 min-h-dvh overflow-x-hidden w-full max-w-full">
          <div className="max-w-3xl mx-auto px-4 md:px-12 pt-28 md:pt-40 pb-28 md:pb-40 min-h-dvh flex flex-col">
            {/* ---- Empty state — editorial split hero ---- */}
            {view === "empty" && (
              <div className="flex-1">
                <div data-hero>
                  <span className="inline-block rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-medium bg-white/[0.05] ring-1 ring-white/10 text-neutral-400">
                    Evidence-first verification
                  </span>
                </div>

                <h1
                  data-hero
                  className="mt-7 text-5xl md:text-7xl font-semibold tracking-[-0.045em] leading-[1.02] text-neutral-50 text-balance"
                >
                  Check if it&rsquo;s&nbsp;true.
                </h1>

                <p data-hero className="mt-6 text-neutral-400 text-base md:text-lg max-w-[46ch] leading-relaxed text-pretty">
                  Paste any claim or headline. The agent checks fact-check feeds, the web,
                  and trusted sources — then shows its work.
                </p>

                <p data-hero className="mt-5 font-mono text-[11px] text-neutral-600 tabular-nums tracking-tight">
                  5 tools · 5 calls max · full agent trace
                </p>

                {/* Error banner with retry */}
                {error && (
                  <div data-hero className="mt-9 max-w-2xl rounded-[1.5rem] p-1.5 bg-rose-500/[0.06] ring-1 ring-rose-400/20">
                    <div className="rounded-[calc(1.5rem-0.375rem)] bg-[#0a0a0b] px-4 py-3 flex items-start gap-3">
                      <span className="w-1.5 h-1.5 mt-1.5 rounded-full bg-rose-400 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-rose-200">Verification failed</p>
                        <p className="text-[11px] text-rose-300/60 mt-0.5 break-words">{error}</p>
                      </div>
                      {lastClaim && (
                        <button
                          onClick={() => handleSubmit(lastClaim)}
                          className="text-[11px] font-semibold text-rose-200 hover:text-rose-100 underline underline-offset-2 shrink-0 focus-visible:outline-none"
                        >
                          Retry
                        </button>
                      )}
                    </div>
                  </div>
                )}

                <div data-hero className="mt-12">
                  <ClaimInput onSubmit={handleSubmit} loading={loading} />
                </div>

                <div data-hero className="mt-8">
                  <ExampleClaims onSelect={handleSubmit} />
                </div>
              </div>
            )}

            {/* ---- Loading — double-bezel skeleton ---- */}
            {view === "loading" && <ResultSkeleton claim={lastClaim} />}

            {/* ---- Result — GSAP-cascading bezels ---- */}
            {view === "result" && currentResult && (
              <div ref={resultRef} className="flex-1">
                <div data-reveal className="mb-10">
                  <button
                    onClick={handleNewVerification}
                    className="text-xs text-neutral-500 hover:text-emerald-300 transition-colors duration-500 ease-fluid font-medium focus-visible:outline-none"
                  >
                    ← New verification
                  </button>
                </div>

                <div data-reveal>
                  <VerdictCard verification={currentResult} />
                </div>

                {currentResult.sources && currentResult.sources.length > 0 && (
                  <div data-reveal className="-mt-3">
                    <SourceList sources={currentResult.sources} />
                  </div>
                )}

                <div data-reveal>
                  <AgentTrace trace={currentResult.agent_trace || []} />
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
