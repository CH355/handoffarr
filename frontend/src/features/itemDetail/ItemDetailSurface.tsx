import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, X } from "lucide-react";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EvidenceDrawer } from "@/components/EvidenceDrawer";
import { ActivityTimeline, type ActivityTimelineEntry } from "@/components/ActivityTimeline";
import { ItemDetailHeader } from "./components/ItemDetailHeader";
import { useItemDetailData } from "./hooks/useItemDetailData";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { cn } from "@/lib/cn";
import type { TimelineStage } from "@/api/timelineApi";

const STAGE_TONE: Record<string, ActivityTimelineEntry["tone"]> = {
  FAILED: "critical",
  PENDING: "caution",
  COMPLETE: "success",
};

function stageLabel(stage: TimelineStage): string {
  const name = stage.stage ?? "Activity";
  const status = stage.stage_status ? ` (${stage.stage_status.toLowerCase()})` : "";
  return `${name}${status}`;
}

function deriveEntries(
  stages: TimelineStage[],
  importsHistory: Array<{ import_status?: string | null; import_timestamp?: string | null }>,
): ActivityTimelineEntry[] {
  const fromStages = stages
    .filter((s) => s.timestamp)
    .map<ActivityTimelineEntry>((s, idx) => ({
      id: `stage-${idx}-${s.stage ?? "stage"}`,
      label: stageLabel(s),
      timestamp: s.timestamp ?? null,
      tone: STAGE_TONE[(s.stage_status ?? "").toUpperCase()] ?? "default",
    }));
  const fromImports = importsHistory
    .filter((event) => event.import_timestamp)
    .map<ActivityTimelineEntry>((event, idx) => ({
      id: `import-${idx}`,
      label: `Import ${event.import_status ?? "event"}`,
      timestamp: event.import_timestamp ?? null,
      tone:
        (event.import_status ?? "").toLowerCase() === "success"
          ? "success"
          : (event.import_status ?? "").toLowerCase() === "failed"
            ? "critical"
            : "default",
    }));
  const merged = [...fromStages, ...fromImports];
  merged.sort((a, b) => (b.timestamp ?? "").localeCompare(a.timestamp ?? ""));
  return merged.slice(0, 6);
}

export function ItemDetailSurface() {
  const { mediaId = "" } = useParams<{ mediaId: string }>();
  const navigate = useNavigate();
  const isTabletPlus = useMediaQuery("(min-width: 768px)");
  const { library, timeline, imports } = useItemDetailData(mediaId);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const evidenceTriggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const closeTriggerOrigin = useRef<HTMLElement | null>(null);

  const close = () => navigate("/library");

  /* Focus management: drawer mode moves focus into the panel on open and back
     to the previously focused element on close, matching EvidenceDrawer. */
  useEffect(() => {
    if (!isTabletPlus) return;
    closeTriggerOrigin.current = (document.activeElement as HTMLElement | null) ?? null;
    panelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !evidenceOpen) {
        e.stopPropagation();
        close();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      closeTriggerOrigin.current?.focus?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isTabletPlus]);

  const artifact = library.data?.library_artifact ?? null;
  const stages = timeline.data?.stages ?? [];
  const history = imports.data?.history ?? [];
  const entries = useMemo(() => deriveEntries(stages, history), [stages, history]);

  const isLoading = library.isLoading || timeline.isLoading || imports.isLoading;
  const isError = library.isError && timeline.isError && imports.isError;
  const fallbackTitle = library.data?.media_id ?? mediaId;

  const body = (
    <div className="flex flex-col gap-5">
      {isLoading ? (
        <LoadingState label="Loading item" rows={3} />
      ) : isError ? (
        <ErrorState
          title="Couldn't load this item"
          description="The library and timeline feeds are unreachable right now."
        />
      ) : (
        <>
          <ItemDetailHeader artifact={artifact} fallbackTitle={fallbackTitle} />

          <section aria-labelledby="recent-activity-heading" className="flex flex-col gap-3">
            <div className="flex items-baseline justify-between gap-2">
              <h3 id="recent-activity-heading" className="text-subtitle text-text">
                Recent activity
              </h3>
              <button
                ref={evidenceTriggerRef}
                type="button"
                onClick={() => setEvidenceOpen(true)}
                className="rounded-sm text-meta text-text-muted hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
              >
                Why?
              </button>
            </div>
            <ActivityTimeline entries={entries} variant="compact" />
          </section>

          {artifact?.source_application ? (
            <p className="text-meta text-text-muted">
              Source: {artifact.source_application}
            </p>
          ) : null}
        </>
      )}
    </div>
  );

  if (isTabletPlus) {
    return (
      <div className="fixed inset-0 z-40 flex" role="presentation">
        <div
          aria-hidden={true}
          className="absolute inset-0 bg-bg/60 backdrop-blur-sm"
          onClick={close}
        />
        <div
          ref={panelRef}
          tabIndex={-1}
          role="dialog"
          aria-modal="true"
          aria-label="Item detail"
          className={cn(
            "relative ml-auto flex h-full w-full max-w-[560px] flex-col gap-4",
            "bg-surface-raised p-6 shadow-elev-3 outline-none",
            "md:rounded-l-lg",
          )}
        >
          <header className="flex items-start justify-between gap-3">
            <h2 className="sr-only">Item detail</h2>
            <button
              type="button"
              onClick={close}
              aria-label="Close item detail"
              className="ml-auto rounded-md p-1 text-text-muted hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
            >
              <X size={18} aria-hidden={true} />
            </button>
          </header>
          <div className="flex-1 overflow-y-auto pr-1">{body}</div>
        </div>
        <EvidenceDrawer
          open={evidenceOpen}
          onClose={() => setEvidenceOpen(false)}
          label="Why?"
          triggerRef={evidenceTriggerRef as React.RefObject<HTMLElement>}
        >
          <EvidenceBody artifact={artifact} />
        </EvidenceDrawer>
      </div>
    );
  }

  /* Mobile: full-screen route surface. */
  return (
    <section
      aria-labelledby="item-detail-title"
      className="fixed inset-0 z-30 flex flex-col gap-4 overflow-y-auto bg-bg p-4"
    >
      <h1 id="item-detail-title" className="sr-only">
        Item detail
      </h1>
      <button
        type="button"
        onClick={close}
        className="inline-flex w-fit items-center gap-1 rounded-md text-meta text-text-muted hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
      >
        <ArrowLeft size={16} aria-hidden={true} />
        Library
      </button>
      {body}
      <EvidenceDrawer
        open={evidenceOpen}
        onClose={() => setEvidenceOpen(false)}
        label="Why?"
        triggerRef={evidenceTriggerRef as React.RefObject<HTMLElement>}
      >
        <EvidenceBody artifact={artifact} />
      </EvidenceDrawer>
    </section>
  );
}

function EvidenceBody({ artifact }: { artifact: { evidence?: Record<string, unknown> } | null }) {
  const evidence = artifact?.evidence ?? {};
  const entries = Object.entries(evidence);
  if (entries.length === 0) {
    return <p className="text-meta text-text-muted">No evidence available for this item.</p>;
  }
  return (
    <dl className="flex flex-col gap-3">
      {entries.map(([key, value]) => (
        <div key={key} className="flex flex-col gap-1">
          <dt className="text-meta text-text-muted">{key}</dt>
          <dd className="break-words text-body text-text">
            {typeof value === "string" ? value : <pre className="whitespace-pre-wrap font-mono text-meta">{JSON.stringify(value, null, 2)}</pre>}
          </dd>
        </div>
      ))}
    </dl>
  );
}
