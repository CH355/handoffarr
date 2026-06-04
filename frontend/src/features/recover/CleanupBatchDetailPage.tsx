import { Link, useParams } from "react-router-dom";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { BackgroundRefreshStatus } from "@/components/BackgroundRefreshStatus";
import { formatBytes } from "@/lib/formatBytes";
import { formatRelativeTime } from "@/lib/formatRelativeTime";
import { useCleanupExecutionsQuery } from "./hooks/useCleanupReview";

/* CleanupBatchDetailPage — Blueprint §4 Cleanup Batch Detail.
   R-B3: no dedicated drill-down endpoint exists; we filter the executions list
   client-side. R-B4: Undo/Restore is a backend gap and is not offered here. */
export function CleanupBatchDetailPage() {
  const { batchId } = useParams<{ batchId: string }>();
  const executions = useCleanupExecutionsQuery();

  if (executions.isLoading) return <LoadingState label="Loading batch" rows={3} />;
  if (executions.isError) {
    return (
      <ErrorState
        title="Couldn't load batch"
        description="Reload once the backend is back."
      />
    );
  }

  const batch = executions.data?.batches.find((b) => b.batch_id === batchId);
  const items = (executions.data?.executions ?? []).filter(
    (e) => e.batch_id === batchId,
  );

  if (!batch) {
    return (
      <EmptyState
        title="Batch not found"
        description="This batch id does not appear in history."
      />
    );
  }

  return (
    <section
      aria-labelledby="batch-title"
      className="mx-auto flex w-full max-w-page flex-col gap-5"
    >
      <header className="flex flex-col gap-2">
        <Link
          to="/recover/history"
          className="w-fit rounded-md text-meta text-text-muted hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          ← Back to history
        </Link>
        <h1 id="batch-title" className="text-title text-text">
          Batch detail
        </h1>
        <p className="text-meta text-text-muted [font-variant-numeric:tabular-nums]">
          {batch.batch_id}
        </p>
        <BackgroundRefreshStatus isFetching={executions.isFetching && !executions.isLoading} />
      </header>

      <section
        aria-label="Batch summary"
        className="flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-elev-1"
      >
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Status" value={batch.status ?? "—"} />
          <Stat
            label="Items"
            value={`${batch.completed_count ?? 0}/${batch.item_count ?? 0}`}
          />
          <Stat
            label="Recovered"
            value={formatBytes(batch.actual_recovered_bytes ?? 0)}
          />
          <Stat
            label="Planned"
            value={formatBytes(batch.planned_recoverable_bytes ?? 0)}
          />
        </dl>
        <p className="text-meta text-text-muted">
          {formatRelativeTime(batch.completed_at ?? batch.created_at)}
        </p>
      </section>

      <section aria-label="Batch items" className="flex flex-col gap-2">
        <h2 className="text-subtitle text-text">Items</h2>
        {items.length === 0 ? (
          <EmptyState
            title="No item rows recorded"
            description="The backend has no per-item executions linked to this batch id."
          />
        ) : (
          <ul className="flex flex-col gap-2">
            {items.map((e) => (
              <li
                key={e.execution_id}
                className="rounded-lg bg-surface p-3 shadow-elev-1"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="text-body text-text">
                    {e.media_title ?? e.media_id ?? e.execution_id}
                  </p>
                  <p className="text-meta text-text-muted [font-variant-numeric:tabular-nums]">
                    {formatBytes(e.recoverable_bytes ?? 0)}
                  </p>
                </div>
                <p className="text-meta text-text-muted">
                  {e.execution_status ?? "—"} · {e.match_strength ?? "—"}
                </p>
                {e.blocking_reasons?.length ? (
                  <ul className="mt-1 list-disc pl-5 text-meta text-text-muted">
                    {e.blocking_reasons.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <dt className="text-meta text-text-subtle">{label}</dt>
      <dd className="text-body text-text [font-variant-numeric:tabular-nums]">{value}</dd>
    </div>
  );
}
