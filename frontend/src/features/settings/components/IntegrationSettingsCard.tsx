import { LoadingState } from "@/components/LoadingState";
import { EmptyState } from "@/components/EmptyState";
import type { IntegrationProbe } from "@/api/healthApi";
import { SettingsCard } from "./SettingsCard";

interface IntegrationRow {
  id: string;
  name: string;
  probe: IntegrationProbe | undefined;
  isLoading: boolean;
  isError: boolean;
}

interface IntegrationSettingsCardProps {
  rows: IntegrationRow[];
}

/* Integration Settings.

   Lists every integration probe exposed by app/main.py debug endpoints,
   showing friendly connection and enablement state. Read-only: there
   is no PUT/POST endpoint for changing integration credentials, so the
   mockup's [Edit] button is omitted per the sprint brief ("Editable mode
   only appears when supported"). */
export function IntegrationSettingsCard({ rows }: IntegrationSettingsCardProps) {
  const allLoading = rows.every((r) => r.isLoading);
  const visibleRows = rows.filter((r) => !r.isError || r.probe !== undefined);

  return (
    <SettingsCard
      id="settings-integrations"
      title="Integrations"
      description="Discovered services and whether Handoffarr can use them. Detailed warnings live in Health."
    >
      {allLoading ? (
        <LoadingState rows={3} label="Loading integrations" />
      ) : visibleRows.length === 0 ? (
        <EmptyState
          title="No integrations discovered"
          description="The backend has not reported any integration probes yet."
        />
      ) : (
        <ul className="flex flex-col divide-y divide-border overflow-hidden rounded-md border border-border">
          {rows.map((row) => (
            <li key={row.id} className="px-4 py-3">
              <IntegrationLine row={row} />
            </li>
          ))}
        </ul>
      )}
    </SettingsCard>
  );
}

function IntegrationLine({ row }: { row: IntegrationRow }) {
  if (row.isLoading) {
    return (
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-body font-semibold text-text">{row.name}</p>
        <span className="text-meta text-text-muted">Probing…</span>
      </div>
    );
  }

  if (row.isError || !row.probe) {
    return (
      <div className="flex flex-col gap-1">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-body font-semibold text-text">{row.name}</p>
          <span className="text-meta text-critical">Probe failed</span>
        </div>
        <p className="text-meta text-text-muted">
          The debug endpoint returned an error.
        </p>
      </div>
    );
  }

  const probe = row.probe;
  const enabled = probe.enabled !== false;
  const status = !enabled
    ? { label: "Disabled", className: "text-text-muted" }
    : probe.ok === true
      ? { label: "Connected", className: "text-success" }
      : probe.ok === false
        ? { label: "Unreachable", className: "text-critical" }
        : { label: "Unknown", className: "text-text-muted" };

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-body font-semibold text-text">{row.name}</p>
        <span className={`text-meta uppercase tracking-wide ${status.className}`}>
          {status.label}
        </span>
      </div>
      <p className="text-meta text-text-muted">
        {enabled ? integrationSummary(probe) : "Not configured"}
      </p>
    </div>
  );
}
function integrationSummary(probe: IntegrationProbe): string {
  if (probe.ok === true) {
    if (typeof probe.record_count === "number") {
      return `${probe.record_count} records visible`;
    }
    if (typeof probe.torrent_count === "number") {
      return `${probe.torrent_count} torrents visible`;
    }
    return "Connection ready";
  }
  if (probe.ok === false) return "Needs attention in Health";
  return "Status not reported";
}

