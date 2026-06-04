import { useMemo } from "react";
import { PrimaryBanner } from "./components/PrimaryBanner";
import { StatTileRow } from "./components/StatTileRow";
import { RecentlyAddedSection } from "./components/RecentlyAddedSection";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { formatBytes } from "@/lib/formatBytes";
import { formatRelativeTime } from "@/lib/formatRelativeTime";
import { useHomeData } from "./hooks/useHomeData";
import { PageRefreshControls } from "@/components/PageRefreshControls";
import type { CleanupResponse, CleanupCandidate } from "@/api/cleanupApi";
import type { ValidationResponse } from "@/api/validationApi";

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
): BannerData {
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
  const { cleanup, validation, storage, imports } = useHomeData();
  const queries = [cleanup, validation, storage, imports];

  const banner = useMemo(
    () => deriveBanner(cleanup.data, validation.data),
    [cleanup.data, validation.data],
  );

  const bannerLoading = cleanup.isLoading || validation.isLoading;
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
      <PageRefreshControls
        dataUpdatedAt={Math.max(...queries.map((query) => query.dataUpdatedAt))}
        isFetching={queries.some((query) => query.isFetching)}
        onRefresh={() => { queries.forEach((query) => void query.refetch()); }}
      />

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
        <PrimaryBanner {...banner} />
      )}

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
      />

      <RecentlyAddedSection
        state={{
          data: imports.data,
          isLoading: imports.isLoading,
          isError: imports.isError,
        }}
      />
    </section>
  );
}
