import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";
import type { TorrentsResponse } from "@/api/torrentsApi";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";

export function DeadTorrentsCard({
  data,
  isLoading,
  isError,
}: {
  data: TorrentsResponse | undefined;
  isLoading: boolean;
  isError: boolean;
}) {
  const health = data?.health;
  return (
    <section className="flex flex-col gap-4 rounded-lg bg-surface p-5 shadow-elev-1">
      <header className="flex items-center justify-between gap-3">
        <h3 className="text-subtitle text-text">Dead Torrents</h3>
        {health ? (
          <span
            className={`inline-flex items-center gap-1 text-meta font-semibold uppercase ${
              health.severity === "critical"
                ? "text-critical"
                : health.severity === "warning"
                  ? "text-caution"
                  : "text-success"
            }`}
          >
            {health.count ? (
              <AlertTriangle size={14} aria-hidden="true" />
            ) : (
              <CheckCircle2 size={14} aria-hidden="true" />
            )}
            {health.severity}
          </span>
        ) : null}
      </header>
      {isLoading ? (
        <LoadingState label="Loading dead torrents" rows={2} />
      ) : isError || !health ? (
        <ErrorState
          title="Couldn't load dead torrents"
          description="The current torrent snapshot is unavailable."
        />
      ) : (
        <>
          <p className="text-title tabular-nums text-text">{health.message}</p>
          <p className="text-body text-text-muted">{health.description}</p>
          {health.count > 0 ? (
            <Link
              to="/torrents?status=dead"
              className="text-body font-semibold text-accent hover:text-accent-hover"
            >
              Review Dead Torrents
            </Link>
          ) : null}
        </>
      )}
    </section>
  );
}
