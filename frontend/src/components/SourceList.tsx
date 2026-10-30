/**
 * src/components/SourceList.tsx — Double-bezel source list with shadcn
 * Badges, Tooltip stance dots, and magnetic rows.
 */

import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Source } from "../types";

interface SourceListProps {
  sources: Source[];
}

function tierStyles(tier?: string): { chip: string; label: string } {
  switch (tier) {
    case "tier1_factcheck":
      return { chip: "bg-emerald-400/10 text-emerald-300", label: "Fact-check" };
    case "tier1_news":
      return { chip: "bg-sky-400/10 text-sky-300", label: "News" };
    default:
      return { chip: "bg-white/[0.06] text-neutral-400", label: "Web" };
  }
}

function stance(stance?: string): { dot: string; title: string } {
  const s = (stance || "").toLowerCase();
  if (s.startsWith("support") || s === "true") return { dot: "bg-emerald-400", title: "Supports the claim" };
  if (s.startsWith("contradict") || s.startsWith("false") || s.startsWith("debunk"))
    return { dot: "bg-rose-400", title: "Contradicts the claim" };
  return { dot: "bg-amber-400", title: "Neutral / not rated" };
}

export function SourceList({ sources }: SourceListProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="relative z-0 -mt-3">
      {/* Outer shell */}
      <div className="rounded-[2rem] p-1.5 bg-white/[0.03] ring-1 ring-white/[0.08] shadow-[inset_0_1px_1px_rgba(255,255,255,0.06),0_40px_80px_-48px_rgba(0,0,0,0.9)]">
        {/* Inner core */}
        <div className="rounded-[calc(2rem-0.375rem)] bg-[#0a0a0b] overflow-hidden">
          <div className="px-6 pt-6 pb-4">
            <h3 className="text-sm font-semibold text-neutral-100 tracking-tight flex items-center gap-2">
              Sources
              <span className="text-xs text-neutral-500 font-mono tabular-nums font-normal">({sources.length})</span>
            </h3>
          </div>
          <div className="divide-y divide-white/[0.05]">
            {sources.map((source, i) => {
              const tier = tierStyles(source.tier);
              const s = stance(source.stance);
              const url = source.url || source.href || "";
              let host = "";
              try {
                host = url ? new URL(url).hostname.replace("www.", "") : "";
              } catch {
                host = "";
              }

              return (
                <a
                  key={i}
                  href={url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  tabIndex={url ? 0 : -1}
                  aria-disabled={!url}
                  className="group flex items-start gap-4 px-6 py-4 transition-all duration-500 ease-fluid hover:bg-white/[0.03] focus-visible:outline-none animate-rise"
                  style={{ animationDelay: `${60 + i * 70}ms` }}
                >
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span
                        className={`w-1.5 h-1.5 mt-[7px] rounded-full shrink-0 transition-transform duration-500 ease-fluid group-hover:scale-125 ${s.dot}`}
                        aria-label={`stance: ${s.title}`}
                      />
                    </TooltipTrigger>
                    <TooltipContent side="top" className="text-[11px]">{s.title}</TooltipContent>
                  </Tooltip>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="secondary" className={`text-[10px] px-2 py-px rounded-md font-semibold tracking-wide border-0 ${tier.chip}`}>
                        {tier.label}
                      </Badge>
                      {source.relevance_score !== undefined && (
                        <span className="text-[10px] text-neutral-600 font-mono tabular-nums">
                          {source.relevance_score}
                        </span>
                      )}
                    </div>
                    <h4 className="text-sm font-medium text-neutral-200 leading-snug text-pretty transition-colors duration-500 ease-fluid group-hover:text-emerald-200">
                      {source.title || source.source || "Untitled source"}
                    </h4>
                    <p className="text-[11px] text-neutral-600 font-mono truncate mt-1">{host || url}</p>
                  </div>
                  <ExternalLink
                    size={14}
                    strokeWidth={1.5}
                    className="text-neutral-700 shrink-0 mt-1.5 transition-all duration-500 ease-fluid group-hover:text-neutral-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                  />
                </a>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
