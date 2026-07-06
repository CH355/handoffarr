import { useQuery } from "@tanstack/react-query";
import { getRecoveryAgentStatus } from "@/api/recoveryAgentApi";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContainer } from "@/components/PageContainer";

export function RecoveryAgentPage() {
  const query = useQuery({
    queryKey: ["recovery-agent", "status"],
    queryFn: getRecoveryAgentStatus,
    refetchInterval: 60_000,
  });
  return (
    <PageContainer
      title="Recovery Agent"
      description="Background, plan-only recovery orchestration."
    >
      {query.isLoading ? (
        <LoadingState label="Loading Recovery Agent" rows={4} />
      ) : query.isError || !query.data ? (
        <ErrorState
          title="Recovery Agent unavailable"
          description="Status could not be loaded."
        />
      ) : (
        <div className="flex flex-col gap-4">
          <section className="rounded-lg bg-accent-quiet p-5">
            <p className="text-meta font-semibold uppercase text-accent">
              Agent status
            </p>
            <p className="mt-1 text-title text-text">
              {query.data.enabled ? query.data.agent_status : "Disabled"}
            </p>
            <p className="mt-2 text-body text-text-muted">
              Last evaluation: {formatTime(query.data.last_evaluation_at)} · Next
              evaluation: {formatTime(query.data.next_evaluation_at)}
            </p>
          </section>
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Metric label="Jobs evaluated" value={query.data.jobs_evaluated} />
            <Metric label="Dead torrents" value={query.data.dead_torrents} />
            <Metric label="Plans generated" value={query.data.plans_generated} />
            <Metric
              label="Average confidence"
              value={`${query.data.average_confidence}%`}
            />
            <Metric
              label="Evaluation duration"
              value={`${query.data.evaluation_duration_ms} ms`}
            />
            <Metric
              label="Interval"
              value={`${query.data.interval_minutes} min`}
            />
          </dl>
        </div>
      )}
    </PageContainer>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-surface p-5 shadow-elev-1">
      <dt className="text-meta text-text-muted">{label}</dt>
      <dd className="mt-1 text-title tabular-nums text-text">{value}</dd>
    </div>
  );
}

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : "Not yet";
}
