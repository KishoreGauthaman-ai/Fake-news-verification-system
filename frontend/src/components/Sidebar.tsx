/**
 * src/components/Sidebar.tsx — Sticky desktop column + mobile fluid-island
 * bar. shadcn Input/ScrollArea/Button themed to the OLED design.
 */

import { useState, useCallback } from "react";
import { Search, Plus } from "lucide-react";
import { api } from "../api/client";
import type { Verification } from "../types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

interface SidebarProps {
  history: Verification[];
  onSelect: (v: Verification) => void;
  onNew: () => void;
  selectedId?: number;
}

function groupByDay(items: Verification[]): { label: string; entries: Verification[] }[] {
  const today = new Date().toISOString().split("T")[0];
  const yesterday = new Date(Date.now() - 86400000).toISOString().split("T")[0];
  const groups = new Map<string, Verification[]>();
  for (const item of items) {
    const date = (item.created_at || "").split("T")[0];
    let label = date;
    if (date === today) label = "Today";
    if (date === yesterday) label = "Yesterday";
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label)!.push(item);
  }
  return Array.from(groups.entries()).map(([label, entries]) => ({ label, entries }));
}

function verdictDot(v: string): string {
  switch (v) {
    case "True": return "bg-emerald-400";
    case "False": return "bg-rose-400";
    case "Misleading": return "bg-amber-400";
    default: return "bg-neutral-500";
  }
}

function verdictBadge(v: string): string {
  switch (v) {
    case "True": return "bg-emerald-400/10 text-emerald-300";
    case "False": return "bg-rose-400/10 text-rose-300";
    case "Misleading": return "bg-amber-400/10 text-amber-300";
    default: return "bg-white/[0.06] text-neutral-400";
  }
}

