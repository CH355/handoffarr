import { cn } from "@/lib/cn";
import type { LibraryMediaType } from "../types";

export type LibraryFilter = "all" | LibraryMediaType;

interface FilterChipRowProps {
  value: LibraryFilter;
  onChange: (next: LibraryFilter) => void;
  counts: Record<LibraryFilter, number>;
}

const CHIPS: Array<{ value: LibraryFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "movie", label: "Movies" },
  { value: "show", label: "Shows" },
  { value: "music", label: "Music" },
];

/* Single-select filter chips per Sprint 4 brief. */
export function FilterChipRow({ value, onChange, counts }: FilterChipRowProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Filter library by media type"
      className="flex flex-wrap items-center gap-2"
    >
      {CHIPS.map((chip) => {
        const active = chip.value === value;
        return (
          <button
            key={chip.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(chip.value)}
            className={cn(
              "inline-flex h-8 items-center gap-1.5 rounded-pill px-3 text-meta transition-colors duration-fast",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
              active
                ? "bg-accent text-accent-on"
                : "bg-surface text-text-muted hover:text-text",
            )}
          >
            <span>{chip.label}</span>
            <span className={cn("text-meta", active ? "opacity-90" : "opacity-60")}>
              {counts[chip.value] ?? 0}
            </span>
          </button>
        );
      })}
    </div>
  );
}
