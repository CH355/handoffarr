import { useRef } from "react";
import { cn } from "@/lib/cn";
import { formatBytes } from "@/lib/formatBytes";
import type { CleanupReviewItem } from "@/api/cleanupApi";

interface CandidateRowProps {
  item: CleanupReviewItem;
  variant: "safe" | "risky";
  selected?: boolean;
  onToggle?: (item: CleanupReviewItem, next: boolean) => void;
  onOpenEvidence: (item: CleanupReviewItem, trigger: HTMLElement) => void;
}

/* CandidateRow — Safe and Risky variants per Mockups §3/§4.
   Safe variant has a selection checkbox; Risky is read-only. */
export function CandidateRow({
  item,
  variant,
  selected,
  onToggle,
  onOpenEvidence,
}: CandidateRowProps) {
  const evidenceBtn = useRef<HTMLButtonElement>(null);
  const isRisky = variant === "risky";
  const confidence =
    typeof item.confidence_score === "number"
      ? `${Math.round(item.confidence_score * 100)}%`
      : "—";
  const explanation = item.pipeline_explanation;

  return (
    <li
      className={cn(
        "flex flex-col gap-3 rounded-lg bg-surface p-4 shadow-elev-1 md:flex-row md:items-start",
        isRisky ? "border-l-2 border-caution" : "border-l-2 border-success",
      )}
    >
      {!isRisky && onToggle ? (
        <label className="flex items-start gap-3 md:pt-1">
          <input
            type="checkbox"
            checked={Boolean(selected)}
            onChange={(e) => onToggle(item, e.target.checked)}
            aria-label={`Include ${item.media_title ?? "candidate"} in batch`}
            className="mt-0.5 h-4 w-4 rounded border-border-strong text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
          />
          <span className="sr-only">Include in batch</span>
        </label>
      ) : null}

      <div className="flex-1">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className="text-subtitle text-text">{item.media_title ?? "Untitled"}</p>
          <p className="text-body text-text [font-variant-numeric:tabular-nums]">
            {formatBytes(item.recoverable_bytes ?? 0)}
          </p>
        </div>
        {explanation ? (
          <div className="mt-2 flex flex-col gap-1 rounded-md bg-surface-raised px-3 py-2">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={cn(
                  "rounded-pill px-2 py-0.5 text-meta font-medium",
                  isRisky
                    ? "bg-caution/10 text-caution"
                    : "bg-success/10 text-success",
                )}
              >
                {explanation.title ?? "Needs review"}
              </span>
              <span className="text-meta text-text-subtle">
                {explanation.stage ?? "Evidence review"}
              </span>
            </div>
            {explanation.detail ? (
              <p className="text-meta text-text-muted">{explanation.detail}</p>
            ) : null}
          </div>
        ) : null}
        <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-meta text-text-muted">
          <div className="flex gap-1">
            <dt>Match</dt>
            <dd className="text-text">{item.match_strength ?? "—"}</dd>
          </div>
          <div className="flex gap-1">
            <dt>Confidence</dt>
            <dd className="text-text [font-variant-numeric:tabular-nums]">{confidence}</dd>
          </div>
          {explanation?.last_event ? (
            <div className="flex gap-1">
              <dt>Last</dt>
              <dd className="text-text">{explanation.last_event}</dd>
            </div>
          ) : null}
          {item.source_application ? (
            <div className="flex gap-1">
              <dt>Source</dt>
              <dd className="text-text">{item.source_application}</dd>
            </div>
          ) : null}
        </dl>
        {isRisky && item.risk_reasons?.length ? (
          <ul className="mt-2 list-disc pl-5 text-meta text-text-muted">
            {item.risk_reasons.slice(0, 3).map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        ) : null}
      </div>

      <div className="flex md:items-start">
        <button
          ref={evidenceBtn}
          type="button"
          onClick={() => onOpenEvidence(item, evidenceBtn.current!)}
          className="rounded-md px-3 py-1.5 text-meta font-medium text-accent hover:bg-accent-quiet focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          {isRisky ? "Why risky?" : "Why safe?"}
        </button>
      </div>
    </li>
  );
}
