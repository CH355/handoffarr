import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, LoaderCircle, X } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import {
  evaluateTorrentAlternatives,
  getTorrent,
  removeSelectedTorrents,
  type ReplacementCandidate,
} from "@/api/torrentsApi";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { formatBytes } from "@/lib/formatBytes";

export function TorrentDetailPage() {
  const { torrentHash = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [candidateSort, setCandidateSort] =
    useState<CandidateSort>("health-score");
  const query = useQuery({
    queryKey: ["torrent", torrentHash],
    queryFn: () => getTorrent(torrentHash),
    enabled: Boolean(torrentHash),
  });
  const remove = useMutation({
    mutationFn: () => removeSelectedTorrents([torrentHash], false),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["torrents"] });
      navigate("/torrents?status=dead");
    },
  });
  const evaluate = useMutation({
    mutationFn: (force: boolean) =>
      evaluateTorrentAlternatives(torrentHash, force),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["torrent", torrentHash] }),
        queryClient.invalidateQueries({ queryKey: ["torrents"] }),
      ]);
    },
  });
  const candidates = useMemo(
    () =>
      [...(query.data?.replacement_candidates ?? [])].sort((left, right) =>
        compareCandidates(left, right, candidateSort),
      ),
    [candidateSort, query.data?.replacement_candidates],
  );

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
                value={
                  query.data.availability_percent == null
                    ? "Unavailable"
                    : `${query.data.availability_percent.toFixed(0)}%`
                }
              />
              <Metric label="Seeders" value={String(query.data.seeders)} />
              <Metric label="Peers" value={String(query.data.peers)} />
              <Metric label="Status" value={query.data.recovery_status} />
              <Metric
                label="Size"
                value={formatBytes(
                  query.data.total_size ?? query.data.size ?? null,
                )}
              />
            </dl>
            {query.data.dead_reason ? (
              <section className="rounded-lg bg-caution-quiet p-4">
                <h3 className="text-meta font-semibold uppercase tracking-wide text-caution">
                  Reason
                </h3>
                <p className="mt-2 text-body text-text">
                  {query.data.dead_reason}
                </p>
              </section>
            ) : null}
            <section className="rounded-lg bg-accent-quiet p-4">
              <h3 className="text-meta font-semibold uppercase tracking-wide text-accent">
                Current Recommendation
              </h3>
              <p className="mt-2 text-subtitle text-text">
                {query.data.best_replacement ??
                  query.data.recommendation ??
                  "Healthy"}
              </p>
              {query.data.replacement_recommendation_reasons.length ? (
                <div className="mt-2 text-body text-text-muted">
                  <p>Recommended because</p>
                  <ul className="mt-1 list-disc space-y-1 pl-5">
                    {query.data.replacement_recommendation_reasons.map(
                      (reason) => (
                        <li key={reason}>{reason}</li>
                      ),
                    )}
                  </ul>
                </div>
              ) : (
                <p className="mt-1 text-body text-text-muted">
                  {query.data.replacement_recommendation ??
                    query.data.recommendation_reason}
                </p>
              )}
            </section>
            <section className="rounded-lg border border-border p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-subtitle text-text">
                  Alternative Releases
                </h3>
                <div className="flex flex-wrap items-center gap-2">
                  <label className="flex items-center gap-2 text-meta text-text-muted">
                    Sort
                    <select
                      value={candidateSort}
                      onChange={(event) =>
                        setCandidateSort(event.target.value as CandidateSort)
                      }
                      className="h-9 rounded-md border border-border bg-surface px-2 text-body text-text"
                    >
                      <option value="health-score">Health Score</option>
                      <option value="seeders">Seeders</option>
                      <option value="quality">Quality</option>
                      <option value="age">Age</option>
                    </select>
                  </label>
                  {query.data.recovery_status !== "healthy" ? (
                    <button
                      type="button"
                      disabled={evaluate.isPending}
                      onClick={() =>
                        evaluate.mutate(
                          Boolean(query.data.alternatives_evaluated_at),
                        )
                      }
                      className="inline-flex h-9 items-center gap-2 rounded-md bg-accent px-3 text-body font-semibold text-accent-on disabled:opacity-60"
                    >
                      {evaluate.isPending ? (
                        <LoaderCircle
                          size={15}
                          className="animate-spin"
                          aria-hidden="true"
                        />
                      ) : null}
                      {query.data.alternatives_evaluated_at
                        ? "Refresh Alternatives"
                        : "Evaluate"}
                    </button>
                  ) : null}
                </div>
              </div>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[900px] text-left text-body">
                  <thead className="border-b border-border text-meta uppercase tracking-wide text-text-subtle">
                    <tr>
                      <th className="p-3 font-medium">Release</th>
                      <th className="p-3 font-medium">Quality</th>
                      <th className="p-3 font-medium">Indexer</th>
                      <th className="p-3 font-medium">Seeds</th>
                      <th className="p-3 font-medium">Peers</th>
                      <th className="p-3 font-medium">Age</th>
                      <th className="p-3 font-medium">Size</th>
                      <th className="p-3 font-medium">Score</th>
                      <th className="p-3 font-medium">Recommended</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {candidates.length ? (
                      candidates.map((candidate, index) => (
                        <tr
                          key={`${candidate.release_name}:${index}`}
                          className={
                            candidate.recommended ? "bg-success-quiet/60" : ""
                          }
                        >
                          <td className="max-w-80 p-3">
                            <p className="font-medium text-text">
                              {candidate.release_name}
                            </p>
                            {candidate.rejected ? (
                              <p className="mt-1 text-meta text-critical">
                                {candidate.rejection_reason ?? "Rejected by Arr"}
                              </p>
                            ) : null}
                          </td>
                          <td className="p-3 text-text-muted">
                            {candidate.quality ?? "—"}
                          </td>
                          <td className="p-3 text-text-muted">
                            {candidate.indexer ?? "—"}
                          </td>
                          <td className="p-3 tabular-nums text-text-muted">
                            {candidate.seeders}
                          </td>
                          <td className="p-3 tabular-nums text-text-muted">
                            {candidate.peers}
                          </td>
                          <td className="p-3 tabular-nums text-text-muted">
                            {formatAge(candidate.age_days)}
                          </td>
                          <td className="p-3 tabular-nums text-text-muted">
                            {formatBytes(candidate.size)}
                          </td>
                          <td className="p-3 font-semibold tabular-nums text-text">
                            {candidate.score.toFixed(0)}
                          </td>
                          <td className="p-3">
                            {candidate.recommended ? (
                              <span className="inline-flex items-center gap-1 text-meta font-semibold text-success">
                                <CheckCircle2 size={14} aria-hidden="true" />
                                Recommended
                              </span>
                            ) : (
                              "—"
                            )}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td
                          colSpan={9}
                          className="p-6 text-center text-text-muted"
                        >
                          Evaluate this torrent to retrieve read-only results
                          from Radarr or Sonarr.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              {evaluate.isError ? (
                <p role="alert" className="mt-3 text-body text-critical">
                  Alternatives could not be evaluated. Confirm this torrent can
                  be matched to a configured Arr item.
                </p>
              ) : null}
            </section>
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

type CandidateSort = "health-score" | "seeders" | "quality" | "age";

function compareCandidates(
  left: ReplacementCandidate,
  right: ReplacementCandidate,
  sort: CandidateSort,
): number {
  if (sort === "seeders") return right.seeders - left.seeders;
  if (sort === "quality")
    return (left.quality ?? "").localeCompare(right.quality ?? "");
  if (sort === "age")
    return (
      (left.age_days ?? Number.POSITIVE_INFINITY) -
      (right.age_days ?? Number.POSITIVE_INFINITY)
    );
  return right.score - left.score;
}

function formatAge(ageDays: number | null): string {
  if (ageDays == null) return "—";
  if (ageDays < 1) return "<1d";
  return `${Math.round(ageDays)}d`;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-meta uppercase tracking-wide text-text-subtle">{label}</dt>
      <dd className="mt-1 text-body font-medium tabular-nums text-text">{value}</dd>
    </div>
  );
}
