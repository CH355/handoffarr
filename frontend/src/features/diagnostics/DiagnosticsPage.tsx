import { useMemo } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, ChevronDown } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { ExpertChip } from "@/components/foundation/ExpertChip";
import { buildIntegrations, rollupStatus } from "@/features/health/integrations";
import { StatusIcon, statusLabel } from "@/features/health/components/StatusIcon";
import type { HealthStatus, IntegrationStatus } from "@/features/health/types";
import { formatBytes } from "@/lib/formatBytes";
import { formatRelativeTime } from "@/lib/formatRelativeTime";
import type { ValidationStatus } from "@/api/validationApi";
import type { CleanupExecutionRow } from "@/api/cleanupApi";
import type { MediaTimeline } from "@/api/timelineApi";
import { useDiagnosticsData } from "./hooks/useDiagnosticsData";

function validationStatus(status: ValidationStatus | undefined): HealthStatus {
  if (status === "OK") return "healthy";
  if (status === "WARN") return "warning";
  if (status === "FAIL") return "critical";
  return "unknown";
}

function executionStatus(status: string | null | undefined): HealthStatus {
  const value = status?.toLowerCase() ?? "";
  if (value.includes("complete")) return "healthy";
  if (value.includes("fail") || value.includes("block")) return "critical";
  if (value) return "warning";
  return "unknown";
}

function Card({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-4 rounded-lg bg-surface p-5 shadow-elev-1">
      <h2 id={id} className="text-subtitle text-text">{title}</h2>
      {children}
    </section>
  );
}

