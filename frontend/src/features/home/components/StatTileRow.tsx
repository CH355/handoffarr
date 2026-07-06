import { CheckCircle2, AlertTriangle, AlertOctagon, HelpCircle } from "lucide-react";
import { StatTile } from "./StatTile";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { formatBytes } from "@/lib/formatBytes";
import type { StorageResponse } from "@/api/storageApi";
import type { ImportsResponse, ImportEvent } from "@/api/importsApi";
import type { ValidationResponse } from "@/api/validationApi";
import type { TorrentsResponse } from "@/api/torrentsApi";
import { Link } from "react-router-dom";

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
  torrents: {
    data: TorrentsResponse | undefined;
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

export function StatTileRow({ storage, imports, validation, torrents }: StatTileRowProps) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StorageTile state={storage} />
      <ActivityTile state={imports} />
      <DeadDownloadsTile state={torrents} />
      <HealthTile state={validation} />
    </div>
  );
}

function DeadDownloadsTile({
  state,
}: {
  state: StatTileRowProps["torrents"];
}) {
  if (state.isLoading) return <TileSkeleton label="Recovery Center" />;
  if (state.isError || !state.data) return <TileError label="Recovery Center" />;
  const count = state.data.summary.dead_torrents;
  return (
    <Link
      to="/torrents?status=dead"
      className="rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
    >
      <StatTile
        label="Recovery Center"
        value={String(count)}
        supporting="No seeders available"
      />
    </Link>
  );
}

function StorageTile({ state }: { state: StatTileRowProps["storage"] }) {
  if (state.isLoading) return <TileSkeleton label="Storage" />;
  if (state.isError || !state.data) return <TileError label="Storage" />;
  const s = state.data.summary;
  const free = s.free_bytes;
  const total = s.total_bytes;
  const retained = s.retained_bytes ?? s.completed_torrent_bytes ?? 0;
  const completedCount = s.completed_torrent_count ?? 0;
  const usedPct =
    free != null && total != null && total > 0
      ? ((total - free) / total) * 100
      : null;

  if (retained > 0) {
    return (
      <StatTile
        label="Storage"
        value={`${formatBytes(retained)} retained`}
        supporting={`${completedCount} completed item${completedCount === 1 ? "" : "s"} to review`}
        progressPct={usedPct}
      />
    );
  }

  if (free != null) {
    return (
      <StatTile
        label="Storage"
        value={`${formatBytes(free)} free`}
        supporting={total != null ? `of ${formatBytes(total)}` : "No retained downloads found"}
        progressPct={usedPct}
      />
    );
  }

  return (
    <StatTile
      label="Storage"
      value="No retained space"
      supporting="Storage capacity is not reported yet"
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
