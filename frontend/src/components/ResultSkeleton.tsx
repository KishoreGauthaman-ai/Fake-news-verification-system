/**
 * src/components/ResultSkeleton.tsx — Loading skeleton shaped like the
 * double-bezel result view, so the layout doesn't jump when data lands.
 */

interface ResultSkeletonProps {
  claim: string;
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-[2rem] p-1.5 bg-white/[0.03] ring-1 ring-white/[0.08] shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)]">
      <div className="rounded-[calc(2rem-0.375rem)] bg-[#0a0a0b]">{children}</div>
    </div>
  );
}

export function ResultSkeleton({ claim }: ResultSkeletonProps) {
  return (
    <div className="flex-1">
      <p className="mb-8 text-sm text-neutral-400 text-pretty max-w-[60ch]">
        Checking <span className="text-neutral-200 font-medium">“{claim}”</span> against fact-check feeds,
        the web, and trusted sources.
      </p>

      <div className="space-y-4">
        {/* Verdict card skeleton */}
        <Shell>
          <div className="p-6 md:p-8">
            <div className="flex items-end justify-between mb-4">
              <div className="skeleton h-3 w-24 rounded-full animate-shimmer" />
              <div className="skeleton h-12 w-28 rounded-xl animate-shimmer" />
            </div>
            <div className="skeleton h-1.5 w-full rounded-full animate-shimmer mb-8" />
            <div className="space-y-3">
              <div className="skeleton h-3.5 w-full animate-shimmer" />
              <div className="skeleton h-3.5 w-[92%] animate-shimmer" />
              <div className="skeleton h-3.5 w-[64%] animate-shimmer" />
            </div>
          </div>
        </Shell>

        {/* Sources skeleton */}
        <Shell>
          <div className="px-6 pt-6 pb-4">
            <div className="skeleton h-4 w-28 rounded animate-shimmer" />
          </div>
          {[88, 76, 60].map((w, i) => (
            <div key={i} className="flex items-center gap-4 px-6 py-4 border-t border-white/[0.05]">
              <div className="skeleton w-1.5 h-1.5 rounded-full animate-shimmer" />
              <div className="flex-1 space-y-2">
                <div className="skeleton h-3.5 rounded animate-shimmer" style={{ width: `${w}%` }} />
                <div className="skeleton h-2.5 w-40 rounded animate-shimmer" />
              </div>
            </div>
          ))}
        </Shell>

        {/* Trace skeleton */}
        <Shell>
          <div className="px-6 py-5">
            <div className="skeleton h-4 w-44 rounded animate-shimmer" />
          </div>
        </Shell>
      </div>
    </div>
  );
}
