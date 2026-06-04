import { useSettingsData } from "./hooks/useSettingsData";
import { GeneralSettingsCard } from "./components/GeneralSettingsCard";
import { IntegrationSettingsCard } from "./components/IntegrationSettingsCard";
import { CleanupSettingsCard } from "./components/CleanupSettingsCard";
import { RuntimeSettingsCard } from "./components/RuntimeSettingsCard";
import { AboutCard } from "./components/AboutCard";
import { ModeSettingsCard } from "./components/ModeSettingsCard";
import { DiagnosticsSettingsCard } from "./components/DiagnosticsSettingsCard";
import { useModeStore } from "@/app/stores/useModeStore";

/* Settings remains a configuration visibility surface. Sprint 7 adds only
   the client-side Mode control and Expert-gated Diagnostics entry. */
export function SettingsPage() {
  const mode = useModeStore((s) => s.mode);
  const { health, qbit, radarr, seerr, storage, executions } = useSettingsData();

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

      <GeneralSettingsCard
        health={health.data}
        isLoading={health.isLoading}
        isError={health.isError}
      />

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

      <CleanupSettingsCard
        config={executions.data?.config}
        isLoading={executions.isLoading}
        isError={executions.isError}
      />

      <RuntimeSettingsCard
        storage={storage.data}
        isLoading={storage.isLoading}
        isError={storage.isError}
      />

      <ModeSettingsCard />

      {mode === "expert" ? <DiagnosticsSettingsCard /> : null}

      <AboutCard />
    </section>
  );
}
