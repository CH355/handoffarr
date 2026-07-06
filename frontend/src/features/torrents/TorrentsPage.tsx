import { useEffect, useMemo, useReducer, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Eye,
  LoaderCircle,
  SearchCheck,
} from "lucide-react";
import { Link, Outlet, useSearchParams } from "react-router-dom";
import {
  listTorrents,
  evaluateTorrentAlternatives,
  removeSelectedTorrents,
  type RecoveryStatus,
  type Torrent,
  type TorrentSummary,
} from "@/api/torrentsApi";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContainer } from "@/components/PageContainer";
import { useRefreshQueryOptions } from "@/hooks/useRefreshQueryOptions";
import { formatRelativeTime } from "@/lib/formatRelativeTime";
import {
  initialSelectionState,
  selectionReducer,
} from "./reducers/selectionReducer";

type StatusFilter = "all" | RecoveryStatus;
type SortKey =
  | "media"
  | "type"
  | "release"
  | "progress"
  | "availability"
  | "seeds"
  | "health-score"
  | "status"
  | "recommendation";

const FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "dead", label: "Dead" },
  { value: "downloading", label: "Downloading" },
  { value: "stalled", label: "Stalled" },
  { value: "queued", label: "Queued" },
  { value: "healthy", label: "Healthy" },
];

