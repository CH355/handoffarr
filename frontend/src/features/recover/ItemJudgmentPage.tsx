import { useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { EvidenceDrawer } from "@/components/EvidenceDrawer";
import { CandidateRow } from "./components/CandidateRow";
import { EvidencePanel } from "./components/EvidencePanel";
import { useCleanupReviewQuery } from "./hooks/useCleanupReview";
import type { CleanupReviewItem } from "@/api/cleanupApi";

const RISKY_REVIEW_CLASS = "Risky Review Candidate";

/* ItemJudgmentPage — Mockups §4. Read-only review of risky candidates.
   No execution actions; Handoffarr will not act on risky items from this surface. */
export function ItemJudgmentPage() {
  const review = useCleanupReviewQuery({
    review_class: RISKY_REVIEW_CLASS,
    sort: "recoverable_bytes desc",
    limit: 200,
  });
  const [drawerItem, setDrawerItem] = useState<CleanupReviewItem | null>(null);
  const [drawerTrigger, setDrawerTrigger] = useState<HTMLElement | null>(null);

  const candidates = review.data?.candidates ?? [];

  return (
    <section
      aria-labelledby="judgment-title"
      className="mx-auto flex w-full max-w-page flex-col gap-5"
    >
      <header className="flex flex-col gap-2">
        <Link
          to="/recover"
          className="w-fit rounded-md text-meta text-text-muted hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          ← Back to Recover space
        </Link>
        <h1 id="judgment-title" className="text-title text-text">
          Items that need your judgment
        </h1>
        <p className="text-body text-text-muted">
          Evidence is partial, weak, or contradictory for these items. Handoffarr will
          not act on them. Review carefully outside Handoffarr before taking any action.
        </p>
      </header>

      <aside
        role="note"
        className="flex items-start gap-3 rounded-lg bg-caution-quiet p-4"
      >
        <AlertTriangle
          size={20}
          aria-hidden="true"
          className="mt-0.5 text-caution"
        />
        <div className="flex flex-col gap-1">
          <p className="text-subtitle text-text">Read-only review</p>
          <p className="text-body text-text-muted">
            There are no Remove or Keep actions on this surface in Sprint 3. Use the
            evidence here to decide whether to investigate further in your *arr or
            qBittorrent.
          </p>
        </div>
      </aside>

      {review.isLoading ? (
        <LoadingState label="Loading risky candidates" rows={4} />
      ) : review.isError ? (
        <ErrorState
          title="Couldn't load risky candidates"
          description="Try reloading. If the issue persists, check Health."
        />
      ) : candidates.length === 0 ? (
        <EmptyState
          title="Nothing to review"
          description="Handoffarr hasn't flagged any risky candidates right now."
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {candidates.map((item, index) => (
            <CandidateRow
              key={`${item.media_id}-${index}`}
              item={item}
              variant="risky"
              onOpenEvidence={(it, trigger) => {
                setDrawerTrigger(trigger);
                setDrawerItem(it);
              }}
            />
          ))}
        </ul>
      )}

      <EvidenceDrawer
        open={Boolean(drawerItem)}
        onClose={() => setDrawerItem(null)}
        label="Why risky?"
        triggerRef={{ current: drawerTrigger }}
      >
        {drawerItem ? <EvidencePanel item={drawerItem} /> : null}
      </EvidenceDrawer>
    </section>
  );
}
