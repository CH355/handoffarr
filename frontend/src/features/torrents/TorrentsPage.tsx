import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Download } from "lucide-react";
import { Link, Outlet, useSearchParams } from "react-router-dom";
import { listTorrents, type Torrent } from "@/api/torrentsApi";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContainer } from "@/components/PageContainer";
import { useRefreshQueryOptions } from "@/hooks/useRefreshQueryOptions";
import { formatBytes } from "@/lib/formatBytes";

type StatusFilter = "all" | "dead";

export function TorrentsPage() {
  const refreshOptions = useRefreshQueryOptions("medium");
  const query = useQuery({
    queryKey: ["torrents"],
    queryFn: listTorrents,
    ...refreshOptions,
  });
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const filter: StatusFilter = params.get("status") === "dead" ? "dead" : "all";
  const torrents = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return (query.data?.torrents ?? []).filter((torrent) => {
      if (filter === "dead" && !torrent.dead_torrent) return false;
      return !needle || String(torrent.name ?? "").toLowerCase().includes(needle);
    });
  }, [filter, query.data, search]);

  return (
    <>
      <PageContainer
        title="Downloads"
        description="Current torrents reported by qBittorrent."
      >
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search downloads"
              aria-label="Search downloads"
              className="h-10 flex-1 rounded-md border border-border bg-surface px-3 text-body text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            />
            <label className="flex items-center gap-2 text-body text-text-muted">
              Status
              <select
                value={filter}
                onChange={(event) => {
                  const next = event.target.value as StatusFilter;
                  setParams(next === "dead" ? { status: "dead" } : {});
                }}
                className="h-10 rounded-md border border-border bg-surface px-3 text-text"
              >
                <option value="all">All torrents</option>
                <option value="dead">Dead torrents</option>
              </select>
            </label>
          </div>
          <TorrentBody
            isLoading={query.isLoading}
            isError={query.isError}
            torrents={torrents}
            filtered={filter === "dead" || search.length > 0}
          />
        </div>
      </PageContainer>
      <Outlet />
    </>
  );
}

function TorrentBody({
  isLoading,
  isError,
  torrents,
  filtered,
}: {
  isLoading: boolean;
  isError: boolean;
  torrents: Torrent[];
  filtered: boolean;
}) {
  if (isLoading) return <LoadingState label="Loading downloads" rows={6} />;
  if (isError) {
    return (
      <ErrorState
        title="Couldn't load downloads"
        description="The torrent snapshot is unavailable."
      />
    );
  }
  if (!torrents.length) {
    return (
      <EmptyState
        title={filtered ? "No matching downloads" : "No downloads"}
        description={
          filtered
            ? "No torrents match the current status filter."
            : "qBittorrent has not reported any torrents."
        }
      />
    );
  }
  return (
    <div className="overflow-x-auto rounded-lg bg-surface shadow-elev-1">
      <table className="w-full text-left text-body">
        <thead className="border-b border-border text-meta uppercase tracking-wide text-text-subtle">
          <tr>
            <th className="p-4 font-medium">Name</th>
            <th className="p-4 font-medium">Status</th>
            <th className="p-4 font-medium">Progress</th>
            <th className="p-4 font-medium">Size</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {torrents.map((torrent) => (
            <tr key={torrent.hash}>
              <td className="p-4">
                <Link
                  to={`/torrents/${torrent.hash}`}
                  className="font-medium text-text hover:text-accent"
                >
                  {torrent.name || torrent.hash}
                </Link>
              </td>
              <td className="p-4">
                {torrent.dead_torrent ? (
                  <span className="inline-flex items-center gap-1 rounded-pill bg-caution-quiet px-2 py-1 text-meta font-semibold text-caution">
                    <AlertTriangle size={14} aria-hidden="true" />
                    DEAD · NO SEEDERS
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-meta text-text-muted">
                    <Download size={14} aria-hidden="true" />
                    {torrent.state || "Unknown"}
                  </span>
                )}
              </td>
              <td className="p-4 tabular-nums text-text-muted">
                {Math.round((torrent.progress ?? 0) * 100)}%
              </td>
              <td className="p-4 tabular-nums text-text-muted">
                {formatBytes(torrent.total_size ?? torrent.size ?? null)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
