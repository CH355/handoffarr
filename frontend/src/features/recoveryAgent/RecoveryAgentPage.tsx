import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  getRecoveryAgentStatus,
  getRecoveryHistory,
  getRecoveryPlans,
  getRecoveryQueue,
} from "@/api/recoveryAgentApi";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContainer } from "@/components/PageContainer";

export function RecoveryAgentPage() {
  const query = useQuery({
    queryKey: ["recovery-agent", "status"],
    queryFn: getRecoveryAgentStatus,
  });
  const plans = useQuery({
    queryKey: ["recovery-agent", "plans"],
    queryFn: ({ signal }) => getRecoveryPlans({ limit: 5 }, signal),
  });
  const history = useQuery({
    queryKey: ["recovery-agent", "history"],
    queryFn: ({ signal }) => getRecoveryHistory({ limit: 5 }, signal),
  });
  const queue = useQuery({
    queryKey: ["recovery-agent", "queue"],
    queryFn: ({ signal }) => getRecoveryQueue({ limit: 25 }, signal),
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
            <Metric label="Jobs evaluated" value={query.data.jobs_evaluated} to="/recovery-agent/activity?status=Completed" />
            <Metric label="Dead torrents" value={query.data.dead_torrents} to="/torrents?status=dead" />
            <Metric label="Plans generated" value={query.data.plans_generated} to="/recovery-agent/plans" />
            <Metric
              label="Average confidence"
              value={`${query.data.average_confidence}%`}
              to="/recovery-agent/plans?sort=confidence"
            />
            <Metric
              label="Evaluation duration"
              value={`${query.data.evaluation_duration_ms} ms`}
              to="/recovery-agent/history"
            />
            <Metric
              label="Interval"
              value={`${query.data.interval_minutes} min`}
              to="/settings"
            />
          </dl>
          <section className="grid gap-4 lg:grid-cols-2">
            <Panel title="Current Queue" to="/recovery-agent/activity">
              {queue.isLoading ? <LoadingState label="Loading queue" rows={3} /> : ["Queued","Running","Completed","Failed","Cancelled"].map(status => <p key={status} className="flex justify-between text-body"><span className="text-text-muted">{status}</span><span>{(queue.data?.jobs ?? []).filter(job => job.status === status).length}</span></p>)}
            </Panel>
            <Panel title="Recent Plans" to="/recovery-agent/plans">
              {plans.isLoading ? <LoadingState label="Loading plans" rows={3} /> : (plans.data?.plans ?? []).slice(0,5).map(plan => <Link key={plan.id} to={`/recovery-agent/plans/${plan.id}`} className="block truncate text-body text-accent">{plan.media_title ?? plan.torrent_hash} · {plan.recommendation}</Link>)}
            </Panel>
            <Panel title="Recent Decisions" to="/recovery-agent/history">
              {history.isLoading ? <LoadingState label="Loading decisions" rows={3} /> : (history.data?.history ?? []).slice(0,5).map(decision => <p key={decision.history_id} className="text-body text-text">{decision.recommendation} · {decision.confidence}%</p>)}
            </Panel>
            <Panel title="Recent Errors" to="/recovery-agent/activity?status=Failed">
              {queue.isLoading ? <LoadingState label="Loading errors" rows={2} /> : (queue.data?.jobs ?? []).filter(job => job.error).slice(0,5).length ? (queue.data?.jobs ?? []).filter(job => job.error).slice(0,5).map(job => <p key={job.job_id} className="text-body text-critical">{job.error}</p>) : <p className="text-body text-text-muted">No recent errors.</p>}
            </Panel>
          </section>
        </div>
      )}
    </PageContainer>
  );
}

function Metric({ label, value, to }: { label: string; value: string | number; to: string }) {
  return (
    <Link to={to} className="rounded-lg bg-surface p-5 shadow-elev-1 hover:ring-2 hover:ring-accent">
      <dt className="text-meta text-text-muted">{label}</dt>
      <dd className="mt-1 text-title tabular-nums text-text">{value}</dd>
    </Link>
  );
}

function Panel({title,to,children}:{title:string;to:string;children:ReactNode}) {
  return <section className="rounded-lg bg-surface p-5 shadow-elev-1"><div className="mb-3 flex justify-between"><h2 className="text-subtitle">{title}</h2><Link to={to} className="text-meta text-accent">View all</Link></div><div className="space-y-2">{children}</div></section>;
}

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : "Not yet";
}
