import { useEffect, useReducer, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { InlineConfirmationStrip } from "@/components/InlineConfirmationStrip";
import { SuccessStateBanner } from "@/components/SuccessStateBanner";
import { formatBytes } from "@/lib/formatBytes";
import {
  CONFIRMATION,
  postCleanupBatchDryRun,
  postCleanupBatchExecute,
  type CleanupBatchDryRunResult,
  type CleanupBatchItem,
} from "@/api/cleanupApi";
import {
  executionReducer,
  initialExecutionState,
} from "./reducers/executionReducer";

/* PreviewPage — Blueprint §4 v1.1 M3. Full-screen (not modal) dry-run preview.
   Pipeline: read selection → batch dry-run → InlineConfirmationStrip (phrase
   "EXECUTE BATCH CLEANUP") → batch execute → SuccessStateBanner.
   No deletion happens until the user types the confirmation phrase and clicks
   Execute. The batch execute call honors the backend's existing safety gates. */
export function PreviewPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selection, setSelection] = useState<CleanupBatchItem[] | null>(null);
  const [dryRun, setDryRun] = useState<CleanupBatchDryRunResult | null>(null);
  const [dryRunError, setDryRunError] = useState<string | null>(null);
  const [state, dispatch] = useReducer(executionReducer, initialExecutionState);

  useEffect(() => {
    const raw = sessionStorage.getItem("recover.batchSelection");
    if (!raw) {
      setSelection([]);
      return;
    }
    try {
      const parsed = JSON.parse(raw) as CleanupBatchItem[];
      setSelection(Array.isArray(parsed) ? parsed : []);
    } catch {
      setSelection([]);
    }
  }, []);

  const dryRunMutation = useMutation({
    mutationFn: () =>
      postCleanupBatchDryRun({
        items: selection ?? [],
        confirmation: CONFIRMATION.batchDryRun,
      }),
    onSuccess: (data) => {
      setDryRun(data);
      setDryRunError(null);
    },
    onError: (err: Error) => {
      setDryRunError(err.message);
      setDryRun(null);
    },
  });

  useEffect(() => {
    if (!selection) return;
    if (selection.length === 0) return;
    if (dryRun || dryRunMutation.isPending || dryRunError) return;
    dryRunMutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selection]);

  const executeMutation = useMutation({
    mutationFn: () => {
      if (!dryRun?.plan_id) throw new Error("No dry-run plan to execute.");
      return postCleanupBatchExecute({
        plan_id: dryRun.plan_id,
        confirmation: CONFIRMATION.batchExecute,
      });
    },
    onMutate: () => {
      dispatch({ type: "start" });
    },
    onSuccess: (data) => {
      const status = String(data.batch_status ?? data.status ?? "");
      const completed = Number(data.completed_count ?? 0);
      const failed = Number(data.failed_count ?? 0);
      const recovered = Number(
        data.total_recovered_bytes ?? data.actual_recovered_bytes ?? 0,
      );
      if (status.toLowerCase().includes("blocked")) {
        dispatch({
          type: "blocked",
          payload: {
            message:
              data.blocking_reasons?.join(" ")
              || "Backend safety gates blocked this cleanup.",
          },
        });
      } else {
        dispatch({
          type: "success",
          payload: {
            completedCount: completed,
            failedCount: failed,
            recoveredBytes: recovered,
          },
        });
      }
      queryClient.invalidateQueries({ queryKey: ["cleanup"], exact: true });
      queryClient.invalidateQueries({ queryKey: ["cleanup", "review"] });
      queryClient.invalidateQueries({ queryKey: ["cleanup", "executions"] });
      sessionStorage.removeItem("recover.batchSelection");
    },
    onError: (err: Error) => {
      dispatch({ type: "fail", payload: { message: err.message } });
    },
  });

  if (!selection) return <LoadingState label="Loading preview" rows={3} />;

  if (selection.length === 0) {
    return (
      <section className="mx-auto flex w-full max-w-page flex-col gap-4">
        <EmptyState
          title="No selection to preview"
          description="Pick safe candidates first, then come back here to preview them."
          action={
            <Link
              to="/recover/safe"
              className="rounded-md bg-accent px-4 py-2 text-body font-medium text-accent-on hover:bg-accent-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
            >
              Go to safe review
            </Link>
          }
        />
      </section>
    );
  }

  return (
    <section
      aria-labelledby="preview-title"
      className="mx-auto flex w-full max-w-page flex-col gap-5"
    >
      <header className="flex flex-col gap-2">
        <Link
          to="/recover/safe"
          className="w-fit rounded-md text-meta text-text-muted hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          ← Back to safe review
        </Link>
        <h1 id="preview-title" className="text-title text-text">
          Preview cleanup
        </h1>
        <p className="text-body text-text-muted">
          Handoffarr ran a dry-run against your selection. Review each line, then
          confirm to execute. Nothing has been deleted yet.
        </p>
      </header>

      {dryRunMutation.isPending ? (
        <LoadingState label="Running dry-run" rows={3} />
      ) : dryRunError ? (
        <ErrorState
          title="Dry-run failed"
          description={dryRunError}
          action={
            <button
              type="button"
              onClick={() => {
                setDryRunError(null);
                dryRunMutation.mutate();
              }}
              className="rounded-md bg-accent px-3 py-1.5 text-body font-medium text-accent-on hover:bg-accent-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
            >
              Retry dry-run
            </button>
          }
        />
      ) : dryRun ? (
        <PreviewBody result={dryRun} />
      ) : null}

      {dryRun && state.status === "succeeded" ? (
        <SuccessStateBanner
          variant="success"
          title="Cleanup complete"
          description={`Recovered ${formatBytes(state.recoveredBytes ?? 0)} across ${state.completedCount ?? 0} item${state.completedCount === 1 ? "" : "s"}.`}
          meta="Backend safety gates verified each removal."
          actions={
            <>
              <Link
                to="/recover/history"
                className="rounded-md px-3 py-1.5 text-body text-text hover:bg-surface focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
              >
                View history
              </Link>
              <button
                type="button"
                onClick={() => navigate("/recover")}
                className="rounded-md bg-accent px-3 py-1.5 text-body font-medium text-accent-on hover:bg-accent-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
              >
                Done
              </button>
            </>
          }
        />
      ) : null}

      {dryRun && state.status === "executing" ? (
        <section
          role="status"
          aria-live="polite"
          aria-label="Cleanup submitted"
          className="flex flex-col gap-2 rounded-lg border-l-2 border-accent bg-accent-quiet p-4 shadow-elev-1"
        >
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-border">
            <div className="h-full w-1/2 animate-pulse rounded-full bg-accent" />
          </div>
          <p className="text-subtitle text-text">Cleanup submitted</p>
          <p className="text-body text-text-muted">
            Handoffarr is processing the batch on the server. You may leave this
            page; Cleanup history will show the recorded outcome.
          </p>
          <p className="text-meta text-text-muted">
            Live item progress is not available from the backend.
          </p>
        </section>
      ) : null}

      {dryRun && state.status === "partial-fail" ? (
        <SuccessStateBanner
          variant="partial-fail"
          title="Some items did not complete"
          description={`Completed ${state.completedCount ?? 0}, failed ${state.failedCount ?? 0}. The backend rejected the failed items by its safety gates.`}
          actions={
            <Link
              to="/recover/history"
              className="rounded-md bg-accent px-3 py-1.5 text-body font-medium text-accent-on hover:bg-accent-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
            >
              View history
            </Link>
          }
        />
      ) : null}

      {dryRun && state.status === "total-fail" ? (
        <ErrorState
          title="Execution failed"
          description={state.errorMessage ?? "Handoffarr could not execute the batch."}
          action={
            <button
              type="button"
              onClick={() => dispatch({ type: "reset" })}
              className="rounded-md bg-accent px-3 py-1.5 text-body font-medium text-accent-on hover:bg-accent-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
            >
              Try again
            </button>
          }
        />
      ) : null}

      {dryRun && state.status === "blocked" ? (
        <ErrorState
          title="Cleanup blocked"
          description={state.errorMessage ?? "Backend safety gates blocked this cleanup."}
          action={
            <Link
              to="/recover/history"
              className="rounded-md bg-accent px-3 py-1.5 text-body font-medium text-accent-on hover:bg-accent-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
            >
              View history
            </Link>
          }
        />
      ) : null}

      {dryRun?.allowed && (state.status === "idle" || state.status === "confirming") ? (
        state.status === "idle" ? (
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => dispatch({ type: "request-confirm" })}
              disabled={!dryRun.allowed}
              className="rounded-md bg-critical px-4 py-2 text-body font-medium text-accent-on hover:bg-critical/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50"
            >
              Execute cleanup
            </button>
          </div>
        ) : (
          <InlineConfirmationStrip
            expectedPhrase={CONFIRMATION.batchExecute}
            prompt={`Execute cleanup of ${dryRun.item_count} item${dryRun.item_count === 1 ? "" : "s"} (${formatBytes(dryRun.total_recoverable_bytes)})?`}
            confirmLabel="Execute"
            destructive
            busy={executeMutation.isPending}
            onCancel={() => dispatch({ type: "cancel" })}
            onConfirm={() => executeMutation.mutate()}
          />
        )
      ) : null}
    </section>
  );
}

