import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import {
  getExecutionJob,
  getExecutionJobTimeline,
  approveExecutionJob,
  cancelExecutionJob,
  retryExecutionJob,
  type ExecutionJob,
} from "@/api/executionEngineApi";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContainer } from "@/components/PageContainer";
import { useMutation, useQueryClient } from "@tanstack/react-query";

export function ExecutionDetailPage() {
  const { executionId = "" } = useParams();
  const queryClient = useQueryClient();
  const job = useQuery({
    queryKey: ["execution-engine", "job", executionId],
    queryFn: () => getExecutionJob(executionId),
    enabled: Boolean(executionId),
  });
  const timeline = useQuery({
    queryKey: ["execution-engine", "timeline", executionId],
    queryFn: () => getExecutionJobTimeline(executionId),
    enabled: Boolean(executionId),
  });

  const approve = useMutation({
    mutationFn: () => approveExecutionJob(executionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["execution-engine"] });
    },
  });
  const cancel = useMutation({
    mutationFn: () => cancelExecutionJob(executionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["execution-engine"] });
    },
  });
  const retry = useMutation({
    mutationFn: () => retryExecutionJob(executionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["execution-engine"] });
    },
  });

  if (job.isLoading) {
    return (
      <PageContainer title="Execution Detail">
        <LoadingState label="Loading execution" rows={6} />
      </PageContainer>
    );
  }
  if (job.isError || !job.data) {
    return (
      <PageContainer title="Execution Detail">
        <ErrorState
          title="Execution unavailable"
          description="This execution job could not be loaded."
        />
      </PageContainer>
    );
  }

  const data = job.data;

  return (
    <PageContainer
      title="Execution Detail"
      description={data.execution_id}
    >
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap gap-2">
          <Link to="/execution-center" className="text-accent">
            ← Execution Center
          </Link>
          {data.status === "Pending" && (
            <button
              type="button"
              disabled={approve.isPending}
              onClick={() => approve.mutate()}
              className="ml-auto rounded-md bg-accent px-4 py-2 text-body font-semibold text-accent-on disabled:opacity-60"
            >
              Approve
            </button>
          )}
          {data.status === "Running" && (
            <button
              type="button"
              disabled={cancel.isPending}
              onClick={() => cancel.mutate()}
              className="ml-auto rounded-md bg-caution px-4 py-2 text-body font-semibold text-text disabled:opacity-60"
            >
              Cancel
            </button>
          )}
          {(data.status === "Failed" || data.status === "Cancelled") && (
            <button
              type="button"
              disabled={retry.isPending}
              onClick={() => retry.mutate()}
              className="ml-auto rounded-md bg-accent px-4 py-2 text-body font-semibold text-accent-on disabled:opacity-60"
            >
              Retry
            </button>
          )}
        </div>

        <Section title="Summary">
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Status" value={data.status} />
            <Metric label="Mode" value={data.mode} />
            <Metric label="Plan" value={data.plan_id} />
            <Metric label="Torrent" value={data.torrent_hash} />
            <Metric
              label="Step"
              value={`${data.current_step}/${data.total_steps}`}
            />
            <Metric label="Action" value={data.current_action ?? "—"} />
            <Metric label="Retries" value={String(data.retry_count)} />
            <Metric label="Max Retries" value={String(data.max_retries)} />
          </dl>
        </Section>

        {data.error && (
          <Section title="Error">
            <p className="text-body text-critical">{data.error}</p>
          </Section>
        )}

        <Section title="Timeline">
          {timeline.isLoading ? (
            <LoadingState label="Loading timeline" rows={3} />
          ) : (
            <ol className="relative ml-3 border-l border-border pl-6">
              {(timeline.data?.timeline ?? []).map((event, index) => (
                <li key={`${event.type}:${index}`} className="pb-5">
                  <span className="absolute -left-1.5 mt-1 h-3 w-3 rounded-full bg-accent" />
                  <time className="text-meta text-text-muted">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </time>
                  <p className="font-semibold text-text">{event.label}</p>
                  {event.details ? (
                    <pre className="mt-1 text-meta text-text-muted">
                      {JSON.stringify(event.details, null, 2)}
                    </pre>
                  ) : null}
                </li>
              ))}
            </ol>
          )}
        </Section>

        <Section title="Audit Log">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] text-left text-body">
              <thead className="border-b border-border text-meta uppercase text-text-subtle">
                <tr>
                  {["Step", "Action", "Who", "When", "What", "Result", "Duration"].map(
                    (h) => (
                      <th key={h} className="p-3">
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.audit_log.map((entry) => (
                  <tr key={entry.audit_id}>
                    <td className="p-3">{entry.step_number}</td>
                    <td className="p-3">{entry.action_type}</td>
                    <td className="p-3">{entry.who ?? "system"}</td>
                    <td className="p-3 text-meta">
                      {new Date(entry.when).toLocaleString()}
                    </td>
                    <td className="p-3">{entry.what}</td>
                    <td className="p-3">
                      <span
                        className={
                          entry.result === "success"
                            ? "text-success"
                            : entry.result === "failure"
                              ? "text-critical"
                              : "text-text-muted"
                        }
                      >
                        {entry.result}
                      </span>
                    </td>
                    <td className="p-3">{entry.duration_ms} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        <Section title="Results">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left text-body">
              <thead className="border-b border-border text-meta uppercase text-text-subtle">
                <tr>
                  {["Step", "Action", "Success", "Duration", "Retries", "Error"].map(
                    (h) => (
                      <th key={h} className="p-3">
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.results.map((result, idx) => (
                  <tr key={idx}>
                    <td className="p-3">{result.step_number}</td>
                    <td className="p-3">{result.action_type}</td>
                    <td className="p-3">
                      {result.success ? (
                        <span className="text-success">Yes</span>
                      ) : (
                        <span className="text-critical">No</span>
                      )}
                    </td>
                    <td className="p-3">{result.duration_ms} ms</td>
                    <td className="p-3">{result.retry_count}</td>
                    <td className="p-3 text-critical">{result.error ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      </div>
    </PageContainer>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg bg-surface p-5 shadow-elev-1">
      <h2 className="mb-4 text-subtitle text-text">{title}</h2>
      {children}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-meta uppercase text-text-subtle">{label}</dt>
      <dd className="mt-1 text-body font-semibold text-text">{value}</dd>
    </div>
  );
}
