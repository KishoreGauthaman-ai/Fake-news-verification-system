/**
 * src/components/AgentTrace.tsx — Double-bezel agent trace with shadcn
 * Collapsible.
 */

import { Terminal, ChevronUp } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { AgentTraceStep } from "../types";

interface AgentTraceProps {
  trace: AgentTraceStep[];
}

function stepArgs(step: AgentTraceStep): string {
  if (!step.args || Object.keys(step.args).length === 0) return "{}";
  try {
    return JSON.stringify(step.args);
  } catch {
    return String(step.args);
  }
}

export function AgentTrace({ trace }: AgentTraceProps) {
  if (!trace || trace.length === 0) return null;

  return (
    <div className="animate-rise" style={{ animationDelay: "140ms" }}>
      {/* Outer shell */}
      <div className="rounded-[2rem] p-1.5 bg-white/[0.03] ring-1 ring-white/[0.08] shadow-[inset_0_1px_1px_rgba(255,255,255,0.06),0_40px_80px_-48px_rgba(0,0,0,0.9)]">
        {/* Inner core */}
        <Collapsible defaultOpen className="rounded-[calc(2rem-0.375rem)] bg-[#0a0a0b] overflow-hidden">
          <CollapsibleTrigger className="group w-full flex items-center justify-between px-6 py-5 text-left transition-colors duration-500 ease-fluid hover:bg-white/[0.02] focus-visible:outline-none">
            <div className="flex items-center gap-2.5">
              <Terminal size={15} strokeWidth={1.5} className="text-neutral-500" />
              <h3 className="text-sm font-semibold text-neutral-100 tracking-tight">How I checked this</h3>
              <span className="text-xs text-neutral-500 font-mono tabular-nums">({trace.length} steps)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-neutral-500 font-medium tracking-wide group-data-[state=closed]:hidden">Hide</span>
              <span className="text-[10px] text-neutral-500 font-medium tracking-wide group-data-[state=open]:hidden">Show</span>
              <ChevronUp size={14} strokeWidth={1.5} className="text-neutral-500 transition-transform duration-500 ease-fluid group-data-[state=closed]:rotate-180" />
            </div>
          </CollapsibleTrigger>

          <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-none transition-all">
            <div className="px-6 pb-6 border-t border-white/[0.05]">
              <div className="mt-4 space-y-2">
                {trace.map((step, i) => (
                  <div
                    key={i}
                    className="rounded-2xl bg-white/[0.03] ring-1 ring-white/[0.06] overflow-hidden transition-colors duration-500 ease-fluid hover:ring-white/[0.12] animate-rise"
                    style={{ animationDelay: `${60 + i * 50}ms` }}
                  >
                    <div className="flex items-center gap-2.5 px-4 py-2.5 bg-white/[0.02] border-b border-white/[0.05]">
                      <span className="text-[10px] font-mono font-medium text-emerald-300 tabular-nums">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="text-xs font-mono font-medium text-neutral-200 tracking-tight truncate">
                        {step.name}
                      </span>
                    </div>
                    <div className="p-4 space-y-1.5 font-mono text-xs">
                      <div className="text-neutral-400 truncate" title={stepArgs(step)}>
                        <span className="text-neutral-600">args</span>{" "}
                        <span className="text-neutral-300">{stepArgs(step)}</span>
                      </div>
                      <div className="text-neutral-400">
                        <span className="text-neutral-600">result</span>{" "}
                        <span className={step.success === false ? "text-rose-300" : "text-emerald-200/80"}>
                          {step.result
                            ? step.result.length > 140
                              ? step.result.slice(0, 140) + "…"
                              : step.result
                            : "executed"}
                        </span>
                      </div>
                      {step.error && (
                        <div className="text-rose-300">error: {step.error}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </div>
  );
}
