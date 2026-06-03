import type { ReactNode } from "react";

interface StatTileProps {
  label: string;
  value: ReactNode;
  supporting?: ReactNode;
  progressPct?: number | null;
}

/* Foundation §9.3 Stat Tile. Non-interactive on Home (Mockups §1 Component
   Behavior). Tile structure: uppercase label, Title-sized value, optional
   supporting line, optional progress bar. */
export function StatTile({ label, value, supporting, progressPct }: StatTileProps) {
  return (
    <article className="flex flex-col gap-3 rounded-lg bg-surface p-5 shadow-elev-1">
      <p className="text-meta uppercase tracking-wide text-text-subtle">
        {label}
      </p>
      <div className="flex flex-col gap-1">
        <p className="text-title tabular-nums text-text">{value}</p>
        {supporting ? (
          <p className="text-body text-text-muted">{supporting}</p>
        ) : null}
      </div>
      {typeof progressPct === "number" && Number.isFinite(progressPct) ? (
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(progressPct)}
          aria-label={`${label} usage`}
          className="h-2 w-full overflow-hidden rounded-pill bg-border"
        >
          <div
            className="h-full bg-accent"
            style={{ width: `${Math.max(0, Math.min(100, progressPct))}%` }}
          />
        </div>
      ) : null}
    </article>
  );
}
