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
   showing the configured base URL and connection state. Read-only: there
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
      description="Discovered services and their connection state. Configuration lives in config.yaml — Handoffarr does not currently expose write endpoints."
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
      <p
        className="truncate text-meta text-text-muted"
        title={probe.url || undefined}
      >
        {probe.url || (enabled ? "No URL configured" : "Not configured")}
      </p>
      {probe.ok === false && probe.error ? (
        <p className="text-meta text-critical">{probe.error}</p>
      ) : null}
      {probe.warnings && probe.warnings.length > 0 ? (
        <p className="text-meta text-caution">
          {probe.warnings.length} warning
          {probe.warnings.length === 1 ? "" : "s"}
        </p>
      ) : null}
    </div>
  );
}
