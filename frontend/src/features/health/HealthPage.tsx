import { useMemo } from "react";
import { useHealthData } from "./hooks/useHealthData";
import {
  buildIntegrations,
  countByStatus,
  rollupStatus,
} from "./integrations";
import { HealthSummaryBanner } from "./components/HealthSummaryBanner";
import { ValidationStatusCard } from "./components/ValidationStatusCard";
import { IntegrationStatusList } from "./components/IntegrationStatusList";
import { StorageStatusCard } from "./components/StorageStatusCard";
import { RecentIssuesCard } from "./components/RecentIssuesCard";

/* Sprint 5 Health screen. Monitoring + visibility only — no mutation
   buttons. State handling is per-card; no full-page spinner. */
export function HealthPage() {
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

  const counts = useMemo(() => countByStatus(integrations), [integrations]);
  const overall = useMemo(() => rollupStatus(integrations), [integrations]);

  const lastValidation = validation.dataUpdatedAt
    ? new Date(validation.dataUpdatedAt).toLocaleString()
    : undefined;

  const probesLoading =
    qbit.isLoading || radarr.isLoading || seerr.isLoading || storage.isLoading;

  return (
    <section
      aria-labelledby="health-title"
      className="mx-auto flex w-full max-w-page flex-col gap-6"
    >
      <header className="flex flex-col gap-2">
        <h1 id="health-title" className="text-title text-text">
          Health
        </h1>
        <p className="max-w-[60ch] text-body text-text-muted">
          Is Handoffarr healthy? Which integrations are healthy? What requires
          attention? This page is read-only.
        </p>
      </header>

      <HealthSummaryBanner
        overall={overall}
        counts={counts}
        lastValidation={lastValidation}
      />

      <ValidationStatusCard
        data={validation.data}
        isLoading={validation.isLoading}
        isError={validation.isError}
      />

      <IntegrationStatusList
        integrations={integrations}
        isLoading={probesLoading}
      />

      <StorageStatusCard
        data={storage.data}
        isLoading={storage.isLoading}
        isError={storage.isError}
      />

      <RecentIssuesCard
        validation={validation.data}
        integrations={integrations}
      />
    </section>
  );
}
