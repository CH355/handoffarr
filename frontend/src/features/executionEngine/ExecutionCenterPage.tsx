import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  getExecutionEngineStatus,
  getExecutionJobs,
  type ExecutionJob,
} from "@/api/executionEngineApi";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContainer } from "@/components/PageContainer";

const STATUSES = [
  "Pending",
  "Approved",
  "Running",
  "Waiting",
  "Completed",
  "Failed",
  "Cancelled",
  "Rolled Back",
];

export function ExecutionCenterPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const status = useQuery({
    queryKey: ["execution-engine", "status"],
    queryFn: getExecutionEngineStatus,
  });
  const jobs = useQuery({
    queryKey: ["execution-engine", "jobs", statusFilter],
    queryFn: ({ signal }) =>
      getExecutionJobs(
        { status: statusFilter || undefined, limit: 50 },
        signal,
      ),
  });

  return (
    <PageContainer
      title="Execution Center"
      description="Observable, auditable, cancellable execution of approved recovery plans."
    >
      {status.isLoading ? (
        <LoadingState label="Loading execution status" rows={4} />
      ) : status.isError || !status.data ? (
        <ErrorState
          title="Execution Center unavailable"
          description="Status could not be loaded."
        />
      ) : (
        <div className="flex flex-col gap-4">
          <section className="rounded-lg bg-accent-quiet p-5">
            <p className="text-meta font-semibold uppercase text-accent">
              Execution Engine
            </p>
            <p className="mt-1 text-title text-text">
              {status.data.total_jobs} jobs
            </p>
            <p className="mt-2 text-body text-text-muted">
              Average duration: {status.data.average_duration_seconds}s
            </p>
          </section>

          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {STATUSES.map((s) => (
              <Metric
                key={s}
                label={s}
                value={status.data.queue_counts[s] ?? 0}
                active={statusFilter === s}
                onClick={() =>
                  setStatusFilter((prev) => (prev === s ? "" : s))
                }
              />
            ))}
          </dl>

          <section className="rounded-lg bg-surface p-5 shadow-elev-1">
            <h2 className="mb-4 text-subtitle text-text">Queue</h2>
            {jobs.isLoading ? (
              <LoadingState label="Loading jobs" rows={4} />
            ) : jobs.isError ? (
              <ErrorState
                title="Couldn't load jobs"
                description="The execution queue is unavailable."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[900px] text-left text-body">
                  <thead className="border-b border-border text-meta uppercase text-text-subtle">
                    <tr>
                      {[
                        "ID",
                        "Plan",
                        "Torrent",
                        "Status",
                        "Step",
                        "Action",
                        "Retries",
                        "Created",
                        "Actions",
                      ].map((h) => (
                        <th key={h} className="p-3">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {(jobs.data?.jobs ?? []).map((job) => (
                      <JobRow key={job.execution_id} job={job} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </PageContainer>
  );
}

function Metric({
  label,
  value,
  active,
  onClick,
}: {
  label: string;
  value: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg p-5 text-left shadow-elev-1 hover:ring-2 hover:ring-accent ${
        active ? "bg-accent-quiet ring-2 ring-accent" : "bg-surface"
      }`}
    >
      <dt className="text-meta text-text-muted">{label}</dt>
      <dd className="mt-1 text-title tabular-nums text-text">{value}</dd>
    </button>
  );
}

function JobRow({ job }: { job: ExecutionJob }) {
  return (
    <tr>
      <td className="p-3 font-mono text-meta">
        <Link
          to={`/execution-center/${job.execution_id}`}
          className="text-accent"
        >
          {job.execution_id.slice(0, 20)}…
        </Link>
      </td>
      <td className="p-3">{job.plan_id.slice(0, 16)}…</td>
      <td className="p-3 font-mono text-meta">{job.torrent_hash.slice(0, 12)}…</td>
      <td className="p-3">
        <StatusBadge status={job.status} />
      </td>
      <td className="p-3">
        {job.current_step}/{job.total_steps}
      </td>
      <td className="p-3 text-text-muted">
        {job.current_action ?? "—"}
      </td>
      <td className="p-3">{job.retry_count}</td>
      <td className="p-3 text-meta">
        {new Date(job.created_at).toLocaleString()}
      </td>
      <td className="p-3">
        <Link
          to={`/execution-center/${job.execution_id}`}
          className="font-semibold text-accent"
        >
          Inspect
        </Link>
      </td>
    </tr>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color =
    status === "Completed"
      ? "bg-success-quiet text-success"
      : status === "Failed" || status === "Rolled Back"
        ? "bg-critical-quiet text-critical"
        : status === "Running"
          ? "bg-accent-quiet text-accent"
          : status === "Pending" || status === "Approved"
            ? "bg-caution-quiet text-caution"
            : "bg-surface text-text-muted";
  return (
    <span className={`inline-flex rounded-pill px-2 py-1 text-meta font-semibold ${color}`}>
      {status}
    </span>
  );
}
