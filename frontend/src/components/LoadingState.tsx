interface LoadingStateProps {
  label?: string;
  rows?: number;
}

/* Foundation §10.2 — skeletons over spinners for layout-known content. */
export function LoadingState({ label = "Loading", rows = 3 }: LoadingStateProps) {
  return (
    <div role="status" aria-live="polite" aria-label={label} className="flex flex-col gap-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-16 animate-pulse rounded-lg bg-border"
          style={{ animationDuration: "1.4s" }}
        />
      ))}
    </div>
  );
}
