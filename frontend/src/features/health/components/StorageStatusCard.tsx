import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import type { StorageResponse } from "@/api/storageApi";
import { formatBytes } from "@/lib/formatBytes";
import { StatusIcon, statusLabel } from "./StatusIcon";

interface StorageStatusCardProps {
  data: StorageResponse | undefined;
  isLoading: boolean;
  isError: boolean;
}

export function StorageStatusCard({
  data,
  isLoading,
  isError,
}: StorageStatusCardProps) {
  const summary = data?.summary;
  const hasData =
    summary !== undefined &&
    (summary.total_bytes !== null || summary.free_bytes !== null);

  let utilization: number | null = null;
  if (summary?.total_bytes && summary.used_bytes != null && summary.total_bytes > 0) {
    utilization = (summary.used_bytes / summary.total_bytes) * 100;
  }

  return (
    <section
      aria-labelledby="storage-card-title"
      className="flex flex-col gap-4 rounded-lg bg-surface p-5 shadow-elev-1"
    >
      <header className="flex items-center justify-between gap-3">
        <h3 id="storage-card-title" className="text-subtitle text-text">
          Storage
        </h3>
        {summary ? (
          <span className="inline-flex items-center gap-2 text-meta uppercase tracking-wide text-text-muted">
            <StatusIcon status={summary.health} size={14} />
            {statusLabel(summary.health)}
          </span>
        ) : null}
      </header>

      {isLoading ? (
        <LoadingState rows={2} label="Loading storage" />
      ) : isError ? (
        <ErrorState
          title="Couldn't load storage"
          description="The storage endpoint is unreachable."
        />
      ) : !hasData ? (
        <EmptyState
          title="No storage data"
          description="The backend has not reported storage capacity yet."
        />
      ) : (
        <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Metric label="Total" value={formatBytes(summary?.total_bytes ?? null)} />
          <Metric label="Used" value={formatBytes(summary?.used_bytes ?? null)} />
          <Metric label="Free" value={formatBytes(summary?.free_bytes ?? null)} />
          {utilization !== null ? (
            <div className="sm:col-span-3">
              <p className="mb-2 text-meta uppercase tracking-wide text-text-subtle">
                Utilization
              </p>
              <div
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(utilization)}
                aria-label="Storage utilization"
                className="h-2 w-full overflow-hidden rounded-pill bg-border"
              >
                <div
                  className="h-full bg-accent"
                  style={{
                    width: `${Math.max(0, Math.min(100, utilization))}%`,
                  }}
                />
              </div>
              <p className="mt-1 text-meta text-text-muted tabular-nums">
                {utilization.toFixed(1)}% used
              </p>
            </div>
          ) : null}
        </dl>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-meta uppercase tracking-wide text-text-subtle">
        {label}
      </dt>
      <dd className="text-title tabular-nums text-text">{value}</dd>
    </div>
  );
}
