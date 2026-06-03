import { Search } from "lucide-react";

interface LibrarySearchInputProps {
  value: string;
  onChange: (value: string) => void;
}

/* 40px Library variant per frontend-implementation-spec-v1.md §5.1. */
export function LibrarySearchInput({ value, onChange }: LibrarySearchInputProps) {
  return (
    <label className="relative block">
      <span className="sr-only">Search titles</span>
      <Search
        size={16}
        aria-hidden={true}
        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
      />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search titles..."
        aria-label="Search library titles"
        className="h-10 w-full rounded-md bg-surface pl-9 pr-3 text-body text-text placeholder:text-text-muted shadow-elev-1 outline-none focus-visible:ring-2 focus-visible:ring-accent"
      />
    </label>
  );
}