function Stagger({ on, delay, children }: { on: boolean; delay: number; children: React.ReactNode }) {
  if (!on) return <>{children}</>;
  return (
    <div className="animate-rise" style={{ animationDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}

function SidebarContent({
  history, onSelect, onNew, selectedId, onNavigate, stagger = false,
}: SidebarProps & { onNavigate: () => void; stagger?: boolean }) {
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Verification[] | null>(null);
  const [searching, setSearching] = useState(false);

  const handleSearch = useCallback(async (q: string) => {
    setQuery(q);
    if (!q.trim()) { setSearchResults(null); return; }
    setSearching(true);
    try {
      const res = await api.searchHistory(q, 20);
      setSearchResults(res.results);
    } catch (e) {
      console.error("Search error:", e);
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  const display = searchResults !== null ? searchResults : history;
  const groups = groupByDay(display);

  return (
    <>
      {/* Header */}
      <Stagger on={stagger} delay={0}>
        <div className="px-5 pt-5 pb-4 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-[0.6rem] bg-emerald-400 flex items-center justify-center shadow-[0_4px_16px_-4px_rgba(52,211,153,0.5)] shrink-0">
              <span className="text-neutral-950 font-bold text-sm">F</span>
            </div>
            <div className="min-w-0">
              <h1 className="text-sm font-semibold text-neutral-100 tracking-tight leading-tight">Fact Check AI</h1>
              <p className="text-[10px] text-neutral-500 leading-tight">Evidence-first verification</p>
            </div>
          </div>
        </div>
      </Stagger>

      {/* New verification — shadcn Button, nested island CTA */}
      <Stagger on={stagger} delay={75}>
        <div className="px-3 pb-3 shrink-0">
          <Button
            onClick={() => { onNew(); onNavigate(); }}
            className="group w-full flex items-center justify-between pl-4 pr-1.5 py-1.5 h-auto rounded-full bg-emerald-400 text-neutral-950 transition-all duration-500 ease-fluid hover:bg-emerald-300 active:scale-[0.98] shadow-[0_8px_32px_-12px_rgba(52,211,153,0.5)]"
          >
            <span className="text-xs font-semibold tracking-tight">New verification</span>
            <span className="w-7 h-7 rounded-full bg-neutral-950/10 flex items-center justify-center transition-transform duration-500 ease-fluid group-hover:rotate-90">
              <Plus size={14} strokeWidth={1.5} />
            </span>
          </Button>
        </div>
      </Stagger>

      {/* Search — shadcn Input in double-bezel */}
      <Stagger on={stagger} delay={125}>
        <div className="px-3 pb-2 shrink-0">
          <div className="rounded-full p-1 bg-white/[0.04] ring-1 ring-white/10 transition-all duration-500 ease-fluid focus-within:ring-emerald-400/25">
            <div className="relative rounded-full bg-[#0a0a0b]">
              <Search size={13} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-600 pointer-events-none" />
              <Input
                type="text"
                value={query}
                onChange={(e) => handleSearch(e.target.value)}
                placeholder="Search history…"
                className="w-full pl-9 pr-3 py-2 h-auto rounded-full bg-transparent border-0 text-xs text-neutral-200 placeholder:text-neutral-600 focus-visible:ring-0 focus-visible:border-0 shadow-none"
              />
              {searching && (
                <span className="absolute right-3 top-1/2 -translate-y-1/2 w-3 h-3 border border-neutral-700 border-t-neutral-300 rounded-full animate-spin" />
              )}
            </div>
          </div>
        </div>
      </Stagger>

      {/* History — shadcn ScrollArea */}
      <Stagger on={stagger} delay={175}>
        <ScrollArea className="flex-1 min-h-0 px-2.5 py-2">
          {groups.length === 0 ? (
            <div className="text-center py-10 px-2 text-neutral-600 text-xs">
              <p>{searchResults !== null ? "No matches found." : "No verifications yet."}</p>
              <p className="text-[10px] mt-1.5 text-neutral-700">
                {searchResults !== null ? "Try a different search." : "Check your first claim to get started."}
              </p>
            </div>
          ) : (
            groups.map(({ label, entries }) => (
              <div key={label} className="mb-4">
                <h3 className="text-[10px] font-medium text-neutral-600 tracking-[0.12em] mb-1.5 px-1.5">{label}</h3>
                <div className="space-y-0.5">
                  {entries.map((entry) => (
                    <button
                      key={entry.id}
                      onClick={() => { onSelect(entry); onNavigate(); }}
                      className={`w-full text-left flex items-center gap-2.5 px-2 py-2 rounded-xl transition-all duration-500 ease-fluid active:scale-[0.99] focus-visible:outline-none ${
                        selectedId === entry.id
                          ? "bg-white/[0.07] ring-1 ring-emerald-400/20"
                          : "hover:bg-white/[0.04]"
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 mt-0.5 rounded-full shrink-0 ${verdictDot(entry.verdict)}`} />
                      <div className="min-w-0 flex-1">
                        <p className="text-[11.5px] text-neutral-200 font-medium truncate leading-snug">
                          {entry.claim_text}
                        </p>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className={`text-[9px] px-1.5 py-px rounded-md font-semibold ${verdictBadge(entry.verdict)}`}>
                            {entry.verdict}
                          </span>
                          <span className="text-[10px] text-neutral-600 font-mono tabular-nums">
                            {new Date(entry.created_at).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}
                          </span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))
          )}
        </ScrollArea>
      </Stagger>
    </>
  );
}

/** Two-line hamburger that fluidly morphs into an X */
function Hamburger({ open, onClick }: { open: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="relative w-9 h-9 rounded-full bg-white/[0.06] ring-1 ring-white/10 flex items-center justify-center transition-colors duration-500 ease-fluid hover:bg-white/[0.1] focus-visible:outline-none shrink-0"
      aria-label={open ? "Close menu" : "Open menu"}
      aria-expanded={open}
    >
      <span
        className={`absolute w-4 h-px bg-neutral-200 rounded-full transition-all duration-500 ease-fluid ${
          open ? "rotate-45" : "-translate-y-[3.5px]"
        }`}
      />
      <span
        className={`absolute w-4 h-px bg-neutral-200 rounded-full transition-all duration-500 ease-fluid ${
          open ? "-rotate-45" : "translate-y-[3.5px]"
        }`}
      />
    </button>
  );
}

export function Sidebar(props: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Fluid island bar — detached glass pill, never edge-to-edge.
          z-[55] keeps the morphing burger clickable above the drawer overlay. */}
      <div className="md:hidden fixed top-0 inset-x-0 z-[55] px-4 pt-4 pointer-events-none">
        <div className="pointer-events-auto mx-auto w-max flex items-center gap-2 pl-1.5 pr-3 py-1.5 rounded-full bg-neutral-900/80 backdrop-blur-2xl ring-1 ring-white/10 shadow-[0_16px_48px_-16px_rgba(0,0,0,0.8)]">
          <Hamburger open={mobileOpen} onClick={() => setMobileOpen(!mobileOpen)} />
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-md bg-emerald-400 flex items-center justify-center">
              <span className="text-neutral-950 font-bold text-[10px]">F</span>
            </div>
            <span className="text-[13px] font-semibold text-neutral-100 tracking-tight">Fact Check AI</span>
          </div>
        </div>
      </div>

      {/* Desktop column — sticky, blur allowed on sticky layers */}
      <aside className="hidden md:flex w-[300px] shrink-0 sticky top-0 h-dvh flex-col bg-[#0a0a0b]/85 backdrop-blur-2xl border-r border-white/[0.06]">
        <SidebarContent {...props} onNavigate={() => {}} />
      </aside>

      {/* Drawer — heavy glass overlay + staggered mask reveal */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50">
          <div
            className="absolute inset-0 bg-black/80 backdrop-blur-3xl"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute left-0 top-0 h-dvh w-[280px] bg-[#0a0a0b] border-r border-white/[0.08] flex flex-col shadow-[24px_0_80px_-24px_rgba(0,0,0,0.9)]">
            <SidebarContent {...props} onNavigate={() => setMobileOpen(false)} stagger />
          </aside>
        </div>
      )}
    </>
  );
}
