import { useRefreshPreferencesStore } from "@/app/stores/useRefreshPreferencesStore";
import { SettingsCard } from "./SettingsCard";

const controls = [
  ["autoRefreshEnabled", "Auto refresh enabled", "Allow light status endpoints to refresh every minute."],
  ["refreshOnWindowFocus", "Refresh on window focus", "Refresh visible cached queries when returning to Handoffarr."],
  ["diagnosticsAutoLoad", "Diagnostics auto-load", "Load Diagnostics sections when the page opens."],
  ["heavyEndpointsManualOnly", "Heavy endpoints manual only", "Require an explicit load or refresh for debug and timeline data."],
] as const;

export function RefreshBehaviorSettingsCard() {
  const preferences = useRefreshPreferencesStore();
  const setters = {
    autoRefreshEnabled: preferences.setAutoRefreshEnabled,
    refreshOnWindowFocus: preferences.setRefreshOnWindowFocus,
    diagnosticsAutoLoad: preferences.setDiagnosticsAutoLoad,
    heavyEndpointsManualOnly: preferences.setHeavyEndpointsManualOnly,
  };

  return (
    <SettingsCard
      id="settings-refresh"
      title="Refresh behavior"
      description="Per-device preferences stored in this browser."
    >
      {controls.map(([key, label, hint]) => (
        <label key={key} className="flex cursor-pointer items-start justify-between gap-5 border-t border-border pt-3 first:border-t-0 first:pt-0">
          <span className="flex flex-col gap-1">
            <span className="text-body font-semibold text-text">{label}</span>
            <span className="text-meta text-text-muted">{hint}</span>
          </span>
          <input
            type="checkbox"
            checked={preferences[key]}
            onChange={(event) => setters[key](event.target.checked)}
            className="h-5 w-5 shrink-0 accent-accent"
          />
        </label>
      ))}
    </SettingsCard>
  );
}
