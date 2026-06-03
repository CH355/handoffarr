import { formatBytes } from "@/lib/formatBytes";
import type { CleanupReviewItem } from "@/api/cleanupApi";

interface EvidencePanelProps {
  item: CleanupReviewItem;
}

/* Inner body for EvidenceDrawer (Sprint 3 stub).
   Renders only fields confirmed present in the cleanup-review backend response. */
export function EvidencePanel({ item }: EvidencePanelProps) {
  const reasons = item.risk_reasons?.length ? item.risk_reasons : item.safe_reasons ?? [];
  const paths = item.paths ?? {};
  return (
    <div className="flex flex-col gap-4 text-body">
      <section>
        <p className="text-subtitle text-text">{item.media_title ?? "Untitled"}</p>
        <p className="text-meta text-text-muted">
          {item.review_class ?? "—"} · {item.match_strength ?? "—"} · confidence{" "}
          {typeof item.confidence_score === "number"
            ? `${Math.round(item.confidence_score * 100)}%`
            : "—"}
        </p>
      </section>

      <dl className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2">
        <Field label="Recoverable" value={formatBytes(item.recoverable_bytes ?? 0)} />
        <Field label="Retained" value={formatBytes(item.retained_bytes ?? 0)} />
        <Field label="Library status" value={item.library_status ?? "—"} />
        <Field label="Import status" value={item.import_status ?? "—"} />
        <Field label="Torrent state" value={item.torrent_state ?? "—"} />
        <Field label="Source" value={item.source_application ?? "—"} />
      </dl>

      {reasons.length ? (
        <section>
          <p className="text-meta uppercase tracking-wide text-text-subtle">
            {item.risk_reasons?.length ? "Why risky" : "Why safe"}
          </p>
          <ul className="mt-1 list-disc pl-5 text-body text-text-muted">
            {reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section>
        <p className="text-meta uppercase tracking-wide text-text-subtle">Paths</p>
        <dl className="mt-1 flex flex-col gap-1 text-meta">
          <PathField label="Library" value={paths.library_path} />
          <PathField label="Retained" value={paths.download_path ?? paths.content_path} />
          <PathField label="Imported from" value={paths.import_source_path} />
        </dl>
      </section>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <dt className="text-meta text-text-subtle">{label}</dt>
      <dd className="text-body text-text [font-variant-numeric:tabular-nums]">{value}</dd>
    </div>
  );
}

function PathField({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-text-subtle">{label}</dt>
      <dd className="break-all font-mono text-text">{value ?? "—"}</dd>
    </div>
  );
}
