/**
 * src/components/ClaimInput.tsx — Double-bezel claim input with shadcn
 * Textarea + nested Button-in-Button CTA.
 */

import { useState, useCallback } from "react";
import { ArrowRight } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

export interface ClaimInputProps {
  onSubmit: (claim: string) => void;
  loading?: boolean;
}

export function ClaimInput({ onSubmit, loading }: ClaimInputProps) {
  const [text, setText] = useState("");
  const isDisabled = !text.trim() || loading;

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!isDisabled) {
        onSubmit(text.trim());
      }
    },
    [text, isDisabled, onSubmit]
  );

  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-2xl">
      {/* Outer shell — machined aluminum tray */}
      <div
        className={`rounded-[1.75rem] p-1.5 bg-white/[0.04] ring-1 ring-white/10 transition-all duration-500 ease-fluid
        shadow-[inset_0_1px_1px_rgba(255,255,255,0.07),0_32px_64px_-32px_rgba(0,0,0,0.9)]
        focus-within:ring-emerald-400/30 focus-within:bg-white/[0.05] ${
          loading ? "opacity-60" : ""
        }`}
      >
        {/* Inner core — shadcn Textarea */}
        <div className="relative rounded-[calc(1.75rem-0.375rem)] bg-[#0a0a0b] overflow-hidden">
          <Textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste a claim or headline you want to verify…"
            rows={4}
            disabled={loading}
            className="w-full px-5 py-4 pb-24 bg-transparent border-0 text-neutral-100 placeholder:text-neutral-600 text-[15px] leading-relaxed resize-none min-h-[7.5rem] focus-visible:ring-0 focus-visible:border-0 shadow-none"
          />

          {/* Button-in-Button — shadcn Button with nested icon circle */}
          <Button
            type="submit"
            disabled={isDisabled}
            className={`group absolute bottom-5 right-5 flex items-center gap-2.5 pl-5 pr-1.5 py-1.5 h-auto rounded-full font-semibold text-[13px] tracking-tight transition-all duration-500 ease-fluid ${
              isDisabled
                ? "bg-white/[0.06] text-neutral-600 cursor-not-allowed shadow-none"
                : "bg-emerald-400 text-neutral-950 hover:bg-emerald-300 hover:-translate-y-[2px] active:scale-[0.97] shadow-[0_8px_32px_-8px_rgba(52,211,153,0.45)]"
            }`}
            aria-label="Verify claim"
          >
            {loading ? "Checking" : "Check"}
            <span
              className={`w-8 h-8 rounded-full flex items-center justify-center transition-transform duration-500 ease-fluid ${
                isDisabled ? "bg-white/[0.06]" : "bg-neutral-950/10 group-hover:translate-x-[3px] group-hover:-translate-y-[1px]"
              }`}
            >
              {loading ? (
                <span className="w-3.5 h-3.5 border border-neutral-600/50 border-t-neutral-400 rounded-full animate-spin" />
              ) : (
                <ArrowRight size={15} strokeWidth={1.5} />
              )}
            </span>
          </Button>
        </div>
      </div>
    </form>
  );
}
