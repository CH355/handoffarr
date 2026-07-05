import { useMemo } from "react";
import { PrimaryBanner } from "./components/PrimaryBanner";
import { StatTileRow } from "./components/StatTileRow";
import { RecentlyAddedSection } from "./components/RecentlyAddedSection";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { formatBytes } from "@/lib/formatBytes";
import { formatRelativeTime } from "@/lib/formatRelativeTime";
import { useHomeData } from "./hooks/useHomeData";
import type { CleanupResponse, CleanupCandidate } from "@/api/cleanupApi";
import type { ValidationResponse } from "@/api/validationApi";
import type { TorrentsResponse } from "@/api/torrentsApi";
import { AuditProfiler, measureSync, useRouteAudit } from "@/perf/audit";

type BannerVariant = "critical" | "recover" | "stuck" | "idle";

interface BannerData {
  variant: BannerVariant;
  headline: string;
  accentNumeral?: string | undefined;
  subline?: string | undefined;
  actionLabel?: string | undefined;
  actionTo?: string | undefined;
  meta?: string | undefined;
}

function deriveBanner(
  cleanup: CleanupResponse | undefined,
  validation: ValidationResponse | undefined,
  torrents: TorrentsResponse | undefined,
): BannerData {
  if ((torrents?.summary.dead_torrents ?? 0) > 0) {
    const count = torrents?.summary.dead_torrents ?? 0;
    return {
      variant: "stuck",
      headline: "Some downloads cannot complete because no seeders exist.",
      subline: `${count} dead torrent${count === 1 ? "" : "s"} detected`,
      actionLabel: "Review Dead Torrents",
      actionTo: "/torrents?status=dead",
    };
  }

  if (validation?.status === "FAIL") {
    const failing = validation.checks.find((c) => c.status === "FAIL");
    return {
      variant: "critical",
      headline: failing?.name ?? "An integration needs attention",
      subline: failing?.message,
      actionLabel: "Open Health",
      actionTo: "/health",
    };
  }

  const summary = cleanup?.summary;
  const recoverable = summary?.total_recoverable_bytes ?? 0;
  const pendingItems = summary?.pending ?? 0;
  const lastCompleted = lastCleanupTimestamp(cleanup);

  if (recoverable > 0 && pendingItems > 0) {
    return {
      variant: "recover",
      headline: "ready to recover",
      accentNumeral: formatBytes(recoverable, 0),
      subline: `${pendingItems} item${pendingItems === 1 ? "" : "s"} you've already watched · safe to remove`,
      actionLabel: "Review and recover",
      actionTo: "/recover",
      meta: lastCompleted
        ? `Last cleanup: ${formatRelativeTime(lastCompleted)}`
        : undefined,
    };
  }

  return {
    variant: "idle",
    headline: "Everything's running smoothly.",
    subline: lastCompleted
      ? `Last cleanup: ${formatRelativeTime(lastCompleted)}`
      : "No cleanup activity yet.",
  };
}

function lastCleanupTimestamp(cleanup: CleanupResponse | undefined): string | null {
  if (!cleanup?.completed?.length) return null;
  let latest: string | null = null;
  for (const event of cleanup.completed as CleanupCandidate[]) {
    const ts = event.cleanup_timestamp;
    if (!ts) continue;
    if (latest === null || ts > latest) latest = ts;
  }
  return latest;
}

export function HomePage() {
  const { cleanup, validation, storage, imports, torrents } = useHomeData();
  const dataReady =
    !cleanup.isLoading &&
    !validation.isLoading &&
    !storage.isLoading &&
    !imports.isLoading &&
    !torrents.isLoading;
  useRouteAudit("Home", dataReady, {
    cleanup_status: cleanup.status,
    validation_status: validation.status,
    storage_status: storage.status,
    imports_status: imports.status,
  });

  const banner = useMemo(
    () =>
      measureSync("transform", "Home.deriveBanner", () =>
        deriveBanner(cleanup.data, validation.data, torrents.data),
      ),
    [cleanup.data, validation.data, torrents.data],
  );

  const bannerLoading =
    cleanup.isLoading || validation.isLoading || torrents.isLoading;
  const bannerError =
    cleanup.isError && validation.isError && !cleanup.data && !validation.data;

  return (
    <section
      aria-labelledby="home-title"
      className="mx-auto flex w-full max-w-page flex-col gap-8"
    >
      <h1 id="home-title" className="sr-only">
        Home
      </h1>

      {bannerLoading ? (
        <div
          className="rounded-lg bg-surface p-6 shadow-elev-1 md:p-8"
          aria-busy="true"
        >
          <LoadingState label="Loading summary" rows={2} />
        </div>
      ) : bannerError ? (
        <ErrorState
          title="Couldn't load your summary"
          description="The backend is unreachable. Reload once it's back."
        />
      ) : (
        <AuditProfiler id="Home.PrimaryBanner">
          <PrimaryBanner {...banner} />
        </AuditProfiler>
      )}

      <AuditProfiler id="Home.StatTileRow">
        <StatTileRow
          storage={{
            data: storage.data,
            isLoading: storage.isLoading,
            isError: storage.isError,
          }}
          imports={{
            data: imports.data,
            isLoading: imports.isLoading,
            isError: imports.isError,
          }}
          validation={{
            data: validation.data,
            isLoading: validation.isLoading,
            isError: validation.isError,
          }}
          torrents={{
            data: torrents.data,
            isLoading: torrents.isLoading,
            isError: torrents.isError,
          }}
        />
      </AuditProfiler>

      <AuditProfiler id="Home.RecentlyAddedSection">
        <RecentlyAddedSection
          state={{
            data: imports.data,
            isLoading: imports.isLoading,
            isError: imports.isError,
          }}
        />
      </AuditProfiler>
    </section>
  );
}
