import { Link } from "react-router-dom";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { PageRefreshControls } from "@/components/PageRefreshControls";
import { formatBytes } from "@/lib/formatBytes";
import { formatRelativeTime } from "@/lib/formatRelativeTime";
import { useCleanupExecutionsQuery } from "./hooks/useCleanupReview";

/* CleanupHistoryPage — Blueprint §4 v1.1 M2.
   Lists batches and standalone executions. Undo/Restore is R-B4 (backend gap)
   and is not surfaced as an action here. */
export function CleanupHistoryPage() {
  const executions = useCleanupExecutionsQuery();
  const batches = executions.data?.batches ?? [];
  const singles = (executions.data?.executions ?? []).filter((e) => !e.batch_id);

  return (
    <section
      aria-labelledby="history-title"
      className="mx-auto flex w-full max-w-page flex-col gap-5"
    >
      <header className="flex flex-col gap-2">
        <Link
          to="/recover"
          className="w-fit rounded-md text-meta text-text-muted hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          ← Back to Recover space
        </Link>
        <h1 id="history-title" className="text-title text-text">
          Cleanup history
        </h1>
        <p className="text-body text-text-muted">
          Every dry-run and execution Handoffarr has recorded.
        </p>
        <PageRefreshControls
          dataUpdatedAt={executions.dataUpdatedAt}
          isFetching={executions.isFetching}
          onRefresh={() => { void executions.refetch(); }}
        />
      </header>

      {executions.isLoading ? (
        <LoadingState label="Loading history" rows={4} />
      ) : executions.isError ? (
        <ErrorState
          title="Couldn't load history"
          description="Reload once the backend is back."
        />
      ) : batches.length === 0 && singles.length === 0 ? (
        <EmptyState
          title="No history yet"
          description="When you preview and execute a batch, it will appear here."
        />
      ) : (
        <div className="flex flex-col gap-6">
          {batches.length ? (
            <section className="flex flex-col gap-2">
              <h2 className="text-subtitle text-text">Batches</h2>
              <ul className="flex flex-col gap-2">
                {batches.map((b) => (
                  <li
                    key={b.batch_id}
                    className={`rounded-lg bg-surface p-4 shadow-elev-1 ${
                      isDeemphasized(b.status) ? "opacity-75" : ""
                    }`}
                  >
                    <Link
                      to={`/recover/history/${encodeURIComponent(b.batch_id)}`}
                      className="flex flex-wrap items-baseline justify-between gap-2 rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
                    >
                      <p className="text-body text-text">
                        Cleanup Batch
                      </p>
                      <p className="text-meta text-text-muted">
                        {formatRelativeTime(b.completed_at ?? b.created_at)}
                      </p>
                    </Link>
                    <p className="mt-1 break-all font-mono text-meta text-text-subtle">
                      {b.batch_id}
                    </p>
                    <dl className="mt-1 flex flex-wrap gap-x-4 text-meta text-text-muted">
                      <div className="flex gap-1">
                        <dt>Status</dt>
                        <dd className="text-text">{b.status ?? "—"}</dd>
                      </div>
                      <div className="flex gap-1">
                        <dt>Items</dt>
                        <dd className="text-text [font-variant-numeric:tabular-nums]">
                          {b.completed_count ?? 0}/{b.item_count ?? 0}
                        </dd>
                      </div>
                      <div className="flex gap-1">
                        <dt>Recovered</dt>
                        <dd className={`${isCompleted(b.status) ? "font-semibold text-success" : "text-text"} [font-variant-numeric:tabular-nums]`}>
                          {formatBytes(b.actual_recovered_bytes ?? 0)}
                        </dd>
                      </div>
                    </dl>
                    {batchBlockingReasons(b).length ? (
                      <ul className="mt-2 list-disc pl-5 text-meta text-text-muted">
                        {batchBlockingReasons(b).map((reason) => <li key={reason}>{reason}</li>)}
                      </ul>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {singles.length ? (
            <section className="flex flex-col gap-2">
              <h2 className="text-subtitle text-text">Single executions</h2>
              <ul className="flex flex-col gap-2">
                {singles.map((e) => (
                  <li
                    key={e.execution_id}
                    className={`rounded-lg bg-surface p-4 shadow-elev-1 ${
                      isDeemphasized(e.execution_status) ? "opacity-75" : ""
                    }`}
                  >
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <p className="text-body text-text">
                        {e.media_title ?? e.media_id ?? e.execution_id}
                      </p>
                      <p className="text-meta text-text-muted">
                        {formatRelativeTime(e.completed_at ?? e.created_at)}
                      </p>
                    </div>
                    <p className="text-meta text-text-muted">
                      {e.execution_status ?? "—"} ·{" "}
                      {formatBytes(e.recoverable_bytes ?? 0)}
                    </p>
                    {e.blocking_reasons?.length ? (
                      <ul className="mt-2 list-disc pl-5 text-meta text-text-muted">
                        {e.blocking_reasons.map((reason) => <li key={reason}>{reason}</li>)}
                      </ul>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      )}
    </section>
  );
}

function isCompleted(status: string | null | undefined) {
  return status?.toLowerCase() === "completed";
}

function isDeemphasized(status: string | null | undefined) {
  const normalized = status?.toLowerCase() ?? "";
  return normalized.includes("dry run") || normalized.includes("blocked");
}

function batchBlockingReasons(batch: { evidence?: Record<string, unknown> }) {
  const reasons = batch.evidence?.execute_blocking_reasons;
  return Array.isArray(reasons)
    ? reasons.filter((reason): reason is string => typeof reason === "string")
    : [];
}
