import { CheckCircle2, AlertTriangle, AlertOctagon, HelpCircle } from "lucide-react";
import { StatTile } from "./StatTile";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { formatBytes } from "@/lib/formatBytes";
import type { StorageResponse } from "@/api/storageApi";
import type { ImportsResponse, ImportEvent } from "@/api/importsApi";
import type { ValidationResponse } from "@/api/validationApi";

interface StatTileRowProps {
  storage: {
    data: StorageResponse | undefined;
    isLoading: boolean;
    isError: boolean;
  };
  imports: {
    data: ImportsResponse | undefined;
    isLoading: boolean;
    isError: boolean;
  };
  validation: {
    data: ValidationResponse | undefined;
    isLoading: boolean;
    isError: boolean;
  };
}

function importsThisWeek(events: ImportEvent[] | undefined): number {
  if (!events || events.length === 0) return 0;
  const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000;
  let count = 0;
  for (const event of events) {
    const ts = event.import_timestamp ? Date.parse(event.import_timestamp) : NaN;
    if (Number.isFinite(ts) && ts >= cutoff) count += 1;
  }
  return count;
}

export function StatTileRow({ storage, imports, validation }: StatTileRowProps) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <StorageTile state={storage} />
      <ActivityTile state={imports} />
      <HealthTile state={validation} />
    </div>
  );
}

function StorageTile({ state }: { state: StatTileRowProps["storage"] }) {
  if (state.isLoading) return <TileSkeleton label="Storage" />;
  if (state.isError || !state.data) return <TileError label="Storage" />;
  const s = state.data.summary;
  const free = s.free_bytes;
  const total = s.total_bytes;
  const usedPct =
    free != null && total != null && total > 0
      ? ((total - free) / total) * 100
      : null;
  return (
    <StatTile
      label="Storage"
      value={free != null ? `${formatBytes(free)} free` : "—"}
      supporting={total != null ? `of ${formatBytes(total)}` : undefined}
      progressPct={usedPct}
    />
  );
}

function ActivityTile({ state }: { state: StatTileRowProps["imports"] }) {
  if (state.isLoading) return <TileSkeleton label="Activity" />;
  if (state.isError || !state.data) return <TileError label="Activity" />;
  const count = importsThisWeek(state.data.recent_imports);
  return (
    <StatTile
      label="Activity"
      value={`${count} import${count === 1 ? "" : "s"}`}
      supporting="this week"
    />
  );
}

function HealthTile({ state }: { state: StatTileRowProps["validation"] }) {
  if (state.isLoading) return <TileSkeleton label="Health" />;
  if (state.isError || !state.data) return <TileError label="Health" />;
  const status = state.data.status;
  const issueCount = state.data.checks.filter(
    (c) => c.status === "FAIL" || c.status === "WARN",
  ).length;
  let icon;
  let value;
  if (status === "OK") {
    icon = <CheckCircle2 size={18} className="text-success" aria-hidden="true" />;
    value = "All connected";
  } else if (status === "WARN") {
    icon = <AlertTriangle size={18} className="text-caution" aria-hidden="true" />;
    value = `${issueCount} issue${issueCount === 1 ? "" : "s"}`;
  } else if (status === "FAIL") {
    icon = <AlertOctagon size={18} className="text-critical" aria-hidden="true" />;
    value = `${issueCount} issue${issueCount === 1 ? "" : "s"}`;
  } else {
    icon = <HelpCircle size={18} className="text-text-subtle" aria-hidden="true" />;
    value = "Unknown";
  }
  return (
    <StatTile
      label="Health"
      value={
        <span className="inline-flex items-center gap-2">
          {icon}
          {value}
        </span>
      }
    />
  );
}

function TileSkeleton({ label }: { label: string }) {
  return (
    <article className="flex flex-col gap-3 rounded-lg bg-surface p-5 shadow-elev-1">
      <p className="text-meta uppercase tracking-wide text-text-subtle">
        {label}
      </p>
      <LoadingState label={`${label} loading`} rows={1} />
    </article>
  );
}

function TileError({ label }: { label: string }) {
  return (
    <article className="flex flex-col gap-3 rounded-lg bg-surface p-5 shadow-elev-1">
      <p className="text-meta uppercase tracking-wide text-text-subtle">
        {label}
      </p>
      <ErrorState
        title="Couldn't load"
        description="The data source is unreachable right now."
      />
    </article>
  );
}
