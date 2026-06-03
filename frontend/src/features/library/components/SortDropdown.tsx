export type LibrarySort =
  | "recent"
  | "title_asc"
  | "size_desc";

interface SortDropdownProps {
  value: LibrarySort;
  onChange: (next: LibrarySort) => void;
}

const OPTIONS: Array<{ value: LibrarySort; label: string }> = [
  { value: "recent", label: "Recently added" },
  { value: "title_asc", label: "Title (A–Z)" },
  { value: "size_desc", label: "Largest items" },
];

export function SortDropdown({ value, onChange }: SortDropdownProps) {
  return (
    <label className="inline-flex items-center gap-2 text-meta text-text-muted">
      <span>Sort:</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as LibrarySort)}
        aria-label="Sort library"
        className="h-8 rounded-md bg-surface px-2 text-meta text-text shadow-elev-1 outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        {OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
