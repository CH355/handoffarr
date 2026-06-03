import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import type { ValidationResponse, ValidationStatus } from "@/api/validationApi";
import { StatusIcon, statusLabel } from "./StatusIcon";
import type { HealthStatus } from "../types";

interface ValidationStatusCardProps {
  data: ValidationResponse | undefined;
  isLoading: boolean;
  isError: boolean;
}

function mapStatus(s: ValidationStatus | undefined): HealthStatus {
  if (s === "OK") return "healthy";
  if (s === "WARN") return "warning";
  if (s === "FAIL") return "critical";
  return "unknown";
}

export function ValidationStatusCard({
  data,
  isLoading,
  isError,
}: ValidationStatusCardProps) {
  return (
    <section
      aria-labelledby="validation-card-title"
      className="flex flex-col gap-4 rounded-lg bg-surface p-5 shadow-elev-1"
    >
      <header className="flex items-center justify-between gap-3">
        <h3 id="validation-card-title" className="text-subtitle text-text">
          Validation
        </h3>
        {data ? (
          <span className="inline-flex items-center gap-2 text-meta uppercase tracking-wide text-text-muted">
            <StatusIcon status={mapStatus(data.status)} size={14} />
            {statusLabel(mapStatus(data.status))}
          </span>
        ) : null}
      </header>

      {isLoading ? (
        <LoadingState rows={2} label="Loading validation" />
      ) : isError || !data ? (
        <ErrorState
          title="Couldn't load validation"
          description="The validation endpoint is unreachable."
        />
      ) : (
        <ValidationBody data={data} />
      )}
    </section>
  );
}

function ValidationBody({ data }: { data: ValidationResponse }) {
  const counts = data.checks.reduce(
    (acc, c) => {
      const key = mapStatus(c.status);
      acc[key] += 1;
      return acc;
    },
    { healthy: 0, warning: 0, critical: 0, unknown: 0 } as Record<HealthStatus, number>,
  );

  if (data.checks.length === 0) {
    return (
      <p className="text-body text-text-muted">No validation checks recorded.</p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <dl className="flex flex-wrap gap-x-6 gap-y-2 text-meta text-text-muted">
        <div className="flex items-baseline gap-2">
          <dt className="uppercase tracking-wide">Passing</dt>
          <dd className="tabular-nums text-text">{counts.healthy}</dd>
        </div>
        <div className="flex items-baseline gap-2">
          <dt className="uppercase tracking-wide">Warnings</dt>
          <dd className="tabular-nums text-text">{counts.warning}</dd>
        </div>
        <div className="flex items-baseline gap-2">
          <dt className="uppercase tracking-wide">Failing</dt>
          <dd className="tabular-nums text-text">{counts.critical}</dd>
        </div>
      </dl>
      <ul className="flex flex-col divide-y divide-border rounded-md border border-border">
        {data.checks.map((check, idx) => {
          const status = mapStatus(check.status);
          return (
            <li
              key={`${check.name ?? "check"}-${idx}`}
              className="flex items-start gap-3 px-4 py-3"
            >
              <StatusIcon status={status} size={16} className="mt-0.5" />
              <div className="flex min-w-0 flex-col">
                <p className="text-body text-text">
                  {check.name ?? "Check"}
                </p>
                {check.message ? (
                  <p className="text-meta text-text-muted">{check.message}</p>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
