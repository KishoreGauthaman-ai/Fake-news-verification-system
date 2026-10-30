/**
 * src/components/ExampleClaims.tsx — Example claims that submit directly.
 */

interface ExampleClaimsProps {
  onSelect: (claim: string) => void;
}

const EXAMPLES = [
  {
    text: "COVID-19 vaccines contain tracking microchips",
    label: "Health",
  },
  {
    text: "The 2024 US election results were manipulated",
    label: "Election",
  },
  {
    text: "Climate change is a complete hoax",
    label: "Science",
  },
];

export function ExampleClaims({ onSelect }: ExampleClaimsProps) {
  return (
    <div className="w-full max-w-2xl">
      <p className="text-[10px] font-medium text-neutral-500 tracking-[0.2em] uppercase mb-3">
        Try one of these
      </p>
      <div className="flex flex-col sm:flex-row sm:flex-wrap gap-2">
        {EXAMPLES.map((ex, i) => (
          <button
            key={ex.text}
            onClick={() => onSelect(ex.text)}
            className="group text-left rounded-[1.75rem] p-1.5 bg-white/[0.03] ring-1 ring-white/[0.08] transition-transform duration-700 ease-out hover:scale-[1.02] focus-visible:outline-none active:scale-[0.99] animate-rise"
            style={{ animationDelay: `${320 + i * 70}ms` }}
          >
            <div className="rounded-[calc(1.75rem-0.375rem)] bg-[#0a0a0b] px-4 py-3 transition-colors duration-700 ease-out group-hover:bg-[#0e0e10]">
              <div className="text-[13px] text-neutral-300 font-medium text-pretty leading-snug transition-colors duration-700 ease-out group-hover:text-emerald-200">
                {ex.text}
              </div>
              <span className="text-[10px] text-neutral-600 font-medium tracking-[0.12em] uppercase">
                {ex.label}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
