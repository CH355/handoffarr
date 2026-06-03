import { cn } from "@/lib/cn";
import { formatRelativeTime } from "@/lib/formatRelativeTime";

export interface ActivityTimelineEntry {
  id: string;
  label: string;
  timestamp?: string | null;
  tone?: "default" | "success" | "caution" | "critical";
}

interface ActivityTimelineProps {
  entries: ActivityTimelineEntry[];
  variant?: "compact";
  emptyLabel?: string;
}

const TONE_DOT: Record<NonNullable<ActivityTimelineEntry["tone"]>, string> = {
  default: "bg-text-muted",
  success: "bg-success",
  caution: "bg-caution",
  critical: "bg-critical",
};

/* ActivityTimeline — Compact variant per frontend-implementation-spec-v1.md §11.4.
   Full variant lands in Sprint 7. */
export function ActivityTimeline({
  entries,
  variant = "compact",
  emptyLabel = "No recent activity.",
}: ActivityTimelineProps) {
  if (entries.length === 0) {
    return <p className="text-meta text-text-muted">{emptyLabel}</p>;
  }
  return (
    <ol
      aria-label="Recent activity"
      className={cn(
        "flex flex-col gap-2",
        variant === "compact" ? "text-body" : "text-body",
      )}
    >
      {entries.map((entry) => (
        <li key={entry.id} className="flex items-start gap-3">
          <span
            aria-hidden={true}
            className={cn(
              "mt-2 h-1.5 w-1.5 shrink-0 rounded-full",
              TONE_DOT[entry.tone ?? "default"],
            )}
          />
          <div className="flex min-w-0 flex-1 flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
            <span className="text-body text-text">{entry.label}</span>
            {entry.timestamp ? (
              <span className="text-meta text-text-muted">
                {formatRelativeTime(entry.timestamp)}
              </span>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