function PreviewBody({ result }: { result: CleanupBatchDryRunResult }) {
  return (
    <>
      <section
        aria-label="Preview scope summary"
        className="flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-elev-1"
      >
        <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="flex flex-col">
            <dt className="text-meta text-text-subtle">Items in batch</dt>
            <dd className="text-title text-text [font-variant-numeric:tabular-nums]">
              {result.item_count}
            </dd>
          </div>
          <div className="flex flex-col">
            <dt className="text-meta text-text-subtle">Recoverable</dt>
            <dd className="text-title text-text [font-variant-numeric:tabular-nums]">
              {formatBytes(result.total_recoverable_bytes)}
            </dd>
          </div>
          <div className="flex flex-col">
            <dt className="text-meta text-text-subtle">Plan id</dt>
            <dd className="break-all font-mono text-body text-text">
              {result.plan_id ?? "—"}
            </dd>
          </div>
        </dl>
        <p className="text-meta text-text-muted">{result.warning}</p>
      </section>

      {result.blocking_reasons.length ? (
        <section
          aria-label="Blocking reasons"
          className="flex flex-col gap-2 rounded-lg border-l-2 border-critical bg-critical-quiet p-4"
        >
          <p className="text-subtitle text-text">Backend blocked this batch</p>
          <ul className="list-disc pl-5 text-body text-text-muted">
            {result.blocking_reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-label="Per-item projection" className="flex flex-col gap-2">
        <h2 className="text-subtitle text-text">Per-item projection</h2>
        <ul className="flex flex-col gap-2">
          {result.per_item.map((item) => (
            <li
              key={`${item.media_id}-${item.qbit_hash}`}
              className={`flex flex-col gap-1 rounded-lg bg-surface p-3 shadow-elev-1 ${
                item.allowed ? "border-l-2 border-success" : "border-l-2 border-critical"
              }`}
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="text-body text-text">
                  {item.media_title ?? item.media_id}
                </p>
                <p className="text-body text-text-muted [font-variant-numeric:tabular-nums]">
                  {formatBytes(item.recoverable_bytes ?? 0)}
                </p>
              </div>
              <p className="text-meta text-text-muted">
                {item.match_strength ?? "—"} · {item.allowed ? "Allowed" : "Blocked"}
              </p>
              {item.blocking_reasons?.length ? (
                <ul className="list-disc pl-5 text-meta text-text-muted">
                  {item.blocking_reasons.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
