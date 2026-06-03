import { useMemo } from "react";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { formatBytes } from "@/lib/formatBytes";
import { RecommendationCard } from "./components/RecommendationCard";
import { useCleanupReviewQuery } from "./hooks/useCleanupReview";

/* RecoverSpacePage — Mockups §2 three-section recommendation pattern.
   The stat tiles in the cards are non-clickable; navigation happens through
   the explicit Review actions. */
export function RecoverSpacePage() {
  const review = useCleanupReviewQuery();

  const summary = review.data?.summary;
  const totals = useMemo(() => {
    if (!summary) {
      return {
        safeCount: 0,
        safeRecoverable: 0,
        riskyCount: 0,
        unknownCount: 0,
        totalRecoverable: 0,
      };
    }
    return {
      safeCount: summary.safe_candidate_count,
      safeRecoverable: summary.safe_recoverable_bytes,
      riskyCount: summary.risky_candidate_count,
      unknownCount: summary.unknown_evidence_count + summary.missing_library_count,
      totalRecoverable: summary.recoverable_bytes,
    };
  }, [summary]);

  return (
    <section
      aria-labelledby="recover-title"
      className="mx-auto flex w-full max-w-page flex-col gap-6"
    >
      <header className="flex flex-col gap-2">
        <h1 id="recover-title" className="text-title text-text">
          Recover space
        </h1>
        <p className="text-body text-text-muted">
          Review what Handoffarr has classified before any deletion. Handoffarr never
          removes a file on its own — every action requires explicit confirmation.
        </p>
      </header>

      {review.isLoading ? (
        <LoadingState label="Loading recommendations" rows={3} />
      ) : review.isError ? (
        <ErrorState
          title="Couldn't load cleanup recommendations"
          description="Handoffarr's backend is unreachable. Reload once it's back."
        />
      ) : summary && summary.total === 0 ? (
        <EmptyState
          title="Nothing to recover right now"
          description="Handoffarr hasn't found any cleanup candidates. Check back after the next scan."
        />
      ) : (
        <>
          <p className="text-meta text-text-muted">
            Total recoverable across all classes:{" "}
            <span className="text-text [font-variant-numeric:tabular-nums]">
              {formatBytes(totals.totalRecoverable)}
            </span>
          </p>

          <div className="flex flex-col gap-4">
            <RecommendationCard
              variant="safe"
              title="Safe to recover"
              description="Items with strong evidence that the library copy is intact and the retained download is redundant."
              primaryStat={formatBytes(totals.safeRecoverable)}
              primaryStatLabel="Recoverable"
              secondaryStat={String(totals.safeCount)}
              secondaryStatLabel="Items"
              actionLabel="Review safe candidates"
              actionTo="/recover/safe"
              actionDisabled={totals.safeCount === 0}
              meta="Confirmation phrase required before any action."
            />

            <RecommendationCard
              variant="judgment"
              title="Needs your judgment"
              description="Items where evidence is partial, contradictory, or weak. Read-only — no execution from this surface."
              primaryStat={String(totals.riskyCount)}
              primaryStatLabel="Items"
              actionLabel="Review one at a time"
              actionTo="/recover/judgment"
              actionDisabled={totals.riskyCount === 0}
              meta="Risky items cannot be batch-deleted."
            />

            <RecommendationCard
              variant="notRecommended"
              title="Not recommended"
              description="Items with missing library evidence or unknown classification. Handoffarr will not act on these."
              primaryStat={String(totals.unknownCount)}
              primaryStatLabel="Items"
              meta="No action available."
            />
          </div>

          <nav
            aria-label="Recover space history"
            className="flex flex-wrap items-center gap-3 border-t border-border pt-4 text-meta"
          >
            <a
              href="/recover/history"
              className="rounded-md px-2 py-1 text-accent hover:bg-accent-quiet focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
            >
              View cleanup history →
            </a>
            <a
              href="/api/cleanup/action-plan.txt"
              target="_blank"
              rel="noreferrer"
              className="rounded-md px-2 py-1 text-text-muted hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
            >
              Download action plan (.txt)
            </a>
          </nav>
        </>
      )}
    </section>
  );
}
