import { EmptyState } from "@/components/EmptyState";
import type { ValidationResponse } from "@/api/validationApi";
import type { IntegrationStatus } from "../types";
import { StatusIcon } from "./StatusIcon";
import type { HealthStatus } from "../types";

interface RecentIssuesCardProps {
  validation: ValidationResponse | undefined;
  integrations: IntegrationStatus[];
}

interface Issue {
  key: string;
  status: HealthStatus;
  title: string;
  detail?: string | undefined;
  source: string;
}

const SEVERITY: Record<HealthStatus, number> = {
  critical: 0,
  warning: 1,
  unknown: 2,
  healthy: 3,
};

/* Recent Issues feed. No backend timestamps for issue history exist today —
   see Sprint 5 backend gap. We surface the current set of failing/warning
   signals from validation + integration probes, newest-severity-first. */
export function RecentIssuesCard({
  validation,
  integrations,
}: RecentIssuesCardProps) {
  const issues: Issue[] = [];

  for (const check of validation?.checks ?? []) {
    if (check.status === "OK") continue;
    issues.push({
      key: `validation-${check.name ?? Math.random()}`,
      status: check.status === "FAIL" ? "critical" : "warning",
      title: check.name ?? "Validation check",
      detail: check.message,
      source: "Validation",
    });
  }

  for (const integration of integrations) {
    if (integration.status === "healthy" || integration.status === "unknown") continue;
    issues.push({
      key: `integration-${integration.id}`,
      status: integration.status,
      title: integration.name,
      detail: integration.detail ?? integration.summary,
      source: "Integration",
    });
  }

  issues.sort((a, b) => SEVERITY[a.status] - SEVERITY[b.status]);

  return (
    <section
      aria-labelledby="recent-issues-title"
      className="flex flex-col gap-4 rounded-lg bg-surface p-5 shadow-elev-1"
    >
      <h3 id="recent-issues-title" className="text-subtitle text-text">
        Recent issues
      </h3>
      {issues.length === 0 ? (
        <EmptyState
          title="No active issues"
          description="Nothing is failing or warning right now."
        />
      ) : (
        <ul className="flex flex-col divide-y divide-border">
          {issues.map((issue) => (
            <li
              key={issue.key}
              className="flex items-start gap-3 py-3 first:pt-0 last:pb-0"
            >
              <StatusIcon status={issue.status} size={16} className="mt-0.5" />
              <div className="flex min-w-0 flex-1 flex-col">
                <p className="text-body text-text">{issue.title}</p>
                {issue.detail ? (
                  <p className="text-meta text-text-muted">{issue.detail}</p>
                ) : null}
                <p className="mt-1 text-meta uppercase tracking-wide text-text-subtle">
                  {issue.source}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
