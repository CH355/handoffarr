import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import type { AppHealth } from "@/api/settingsApi";
import { SettingsCard, SettingsRow } from "./SettingsCard";

interface GeneralSettingsCardProps {
  health: AppHealth | undefined;
  isLoading: boolean;
  isError: boolean;
}

/* General Settings — non-editable.

   The backend exposes /api/health which carries config presence. There is
   no endpoint for runtime mode, environment, or app-level version, so the
   card surfaces what the backend actually returns and avoids inventing
   fields. */
export function GeneralSettingsCard({
  health,
  isLoading,
  isError,
}: GeneralSettingsCardProps) {
  return (
    <SettingsCard
      id="settings-general"
      title="General"
      description="How Handoffarr is wired up at runtime. Read-only — these values come straight from the backend."
    >
      {isLoading ? (
        <LoadingState rows={2} label="Loading general settings" />
      ) : isError || !health ? (
        <ErrorState
          title="Couldn't load runtime status"
          description="The /api/health endpoint is unreachable."
        />
      ) : (
        <dl className="flex flex-col gap-3">
          <SettingsRow
            label="Configuration file"
            value={
              <span
                className={
                  health.config_present
                    ? "text-success"
                    : "text-caution"
                }
              >
                {health.config_present ? "Loaded" : "Missing"}
              </span>
            }
            hint={
              health.config_present
                ? "config.yaml found and parsed."
                : "Handoffarr is running in degraded mode until config.yaml is present."
            }
          />
          <SettingsRow
            label="Service status"
            value={health.status === "ok" ? "Running" : health.status}
            hint="Reported by /api/health."
          />
        </dl>
      )}
    </SettingsCard>
  );
}
