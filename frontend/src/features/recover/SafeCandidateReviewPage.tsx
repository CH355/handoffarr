import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { EvidenceDrawer } from "@/components/EvidenceDrawer";
import { StickyActionBar } from "@/components/StickyActionBar";
import { formatBytes } from "@/lib/formatBytes";
import { CandidateRow } from "./components/CandidateRow";
import { EvidencePanel } from "./components/EvidencePanel";
import { useCleanupReviewQuery } from "./hooks/useCleanupReview";
import type {
  CleanupReviewFilters,
  CleanupReviewItem,
  MatchStrength,
} from "@/api/cleanupApi";

const SAFE_REVIEW_CLASS = "Safe Review Candidate";
const SAFE_MATCH_STRENGTHS: MatchStrength[] = [
  "Exact Library Path Match",
  "Filename + Size Match",
  "Exact Hash/DownloadId Match",
];

type SortKey = NonNullable<CleanupReviewFilters["sort"]>;

const SORT_OPTIONS: Array<{ value: SortKey; label: string }> = [
  { value: "recoverable_bytes desc", label: "Recoverable size (high → low)" },
  { value: "confidence_score desc", label: "Confidence (high → low)" },
  { value: "media_title asc", label: "Title (A → Z)" },
];

/* SafeCandidateReviewPage — Mockups §3, Blueprint §4 v1.1 C2.
   Read-only listing with filter / sort / evidence drawer. Selection
   produces a batch that ships to /recover/preview for dry-run. */
export function SafeCandidateReviewPage() {
  const navigate = useNavigate();
  const [matchStrength, setMatchStrength] = useState<MatchStrength | "">("");
  const [sort, setSort] = useState<SortKey>("recoverable_bytes desc");
  const [selected, setSelected] = useState<Record<string, CleanupReviewItem>>({});
  const [drawerItem, setDrawerItem] = useState<CleanupReviewItem | null>(null);
  const [drawerTrigger, setDrawerTrigger] = useState<HTMLElement | null>(null);

  const filters: CleanupReviewFilters = {
    review_class: SAFE_REVIEW_CLASS,
    match_strength: matchStrength || null,
    sort,
    limit: 200,
  };

  const review = useCleanupReviewQuery(filters);
  const candidates = review.data?.candidates ?? [];

  const selectionList = useMemo(() => Object.values(selected), [selected]);
  const selectionTotal = useMemo(
    () => selectionList.reduce((sum, c) => sum + (c.recoverable_bytes ?? 0), 0),
    [selectionList],
  );

  const keyFor = (item: CleanupReviewItem) =>
    `${item.media_id ?? ""}::${(item.qbit_hash ?? item.torrent_hash ?? "").toLowerCase()}`;

  function onToggle(item: CleanupReviewItem, next: boolean) {
    const key = keyFor(item);
    setSelected((prev) => {
      const draft = { ...prev };
      if (next) draft[key] = item;
      else delete draft[key];
      return draft;
    });
  }

  function onOpenEvidence(item: CleanupReviewItem, trigger: HTMLElement) {
    setDrawerTrigger(trigger);
    setDrawerItem(item);
  }

  function onProceedToPreview() {
    const payload = selectionList
      .map((c) => ({
        media_id: String(c.media_id ?? ""),
        qbit_hash: String(c.qbit_hash ?? c.torrent_hash ?? "").toLowerCase(),
      }))
      .filter((p) => p.media_id && p.qbit_hash);
    if (!payload.length) return;
    sessionStorage.setItem("recover.batchSelection", JSON.stringify(payload));
    navigate("/recover/preview");
  }

  return (
    <section
      aria-labelledby="safe-title"
      className="mx-auto flex w-full max-w-page flex-col gap-5"
    >
      <header className="flex flex-col gap-2">
        <Link
          to="/recover"
          className="w-fit rounded-md text-meta text-text-muted hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          ← Back to Recover space
        </Link>
        <h1 id="safe-title" className="text-title text-text">
          Safe candidate review
        </h1>
        <p className="text-body text-text-muted">
          Each candidate has strong evidence that the library copy is intact. Select
          the ones you want to preview. Nothing is deleted until you confirm.
        </p>
      </header>

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-meta text-text-muted">
          Match strength
          <select
            value={matchStrength}
            onChange={(e) => setMatchStrength(e.target.value as MatchStrength | "")}
            className="rounded-md border border-border bg-surface px-3 py-2 text-body text-text focus-visible:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
          >
            <option value="">All safe matches</option>
            {SAFE_MATCH_STRENGTHS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-meta text-text-muted">
          Sort
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            className="rounded-md border border-border bg-surface px-3 py-2 text-body text-text focus-visible:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
          >
            {SORT_OPTIONS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {review.isLoading ? (
        <LoadingState label="Loading safe candidates" rows={4} />
      ) : review.isError ? (
        <ErrorState
          title="Couldn't load safe candidates"
          description="Try reloading. If the issue persists, check Health."
        />
      ) : candidates.length === 0 ? (
        <EmptyState
          title="No safe candidates"
          description="Handoffarr hasn't found anything safe to recover under these filters."
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {candidates.map((item) => (
            <CandidateRow
              key={keyFor(item)}
              item={item}
              variant="safe"
              selected={Boolean(selected[keyFor(item)])}
              onToggle={onToggle}
              onOpenEvidence={onOpenEvidence}
            />
          ))}
        </ul>
      )}

      <StickyActionBar
        meta={
          <span>
            <span className="[font-variant-numeric:tabular-nums]">
              {selectionList.length}
            </span>{" "}
            selected ·{" "}
            <span className="text-text [font-variant-numeric:tabular-nums]">
              {formatBytes(selectionTotal)}
            </span>{" "}
            recoverable
          </span>
        }
        primary={
          <button
            type="button"
            onClick={onProceedToPreview}
            disabled={selectionList.length === 0}
            className="rounded-md bg-accent px-4 py-2 text-body font-medium text-accent-on hover:bg-accent-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50"
          >
            Preview selected
          </button>
        }
      />

      <EvidenceDrawer
        open={Boolean(drawerItem)}
        onClose={() => setDrawerItem(null)}
        label="Why safe?"
        triggerRef={{ current: drawerTrigger }}
      >
        {drawerItem ? <EvidencePanel item={drawerItem} /> : null}
      </EvidenceDrawer>
    </section>
  );
}
