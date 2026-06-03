import { useMemo } from "react";
import { Link, useParams, Navigate } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { useHealthData } from "./hooks/useHealthData";
import { buildIntegrations } from "./integrations";
import { StatusIcon, statusLabel } from "./components/StatusIcon";
import type { IntegrationStatus, HealthStatus } from "./types";
import type { ValidationResponse } from "@/api/validationApi";

const VALID_IDS = new Set([
  "qbittorrent",
  "radarr",
  "seerr",
  "storage",
  "imports",
]);

function mapValidation(s: string): HealthStatus {
  if (s === "OK") return "healthy";
  if (s === "WARN") return "warning";
  if (s === "FAIL") return "critical";
  return "unknown";
}

/* Sprint 5 Integration Detail (sub-screen of Health, route v1.1 M1).
   Read-only per Sprint 5 brief: no Test connection / Edit settings / View
   logs actions are rendered, despite Mockups §7A showing them. The brief
   explicitly forbids any mutation surface here. */
export function IntegrationDetailPage() {
  const { integrationId } = useParams<{ integrationId: string }>();
  const { validation, storage, imports, qbit, radarr, seerr } = useHealthData();

  const integrations = useMemo(
    () =>
      buildIntegrations({
        qbit: qbit.data,
        radarr: radarr.data,
        seerr: seerr.data,
        storage: storage.data,
        imports: imports.data,
      }),
    [qbit.data, radarr.data, seerr.data, storage.data, imports.data],
  );

  if (!integrationId || !VALID_IDS.has(integrationId)) {
    return <Navigate to="/health" replace />;
  }

  const probesLoading =
    qbit.isLoading || radarr.isLoading || seerr.isLoading || storage.isLoading || imports.isLoading;
  const integration = integrations.find((i) => i.id === integrationId);

  return (
    <section
      aria-labelledby="integration-detail-title"
      className="mx-auto flex w-full max-w-[720px] flex-col gap-6"
    >
      <Link
        to="/health"
        className="inline-flex w-fit items-center gap-1 text-meta text-text-muted transition-colors duration-fast ease-out hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
      >
        <ChevronLeft size={16} aria-hidden="true" />
        Health
      </Link>

      {probesLoading && !integration ? (
        <LoadingState rows={3} label="Loading integration" />
      ) : !integration ? (
        <ErrorState
          title="Integration not available"
          description="The backend did not report this integration. It may not be configured."
        />
      ) : (
        <IntegrationDetailBody
          integration={integration}
          validation={validation.data}
        />
      )}
    </section>
  );
}

function IntegrationDetailBody({
  integration,
  validation,
}: {
  integration: IntegrationStatus;
  validation: ValidationResponse | undefined;
}) {
  const related = useMemo(() => {
    if (!validation) return [];
    const needle = integration.name.toLowerCase();
    return validation.checks.filter((c) => {
      const haystack = `${c.name ?? ""} ${c.message ?? ""}`.toLowerCase();
      return haystack.includes(needle) || haystack.includes(integration.id);
    });
  }, [validation, integration]);

  return (
    <>
      <header className="flex flex-col gap-3">
        <h1
          id="integration-detail-title"
          className="text-title text-text"
        >
          {integration.name}
        </h1>
        <div className="flex flex-wrap items-center gap-3 text-body text-text-muted">
          <span className="inline-flex items-center gap-2">
            <StatusIcon status={integration.status} size={16} />
            <span className="text-text">{statusLabel(integration.status)}</span>
          </span>
          <span>·</span>
          <span>{integration.summary}</span>
        </div>
      </header>

      <section
        aria-label="Current status"
        className="flex flex-col gap-3 rounded-lg bg-surface p-5 shadow-elev-1"
      >
        <h2 className="text-subtitle text-text">Current status</h2>
        {integration.detail ? (
          <p className="text-body text-text">{integration.detail}</p>
        ) : (
          <p className="text-body text-text-muted">{integration.summary}</p>
        )}
        {integration.url ? (
          <p className="text-meta text-text-muted">
            <span className="uppercase tracking-wide">Endpoint</span>{" "}
            <code className="font-mono text-text">{integration.url}</code>
          </p>
        ) : null}
      </section>

      <section
        aria-label="Last successful contact"
        className="flex flex-col gap-2 rounded-lg bg-surface p-5 shadow-elev-1"
      >
        <h2 className="text-subtitle text-text">Last contact</h2>
        <p className="text-body text-text-muted">
          The backend does not yet persist a per-integration success or
          failure timestamp; this page reflects the most recent probe result.
        </p>
      </section>

      {integration.warnings.length > 0 ? (
        <section
          aria-label="Probe warnings"
          className="flex flex-col gap-3 rounded-lg bg-surface p-5 shadow-elev-1"
        >
          <h2 className="text-subtitle text-text">Probe warnings</h2>
          <ul className="flex flex-col divide-y divide-border">
            {integration.warnings.slice(0, 25).map((warning, idx) => (
              <li
                key={idx}
                className="flex items-start gap-3 py-2 text-meta text-text-muted first:pt-0 last:pb-0"
              >
                <StatusIcon status="warning" size={14} className="mt-0.5" />
                <span>{warning}</span>
              </li>
            ))}
          </ul>
          {integration.warnings.length > 25 ? (
            <p className="text-meta text-text-subtle">
              Showing first 25 of {integration.warnings.length} warnings.
            </p>
          ) : null}
        </section>
      ) : null}

      <section
        aria-label="Related validation"
        className="flex flex-col gap-3 rounded-lg bg-surface p-5 shadow-elev-1"
      >
        <h2 className="text-subtitle text-text">Related validation</h2>
        {related.length === 0 ? (
          <EmptyState
            title="No related checks"
            description="No validation checks reference this integration by name."
          />
        ) : (
          <ul className="flex flex-col divide-y divide-border">
            {related.map((check, idx) => {
              const status = mapValidation(check.status);
              return (
                <li
                  key={`${check.name ?? idx}-${idx}`}
                  className="flex items-start gap-3 py-3 first:pt-0 last:pb-0"
                >
                  <StatusIcon status={status} size={16} className="mt-0.5" />
                  <div className="flex min-w-0 flex-col">
                    <p className="text-body text-text">
                      {check.name ?? "Check"}
                    </p>
                    {check.message ? (
                      <p className="text-meta text-text-muted">
                        {check.message}
                      </p>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </>
  );
}
