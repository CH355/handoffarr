import { StatusIcon } from "./StatusIcon";
import { cn } from "@/lib/cn";
import type { HealthStatus } from "../types";

interface HealthSummaryBannerProps {
  overall: HealthStatus;
  counts: Record<HealthStatus, number>;
  lastValidation?: string | undefined;
}

function headline(overall: HealthStatus, counts: Record<HealthStatus, number>): string {
  if (overall === "critical") {
    const n = counts.critical;
    return `${n} critical issue${n === 1 ? "" : "s"}`;
  }
  if (overall === "warning") {
    const n = counts.warning + counts.critical;
    return `${n} issue${n === 1 ? "" : "s"} need attention`;
  }
  if (overall === "healthy") return "Everything connected.";
  return "Status unknown";
}

/* Foundation §9.2 Primary Banner pattern adapted for Health.
   Mockups §7: status-driven background (success-quiet / caution-quiet /
   critical-quiet); content drives meaning. */
export function HealthSummaryBanner({
  overall,
  counts,
  lastValidation,
}: HealthSummaryBannerProps) {
  const surface =
    overall === "critical"
      ? "bg-critical-quiet"
      : overall === "warning"
        ? "bg-caution-quiet"
        : overall === "healthy"
          ? "bg-success-quiet"
          : "bg-surface";

  return (
    <section
      aria-labelledby="health-summary-headline"
      className={cn(
        "flex flex-col gap-3 rounded-lg p-6 shadow-elev-1 md:p-8",
        surface,
      )}
    >
      <div className="flex items-start gap-3">
        <StatusIcon status={overall} size={22} className="mt-1" />
        <h2 id="health-summary-headline" className="text-display text-text">
          {headline(overall, counts)}
        </h2>
      </div>
      <dl className="flex flex-wrap gap-x-6 gap-y-2 text-meta text-text-muted">
        <div className="flex items-baseline gap-2">
          <dt className="uppercase tracking-wide">Healthy</dt>
          <dd className="tabular-nums text-text">{counts.healthy}</dd>
        </div>
        <div className="flex items-baseline gap-2">
          <dt className="uppercase tracking-wide">Warning</dt>
          <dd className="tabular-nums text-text">{counts.warning}</dd>
        </div>
        <div className="flex items-baseline gap-2">
          <dt className="uppercase tracking-wide">Critical</dt>
          <dd className="tabular-nums text-text">{counts.critical}</dd>
        </div>
        {counts.unknown > 0 ? (
          <div className="flex items-baseline gap-2">
            <dt className="uppercase tracking-wide">Unknown</dt>
            <dd className="tabular-nums text-text">{counts.unknown}</dd>
          </div>
        ) : null}
      </dl>
      {lastValidation ? (
        <p className="text-meta text-text-subtle">
          Last validation: {lastValidation}
        </p>
      ) : null}
    </section>
  );
}