function Overview({
  collectors,
  validation,
  execution,
}: {
  collectors: IntegrationStatus[];
  validation: HealthStatus;
  execution: HealthStatus;
}) {
  const overall = rollupStatus([...collectors, {
    id: "validation", name: "Validation", status: validation, summary: "", warnings: [], available: true,
  }, {
    id: "execution", name: "Execution", status: execution, summary: "", warnings: [], available: true,
  }]);
  const rows = [
    ["Overall status", statusLabel(overall), overall],
    ["Collectors", `${collectors.length} discovered`, rollupStatus(collectors)],
    ["Validation", statusLabel(validation), validation],
    ["Last execution", statusLabel(execution), execution],
  ] as const;
  return (
    <Card id="diagnostics-overview" title="System overview">
      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {rows.map(([label, value, status]) => (
          <div key={label} className="rounded-md border border-border p-4">
            <dt className="text-meta uppercase tracking-wide text-text-muted">{label}</dt>
            <dd className="mt-2 flex items-center gap-2 text-body font-semibold text-text">
              <StatusIcon status={status} size={16} /> {value}
            </dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

function CollectorStatus({
  collectors,
  isLoading,
  lastResults,
}: {
  collectors: IntegrationStatus[];
  isLoading: boolean;
  lastResults: Record<string, number>;
}) {
  return (
    <Card id="diagnostics-collectors" title="Collector status">
      {isLoading && collectors.length === 0 ? <LoadingState rows={3} label="Loading collector status" /> :
      collectors.length === 0 ? <EmptyState title="No collectors discovered" description="No collector data is currently available." /> :
      <ul className="grid gap-3 md:grid-cols-2">
        {collectors.map((collector) => (
          <li key={collector.id} className="flex flex-col gap-3 rounded-md border border-border p-4">
            <div className="flex items-center justify-between gap-3">
              <span className="text-body font-semibold text-text">{collector.name}</span>
              <span className="flex items-center gap-2 text-meta text-text-muted">
                <StatusIcon status={collector.status} size={15} /> {statusLabel(collector.status)}
              </span>
            </div>
            <dl className="grid grid-cols-2 gap-2 text-meta">
              <div><dt className="text-text-muted">Last result</dt><dd className="text-text">{formatRelativeTime(lastResults[collector.id])}</dd></div>
              <div><dt className="text-text-muted">Warnings</dt><dd className="text-text">{collector.warnings.length}</dd></div>
            </dl>
            <p className="text-meta text-text-muted">{collector.summary}</p>
          </li>
        ))}
      </ul>}
    </Card>
  );
}

function ValidationDetails({ data, isLoading, isError }: ReturnType<typeof useDiagnosticsData>["validation"]) {
  return (
    <Card id="diagnostics-validation" title="Validation details">
      {isLoading ? <LoadingState rows={3} label="Loading validation details" /> :
      isError || !data ? <ErrorState title="Couldn't load validation details" description="The validation endpoint is unreachable." /> :
      data.checks.length === 0 ? <EmptyState title="No validation checks" description="Validation returned no checks." /> :
      <div className="flex flex-col gap-2">
        {data.checks.map((check, index) => {
          const status = validationStatus(check.status);
          return (
            <details key={`${check.name}-${index}`} className="group rounded-md border border-border">
              <summary className="flex cursor-pointer list-none items-start gap-3 px-4 py-3">
                <StatusIcon status={status} size={16} className="mt-0.5" />
                <span className="min-w-0 flex-1">
                  <span className="block text-body font-semibold text-text">{check.name ?? "Validation check"}</span>
                  <span className="block text-meta text-text-muted">{check.reason ?? check.message ?? statusLabel(status)}</span>
                </span>
                <ChevronDown size={17} aria-hidden="true" className="mt-0.5 text-text-muted transition-transform group-open:rotate-180" />
              </summary>
              <div className="border-t border-border px-4 py-3 text-meta text-text-muted">
                {check.evidence && Object.keys(check.evidence).length > 0 ? (
                  <dl className="grid gap-2 sm:grid-cols-2">
                    {Object.entries(check.evidence).map(([key, value]) => (
                      <div key={key}><dt className="font-semibold text-text">{key.replaceAll("_", " ")}</dt><dd>{String(value)}</dd></div>
                    ))}
                  </dl>
                ) : "No additional evidence reported."}
              </div>
            </details>
          );
        })}
      </div>}
    </Card>
  );
}

function ExecutionHistory({ data, isLoading, isError }: ReturnType<typeof useDiagnosticsData>["executions"]) {
  const executions = data?.executions ?? [];
  return (
    <Card id="diagnostics-executions" title="Cleanup execution history">
      {isLoading ? <LoadingState rows={3} label="Loading cleanup executions" /> :
      isError ? <ErrorState title="Couldn't load cleanup executions" description="The execution history endpoint is unreachable." /> :
      executions.length === 0 ? <EmptyState title="No cleanup executions" description="No cleanup execution history has been recorded." /> :
      <ul className="flex flex-col divide-y divide-border rounded-md border border-border">
        {executions.slice(0, 10).map((execution: CleanupExecutionRow) => (
          <li key={execution.execution_id} className="grid gap-2 px-4 py-3 sm:grid-cols-[1fr_auto_auto] sm:items-center">
            <div className="min-w-0">
              <p className="truncate text-body font-semibold text-text">{execution.media_title ?? "Cleanup execution"}</p>
              <p className="text-meta text-text-muted">{formatRelativeTime(execution.completed_at ?? execution.created_at)}</p>
            </div>
            <span className="text-meta text-text-muted">1 item · {formatBytes(execution.recoverable_bytes)}</span>
            <span className="flex items-center gap-2 text-meta text-text">
              <StatusIcon status={executionStatus(execution.execution_status)} size={15} />
              {execution.execution_status ?? "Unknown"}
            </span>
          </li>
        ))}
      </ul>}
    </Card>
  );
}

function activitySummary(timeline: MediaTimeline): string {
  const latest = [...timeline.stages].sort((a, b) => (b.timestamp ?? "").localeCompare(a.timestamp ?? ""))[0];
  if (!latest) return timeline.outcome ?? "Timeline updated";
  if (latest.stage === "Import") return `${timeline.media_title ?? "Item"} was imported`;
  if (latest.stage === "Cleanup") return `${timeline.media_title ?? "Item"} cleanup was reviewed`;
  return `${timeline.media_title ?? "Item"}: ${latest.stage ?? "Activity"} ${latest.stage_status?.toLowerCase() ?? "updated"}`;
}

interface ActivityItem {
  id: string;
  timestamp: string | number | null | undefined;
  status: HealthStatus;
  summary: string;
  detail: string;
}

function RecentActivity({
  timeline,
  executions,
  validation,
}: {
  timeline: ReturnType<typeof useDiagnosticsData>["timeline"];
  executions: ReturnType<typeof useDiagnosticsData>["executions"];
  validation: ReturnType<typeof useDiagnosticsData>["validation"];
}) {
  const items = useMemo<ActivityItem[]>(() => {
    const timelineItems = (timeline.data?.recent_timelines ?? []).map((item) => ({
      id: item.timeline_id ?? item.media_id ?? activitySummary(item),
      timestamp: item.latest_timestamp,
      status: (item.blocked_at ? "warning" : item.outcome === "Complete" ? "healthy" : "unknown") as HealthStatus,
      summary: activitySummary(item),
      detail: item.blocked_at ? `Blocked at ${item.blocked_at}` : `Outcome: ${item.outcome ?? "Pending"}`,
    }));
    const executionItems = (executions.data?.executions ?? []).map((item) => ({
      id: item.execution_id,
      timestamp: item.completed_at ?? item.created_at,
      status: executionStatus(item.execution_status),
      summary: `Cleanup execution ${item.execution_status?.toLowerCase() ?? "updated"}`,
      detail: `${item.media_title ?? "Cleanup item"} · ${formatBytes(item.recoverable_bytes)}`,
    }));
    const validationItem: ActivityItem[] = validation.data ? [{
      id: `validation-${validation.dataUpdatedAt}`,
      timestamp: validation.dataUpdatedAt,
      status: validationStatus(validation.data.status),
      summary: `Validation reported ${validation.data.status}`,
      detail: `${validation.data.checks.length} checks evaluated`,
    }] : [];
    return [...timelineItems, ...executionItems, ...validationItem]
      .sort((a, b) => new Date(b.timestamp ?? 0).getTime() - new Date(a.timestamp ?? 0).getTime())
      .slice(0, 16);
  }, [timeline.data, executions.data, validation.data, validation.dataUpdatedAt]);
  const isLoading = timeline.isLoading || executions.isLoading || validation.isLoading;
  const isError = timeline.isError && executions.isError && validation.isError;
  return (
    <Card id="diagnostics-activity" title="Recent activity timeline">
      {isLoading ? <LoadingState rows={4} label="Loading recent activity" /> :
      isError ? <ErrorState title="Couldn't load recent activity" description="The timeline endpoint is unreachable." /> :
      items.length === 0 ? <EmptyState title="No recent activity" description="No lifecycle timeline activity has been recorded." /> :
      <ol className="flex flex-col divide-y divide-border rounded-md border border-border">
        {items.map((item) => {
          return (
            <li key={item.id} className="flex items-start gap-3 px-4 py-3">
              <StatusIcon status={item.status} size={16} className="mt-0.5" />
              <div className="min-w-0 flex-1">
                <p className="text-body text-text">{item.summary}</p>
                <p className="text-meta text-text-muted">{item.detail} · {formatRelativeTime(item.timestamp)}</p>
              </div>
            </li>
          );
        })}
      </ol>}
    </Card>
  );
}

export function DiagnosticsPage() {
  const data = useDiagnosticsData();
  const collectors = useMemo(() => {
    const built = buildIntegrations({
      qbit: data.qbit.data,
      radarr: data.radarr.data,
      seerr: data.seerr.data,
      storage: data.storage.data,
      imports: data.imports.data,
    });
    const stateWarnings = (data.states.data?.classification_counts?.stalled ?? 0)
      + (data.states.data?.classification_counts?.error ?? 0);
    return built.map((collector) => collector.id === "qbittorrent" && stateWarnings > 0 ? {
      ...collector,
      status: (collector.status === "critical" ? "critical" : "warning") as HealthStatus,
      summary: `${stateWarnings} torrents stalled or missing files`,
      warnings: Array.from({ length: stateWarnings }, () => "Torrent state requires attention"),
    } : collector);
  }, [data.qbit.data, data.radarr.data, data.seerr.data, data.storage.data, data.imports.data, data.states.data]);
  const latestExecution = data.executions.data?.executions[0];
  const lastResults = {
    qbittorrent: Math.max(data.qbit.dataUpdatedAt, data.states.dataUpdatedAt),
    radarr: data.radarr.dataUpdatedAt,
    seerr: data.seerr.dataUpdatedAt,
    storage: data.storage.dataUpdatedAt,
    imports: data.imports.dataUpdatedAt,
  };

  return (
    <section aria-labelledby="diagnostics-title" className="mx-auto flex w-full max-w-page flex-col gap-6">
      <header className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-4">
          <Link to="/settings" className="inline-flex items-center gap-2 text-body font-semibold text-text-muted hover:text-text">
            <ArrowLeft size={17} aria-hidden="true" /> Settings
          </Link>
          <ExpertChip />
        </div>
        <div className="flex flex-col gap-2">
          <h1 id="diagnostics-title" className="text-title text-text">Diagnostics</h1>
          <p className="max-w-[60ch] text-body text-text-muted">Read-only operational details from Handoffarr's existing validation, collector, execution, and timeline APIs.</p>
        </div>
      </header>
      <Overview collectors={collectors} validation={validationStatus(data.validation.data?.status)} execution={executionStatus(latestExecution?.execution_status)} />
      <CollectorStatus collectors={collectors} lastResults={lastResults} isLoading={data.qbit.isLoading || data.radarr.isLoading || data.seerr.isLoading || data.storage.isLoading || data.imports.isLoading || data.states.isLoading} />
      <ValidationDetails {...data.validation} />
      <ExecutionHistory {...data.executions} />
      <RecentActivity timeline={data.timeline} executions={data.executions} validation={data.validation} />
    </section>
  );
}