export function TorrentsPage() {
  const refreshOptions = useRefreshQueryOptions("medium");
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["torrents"],
    queryFn: listTorrents,
    ...refreshOptions,
  });
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortKey>("status");
  const [selection, dispatch] = useReducer(
    selectionReducer,
    initialSelectionState,
  );
  const requestedFilter = params.get("status");
  const filter: StatusFilter = FILTERS.some(
    (option) => option.value === requestedFilter,
  )
    ? (requestedFilter as StatusFilter)
    : "all";
  const torrents = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return (query.data?.torrents ?? [])
      .filter((torrent) => {
        if (filter !== "all" && torrent.recovery_status !== filter) return false;
        return (
          !needle ||
          `${torrent.media_title} ${torrent.current_release} ${torrent.media_type}`
            .toLowerCase()
            .includes(needle)
        );
      })
      .sort((left, right) => compareTorrents(left, right, sort));
  }, [filter, query.data, search, sort]);
  const allHashes = useMemo(
    () => (query.data?.torrents ?? []).map((torrent) => torrent.hash),
    [query.data],
  );
  const visibleHashes = useMemo(
    () => torrents.map((torrent) => torrent.hash),
    [torrents],
  );
  const allVisibleSelected =
    visibleHashes.length > 0 &&
    visibleHashes.every((hash) => selection.selected.has(hash));
  const remove = useMutation({
    mutationFn: ({
      hashes,
      deleteFiles,
    }: {
      hashes: string[];
      deleteFiles: boolean;
    }) => removeSelectedTorrents(hashes, deleteFiles),
    onSuccess: async () => {
      dispatch({ type: "clear" });
      await queryClient.invalidateQueries({ queryKey: ["torrents"] });
    },
  });
  const evaluate = useMutation({
    mutationFn: (hash: string) => evaluateTorrentAlternatives(hash),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["torrents"] });
    },
  });

  useEffect(() => {
    dispatch({ type: "prune", hashes: allHashes });
  }, [allHashes]);

  const removeSelection = (deleteFiles: boolean) => {
    remove.mutate({
      hashes: [...selection.selected],
      deleteFiles,
    });
  };

  return (
    <>
      <PageContainer
        title="Recovery Center"
        description="Review download health and act on torrents that need intervention."
      >
        <div className="flex flex-col gap-4">
          {query.data ? <RecoverySummary summary={query.data.summary} /> : null}
          <div className="flex flex-col gap-3 rounded-lg bg-surface p-4 shadow-elev-1">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search media or current release"
              aria-label="Search recovery items"
              className="h-10 flex-1 rounded-md border border-border bg-surface px-3 text-body text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            />
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-2" aria-label="Status filter">
                {FILTERS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() =>
                      setParams(
                        option.value === "all"
                          ? {}
                          : { status: option.value },
                      )
                    }
                    className={`rounded-pill px-3 py-1.5 text-body font-medium ${
                      filter === option.value
                        ? "bg-accent text-accent-on"
                        : "bg-bg text-text-muted hover:text-text"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              <label className="flex items-center gap-2 text-body text-text-muted">
                Sort
                <select
                  value={sort}
                  onChange={(event) => setSort(event.target.value as SortKey)}
                  className="h-10 rounded-md border border-border bg-surface px-3 text-text"
                >
                  <option value="status">Status</option>
                  <option value="recommendation">Recommendation</option>
                  <option value="media">Media</option>
                  <option value="type">Type</option>
                  <option value="release">Current release</option>
                  <option value="progress">Progress</option>
                  <option value="availability">Availability</option>
                  <option value="seeds">Seeds</option>
                  <option value="health-score">Health score</option>
                </select>
              </label>
            </div>
          </div>
          <TorrentBody
            isLoading={query.isLoading}
            isError={query.isError}
            torrents={torrents}
            filtered={filter !== "all" || search.length > 0}
            selected={selection.selected}
            allVisibleSelected={allVisibleSelected}
            onToggle={(hash) => dispatch({ type: "toggle", hash })}
            onToggleAll={() =>
              dispatch({
                type: allVisibleSelected ? "clear-visible" : "select-visible",
                hashes: visibleHashes,
              })
            }
            evaluatingHash={evaluate.isPending ? evaluate.variables : null}
            onEvaluate={(hash) => evaluate.mutate(hash)}
          />
          {evaluate.isError ? (
            <p role="alert" className="text-body text-critical">
              Alternatives could not be evaluated. Confirm this torrent can be
              matched to a configured Radarr movie or Sonarr episode.
            </p>
          ) : null}
          {selection.selected.size > 0 ? (
            <section className="sticky bottom-16 z-20 flex flex-col gap-3 rounded-lg border border-border-strong bg-surface-raised p-4 shadow-elev-2 md:bottom-0 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-body font-semibold text-text">Bulk actions</p>
                <p className="text-meta text-text-muted">
                  {selection.selected.size} selected. Actions only affect
                  qBittorrent.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={remove.isPending}
                  onClick={() => removeSelection(false)}
                  className="rounded-md border border-border-strong px-4 py-2 text-body font-semibold text-text hover:bg-bg disabled:opacity-60"
                >
                  Remove Selected (keep files)
                </button>
                <button
                  type="button"
                  disabled={remove.isPending}
                  onClick={() => removeSelection(true)}
                  className="inline-flex items-center gap-2 rounded-md bg-critical px-4 py-2 text-body font-semibold text-accent-on disabled:opacity-60"
                >
                  {remove.isPending ? (
                    <LoaderCircle
                      size={16}
                      className="animate-spin"
                      aria-hidden="true"
                    />
                  ) : null}
                  Remove Selected
                </button>
              </div>
            </section>
          ) : null}
          {remove.isError ? (
            <p role="alert" className="text-body text-critical">
              The selected torrents could not be removed from qBittorrent.
            </p>
          ) : null}
        </div>
      </PageContainer>
      <Outlet />
    </>
  );
}

function RecoverySummary({ summary }: { summary: TorrentSummary }) {
  return (
    <section className="rounded-lg bg-accent-quiet p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-meta font-semibold uppercase tracking-wide text-accent">
            Recovery Center
          </p>
          <p className="mt-1 text-title text-text">
            {summary.total_torrents} torrents
          </p>
        </div>
        <dl className="grid grid-cols-3 gap-x-6 gap-y-3 sm:grid-cols-4">
          <SummaryMetric label="Dead" value={summary.dead_torrents} />
          <SummaryMetric label="Stalled" value={summary.stalled_torrents} />
          <SummaryMetric label="Healthy" value={summary.healthy_torrents} />
          <SummaryMetric
            label="Potentially recoverable"
            value={summary.potentially_recoverable}
          />
        </dl>
      </div>
    </section>
  );
}

function SummaryMetric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <dt className="text-meta text-text-muted">{label}</dt>
      <dd className="text-subtitle tabular-nums text-text">{value}</dd>
    </div>
  );
}

function TorrentBody({
  isLoading,
  isError,
  torrents,
  filtered,
  selected,
  allVisibleSelected,
  onToggle,
  onToggleAll,
  evaluatingHash,
  onEvaluate,
}: {
  isLoading: boolean;
  isError: boolean;
  torrents: Torrent[];
  filtered: boolean;
  selected: ReadonlySet<string>;
  allVisibleSelected: boolean;
  onToggle: (hash: string) => void;
  onToggleAll: () => void;
  evaluatingHash: string | null;
  onEvaluate: (hash: string) => void;
}) {
  if (isLoading)
    return <LoadingState label="Loading recovery items" rows={6} />;
  if (isError) {
    return (
      <ErrorState
        title="Couldn't load recovery items"
        description="The torrent snapshot is unavailable."
      />
    );
  }
  if (!torrents.length) {
    return (
      <EmptyState
        title={filtered ? "No matching recovery items" : "No torrents"}
        description={
          filtered
            ? "No torrents match the current filters."
            : "qBittorrent has not reported any torrents."
        }
      />
    );
  }
  return (
    <div className="overflow-x-auto rounded-lg bg-surface shadow-elev-1">
      <table className="w-full min-w-[1500px] text-left text-body">
        <thead className="border-b border-border text-meta uppercase tracking-wide text-text-subtle">
          <tr>
            <th className="p-4 font-medium">
              <input
                type="checkbox"
                checked={allVisibleSelected}
                onChange={onToggleAll}
                aria-label="Select all visible torrents"
                className="h-4 w-4 accent-accent"
              />
            </th>
            <th className="p-4 font-medium">Media</th>
            <th className="p-4 font-medium">Type</th>
            <th className="p-4 font-medium">Current Release</th>
            <th className="p-4 font-medium">Progress</th>
            <th className="p-4 font-medium">Availability</th>
            <th className="p-4 font-medium">Seeds</th>
            <th className="p-4 font-medium">Status</th>
            <th className="p-4 font-medium">Recovery Status</th>
            <th className="p-4 font-medium">Confidence</th>
            <th className="p-4 font-medium">Best replacement</th>
            <th className="p-4 font-medium">Health Score</th>
            <th className="p-4 font-medium">Recommendation</th>
            <th className="p-4 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {torrents.map((torrent) => (
            <tr
              key={torrent.hash}
              className={selected.has(torrent.hash) ? "bg-accent-quiet/60" : ""}
            >
              <td className="p-4">
                <input
                  type="checkbox"
                  checked={selected.has(torrent.hash)}
                  onChange={() => onToggle(torrent.hash)}
                  aria-label={`Select ${torrent.media_title}`}
                  className="h-4 w-4 accent-accent"
                />
              </td>
              <td className="max-w-52 p-4 font-medium text-text">
                <span className="line-clamp-2">{torrent.media_title}</span>
              </td>
              <td className="p-4 text-text-muted">{torrent.media_type}</td>
              <td className="max-w-72 p-4 text-text-muted">
                <span className="line-clamp-2">{torrent.current_release}</span>
              </td>
              <td className="p-4 tabular-nums text-text-muted">
                {Math.round((torrent.progress ?? 0) * 100)}%
              </td>
              <td className="p-4 tabular-nums text-text-muted">
                {torrent.availability_percent == null
                  ? "—"
                  : `${torrent.availability_percent.toFixed(0)}%`}
              </td>
              <td className="p-4 tabular-nums text-text-muted">
                {torrent.seeders}
              </td>
              <td className="p-4">
                <StatusBadge status={torrent.recovery_status} />
              </td>
              <td className="p-4 text-text-muted">
                {torrent.agent_evaluated_at
                  ? `Evaluated ${formatRelativeTime(torrent.agent_evaluated_at)}`
                  : "Pending evaluation"}
              </td>
              <td className="p-4 font-semibold tabular-nums text-text">
                {torrent.agent_confidence == null
                  ? "—"
                  : torrent.agent_confidence.toFixed(0)}
              </td>
              <td className="max-w-64 p-4 text-text">
                <span className="line-clamp-2">
                  {torrent.best_replacement ?? "Not evaluated"}
                </span>
              </td>
              <td className="p-4 font-semibold tabular-nums text-text">
                {torrent.replacement_health_score == null
                  ? "—"
                  : `${torrent.replacement_health_score.toFixed(0)}/100`}
              </td>
              <td className="max-w-56 p-4">
                <p className="font-medium text-text">
                  {torrent.agent_recommendation ??
                    (torrent.replacement_recommendation
                    ? "Replace"
                    : (torrent.recommendation ?? "None"))}
                </p>
                <p className="mt-1 line-clamp-2 text-meta text-text-muted">
                  {torrent.agent_reasoning[0] ??
                    torrent.replacement_recommendation ??
                    torrent.recommendation_reason}
                </p>
              </td>
              <td className="p-4">
                <div className="flex flex-col items-start gap-2">
                  {torrent.recovery_status !== "healthy" ? (
                    <button
                      type="button"
                      disabled={evaluatingHash != null}
                      onClick={() => onEvaluate(torrent.hash)}
                      className="inline-flex items-center gap-1 font-semibold text-accent hover:text-accent-hover disabled:opacity-60"
                    >
                      {evaluatingHash === torrent.hash ? (
                        <LoaderCircle
                          size={15}
                          className="animate-spin"
                          aria-hidden="true"
                        />
                      ) : (
                        <SearchCheck size={15} aria-hidden="true" />
                      )}
                      Evaluate
                    </button>
                  ) : null}
                  <Link
                    to={`/torrents/${torrent.hash}`}
                    className="inline-flex items-center gap-1 font-semibold text-accent hover:text-accent-hover"
                  >
                    <Eye size={15} aria-hidden="true" />
                    View
                  </Link>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusBadge({ status }: { status: RecoveryStatus }) {
  const warning = status === "dead" || status === "stalled";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-pill px-2 py-1 text-meta font-semibold uppercase ${
        status === "dead"
          ? "bg-critical-quiet text-critical"
          : warning
            ? "bg-caution-quiet text-caution"
            : status === "healthy"
              ? "bg-success-quiet text-success"
              : "bg-accent-quiet text-accent"
      }`}
    >
      {warning ? (
        <AlertTriangle size={13} aria-hidden="true" />
      ) : status === "healthy" ? (
        <CheckCircle2 size={13} aria-hidden="true" />
      ) : null}
      {status}
    </span>
  );
}

function compareTorrents(left: Torrent, right: Torrent, sort: SortKey): number {
  const text = (a: string, b: string) => a.localeCompare(b);
  if (sort === "media") return text(left.media_title, right.media_title);
  if (sort === "type") return text(left.media_type, right.media_type);
  if (sort === "release")
    return text(left.current_release, right.current_release);
  if (sort === "progress")
    return (right.progress ?? 0) - (left.progress ?? 0);
  if (sort === "availability")
    return (
      (right.availability_percent ?? -1) - (left.availability_percent ?? -1)
    );
  if (sort === "seeds") return right.seeders - left.seeders;
  if (sort === "health-score")
    return (
      (right.replacement_health_score ?? -1) -
      (left.replacement_health_score ?? -1)
    );
  if (sort === "recommendation")
    return text(left.recommendation ?? "None", right.recommendation ?? "None");
  const order: RecoveryStatus[] = [
    "dead",
    "stalled",
    "queued",
    "downloading",
    "healthy",
  ];
  return (
    order.indexOf(left.recovery_status) - order.indexOf(right.recovery_status)
  );
}
