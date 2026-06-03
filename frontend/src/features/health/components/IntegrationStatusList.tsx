import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import type { IntegrationStatus } from "../types";
import { StatusIcon } from "./StatusIcon";

interface IntegrationStatusListProps {
  integrations: IntegrationStatus[];
  isLoading: boolean;
}

/* Mockups §7 — bordered tile group, rows separated by 1px border. Entire tile
   is the click target navigating to Integration Detail. Read-only per Sprint 5
   brief: no [Fix] / repair / mutation buttons are rendered. */
export function IntegrationStatusList({
  integrations,
  isLoading,
}: IntegrationStatusListProps) {
  return (
    <section
      aria-labelledby="integration-list-title"
      className="flex flex-col gap-3"
    >
      <h3
        id="integration-list-title"
        className="text-subtitle text-text"
      >
        Integrations
      </h3>

      {isLoading && integrations.length === 0 ? (
        <LoadingState rows={4} label="Loading integrations" />
      ) : integrations.length === 0 ? (
        <EmptyState
          title="No integrations discovered"
          description="The backend has not reported any integration probes yet."
        />
      ) : (
        <ul className="flex flex-col divide-y divide-border overflow-hidden rounded-lg border border-border bg-surface">
          {integrations.map((integration) => (
            <li key={integration.id}>
              <Link
                to={`/health/integrations/${integration.id}`}
                className="flex items-start gap-4 px-5 py-4 transition-colors duration-fast ease-out hover:bg-surface-raised focus-visible:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
                aria-label={`${integration.name} — ${integration.summary}`}
              >
                <StatusIcon status={integration.status} className="mt-0.5" />
                <div className="flex min-w-0 flex-1 flex-col">
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <p className="text-body font-semibold text-text">
                      {integration.name}
                    </p>
                    <p className="text-meta text-text-muted">
                      {integration.summary}
                    </p>
                  </div>
                  {integration.detail ? (
                    <p className="mt-1 text-meta text-text-muted">
                      {integration.detail}
                    </p>
                  ) : null}
                </div>
                <ChevronRight
                  size={18}
                  className="mt-1 shrink-0 text-text-subtle"
                  aria-hidden="true"
                />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
