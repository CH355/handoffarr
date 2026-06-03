import { Film } from "lucide-react";
import type { ImportEvent } from "@/api/importsApi";
import { formatRelativeTime } from "@/lib/formatRelativeTime";

interface RecentlyAddedRowProps {
  event: ImportEvent;
}

function buildTitle(event: ImportEvent): string {
  const base = event.title?.trim() || event.media_id || "Untitled";
  if (event.season != null && event.episode != null) {
    const s = String(event.season).padStart(2, "0");
    const e = String(event.episode).padStart(2, "0");
    return `${base} · S${s}E${e}`;
  }
  if (event.release_year) {
    return `${base} (${event.release_year})`;
  }
  return base;
}

/* Foundation §9 ItemRow base behavior: hover raised, focus-visible ring,
   2px translate on active. Tabbable as a link, label includes timestamp. */
export function RecentlyAddedRow({ event }: RecentlyAddedRowProps) {
  const title = buildTitle(event);
  const when = formatRelativeTime(event.import_timestamp);
  return (
    <a
      href={`/library/${encodeURIComponent(event.media_id ?? "")}`}
      aria-label={`${title}, imported ${when}`}
      className="flex items-center gap-3 rounded-md px-3 py-2.5 transition-colors duration-fast ease-out hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg active:translate-y-px"
    >
      <span
        aria-hidden="true"
        className="flex h-10 w-7 shrink-0 items-center justify-center rounded-sm bg-surface-raised text-text-subtle"
      >
        <Film size={14} />
      </span>
      <span className="flex min-w-0 flex-1 items-center justify-between gap-3">
        <span className="truncate text-body text-text">{title}</span>
        <span className="shrink-0 text-meta text-text-subtle">
          Imported · {when}
        </span>
      </span>
    </a>
  );
}
