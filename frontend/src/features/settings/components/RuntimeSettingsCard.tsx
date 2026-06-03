import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import type { StorageResponse } from "@/api/storageApi";
import { formatBytes } from "@/lib/formatBytes";
import { SettingsCard, SettingsRow } from "./SettingsCard";

interface RuntimeSettingsCardProps {
  storage: StorageResponse | undefined;
  isLoading: boolean;
  isError: boolean;
}

interface StorageThresholdSummary {
  warning_free_bytes?: number | null;
  critical_free_bytes?: number | null;
  retained_bytes_threshold?: number | null;
  completed_torrent_threshold?: number | null;
}

/* Runtime Settings.

   The only operational limits the backend exposes today are the storage
   thresholds inside /api/storage. Poll interval and queue settings live in
   config.yaml but are not surfaced through any endpoint, so they are
   intentionally omitted (see backend gaps in the sprint summary). */
export function RuntimeSettingsCard({
  storage,
  isLoading,
  isError,
}: RuntimeSettingsCardProps) {
  const summary = storage?.summary as
    | (StorageResponse["summary"] & StorageThresholdSummary)
    | undefined;
  const hasThresholds =
    summary !== undefined &&
    (summary.warning_free_bytes != null ||
      summary.critical_free_bytes != null ||
      summary.retained_bytes_threshold != null ||
      summary.completed_torrent_threshold != null);

  return (
    <SettingsCard
      id="settings-runtime"
      title="Runtime Limits"
      description="Operational thresholds reported by the storage subsystem."
    >
      {isLoading ? (
        <LoadingState rows={2} label="Loading runtime limits" />
      ) : isError ? (
        <ErrorState
          title="Couldn't load runtime limits"
          description="The /api/storage endpoint is unreachable."
        />
      ) : !hasThresholds || !summary ? (
        <EmptyState
          title="No runtime thresholds reported"
          description="Storage thresholds are not configured."
        />
      ) : (
        <dl className="flex flex-col gap-3">
          <SettingsRow
            label="Storage — warning threshold"
            value={formatBytes(summary.warning_free_bytes ?? null)}
            hint="Free space below this triggers a warning."
          />
          <SettingsRow
            label="Storage — critical threshold"
            value={formatBytes(summary.critical_free_bytes ?? null)}
            hint="Free space below this triggers a critical alert."
          />
          <SettingsRow
            label="Retained torrents — size threshold"
            value={formatBytes(summary.retained_bytes_threshold ?? null)}
          />
          <SettingsRow
            label="Retained torrents — count threshold"
            value={summary.completed_torrent_threshold ?? "—"}
          />
        </dl>
      )}
    </SettingsCard>
  );
}
