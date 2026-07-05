import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, X } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { getTorrent, removeDeadTorrents } from "@/api/torrentsApi";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { formatBytes } from "@/lib/formatBytes";

export function TorrentDetailPage() {
  const { torrentHash = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["torrent", torrentHash],
    queryFn: () => getTorrent(torrentHash),
    enabled: Boolean(torrentHash),
  });
  const remove = useMutation({
    mutationFn: () => removeDeadTorrents([torrentHash]),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["torrents"] });
      navigate("/torrents?status=dead");
    },
  });

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/30">
      <aside
        aria-label="Torrent detail"
        className="h-full w-full max-w-xl overflow-y-auto bg-surface p-6 shadow-elev-3"
      >
        <button
          type="button"
          onClick={() => navigate("/torrents")}
          aria-label="Close torrent detail"
          className="mb-5 rounded-md p-2 text-text-muted hover:bg-bg"
        >
          <X size={20} />
        </button>
        {query.isLoading ? (
          <LoadingState label="Loading torrent detail" rows={5} />
        ) : query.isError || !query.data ? (
          <ErrorState
            title="Couldn't load torrent"
            description="The torrent is no longer in the current snapshot."
          />
        ) : (
          <div className="flex flex-col gap-6">
            <header>
              <h2 className="text-title text-text">{query.data.name}</h2>
              {query.data.dead_torrent ? (
                <p className="mt-2 inline-flex items-center gap-2 text-body font-semibold text-caution">
                  <AlertTriangle size={18} /> Dead torrent
                </p>
              ) : null}
            </header>
            <dl className="grid grid-cols-2 gap-4">
              <Metric
                label="Availability"
                value={`${query.data.availability_percent.toFixed(0)}%`}
              />
              <Metric label="Seeders" value={String(query.data.seeders)} />
              <Metric label="Peers" value={String(query.data.peers)} />
              <Metric label="Health" value={query.data.health} />
              <Metric
                label="Size"
                value={formatBytes(
                  query.data.total_size ?? query.data.size ?? null,
                )}
              />
            </dl>
            {query.data.recommendation ? (
              <section className="rounded-lg bg-caution-quiet p-4">
                <h3 className="text-meta font-semibold uppercase tracking-wide text-caution">
                  Recommendation
                </h3>
                <p className="mt-2 text-body text-text">
                  {query.data.recommendation}
                </p>
              </section>
            ) : null}
            {query.data.dead_torrent ? (
              <button
                type="button"
                disabled={remove.isPending}
                onClick={() => remove.mutate()}
                className="h-10 rounded-md bg-caution px-4 text-body font-semibold text-text disabled:opacity-60"
              >
                {remove.isPending ? "Removing…" : "Remove torrent (keep files)"}
              </button>
            ) : null}
            {remove.isError ? (
              <p role="alert" className="text-body text-critical">
                The torrent could not be removed.
              </p>
            ) : null}
          </div>
        )}
      </aside>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-meta uppercase tracking-wide text-text-subtle">{label}</dt>
      <dd className="mt-1 text-body font-medium tabular-nums text-text">{value}</dd>
    </div>
  );
}
