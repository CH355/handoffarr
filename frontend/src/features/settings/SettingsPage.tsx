import { useSettingsData } from "./hooks/useSettingsData";
import { GeneralSettingsCard } from "./components/GeneralSettingsCard";
import { IntegrationSettingsCard } from "./components/IntegrationSettingsCard";
import { CleanupSettingsCard } from "./components/CleanupSettingsCard";
import { RuntimeSettingsCard } from "./components/RuntimeSettingsCard";
import { AboutCard } from "./components/AboutCard";
import { AuditProfiler, useRouteAudit } from "@/perf/audit";

/* Sprint 6 Settings page.

   Configuration visibility surface only. Every value rendered originates
   from an endpoint that already exists in app/main.py — no invented
   fields, no fabricated save endpoints, no Diagnostics / Expert chrome
   (those are out of scope per the sprint brief). All cards degrade
   independently per frontend-implementation-spec-v1.md §7.2. */
export function SettingsPage() {
  const { health, qbit, radarr, seerr, storage, executions } = useSettingsData();
  const dataReady =
    !health.isLoading &&
    !qbit.isLoading &&
    !radarr.isLoading &&
    !seerr.isLoading &&
    !storage.isLoading &&
    !executions.isLoading;
  useRouteAudit("Settings", dataReady, {
    health_status: health.status,
    qbit_status: qbit.status,
    radarr_status: radarr.status,
    seerr_status: seerr.status,
    storage_status: storage.status,
    executions_status: executions.status,
  });

  return (
    <section
      aria-labelledby="settings-title"
      className="mx-auto flex w-full max-w-[720px] flex-col gap-6"
    >
      <header className="flex flex-col gap-2">
        <h1 id="settings-title" className="text-title text-text">
          Settings
        </h1>
        <p className="max-w-[60ch] text-body text-text-muted">
          How Handoffarr is configured, which integrations are wired up, where
          data comes from, and what operational limits are in effect.
        </p>
      </header>

      <AuditProfiler id="Settings.GeneralSettingsCard">
        <GeneralSettingsCard
          health={health.data}
          isLoading={health.isLoading}
          isError={health.isError}
        />
      </AuditProfiler>

      <AuditProfiler id="Settings.IntegrationSettingsCard">
        <IntegrationSettingsCard
          rows={[
            {
              id: "qbittorrent",
              name: "qBittorrent",
              probe: qbit.data,
              isLoading: qbit.isLoading,
              isError: qbit.isError,
            },
            {
              id: "radarr",
              name: "Radarr",
              probe: radarr.data,
              isLoading: radarr.isLoading,
              isError: radarr.isError,
            },
            {
              id: "seerr",
              name: "Overseerr",
              probe: seerr.data,
              isLoading: seerr.isLoading,
              isError: seerr.isError,
            },
          ]}
        />
      </AuditProfiler>

      <AuditProfiler id="Settings.CleanupSettingsCard">
        <CleanupSettingsCard
          config={executions.data?.config}
          isLoading={executions.isLoading}
          isError={executions.isError}
        />
      </AuditProfiler>

      <AuditProfiler id="Settings.RuntimeSettingsCard">
        <RuntimeSettingsCard
          storage={storage.data}
          isLoading={storage.isLoading}
          isError={storage.isError}
        />
      </AuditProfiler>

      <AuditProfiler id="Settings.AboutCard">
        <AboutCard />
      </AuditProfiler>
    </section>
  );
}
