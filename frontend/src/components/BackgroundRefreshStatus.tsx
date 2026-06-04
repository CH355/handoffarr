import { RefreshCw } from "lucide-react";

export function BackgroundRefreshStatus({ isFetching }: { isFetching: boolean }) {
  if (!isFetching) return null;

  return (
    <span
      role="status"
      aria-live="polite"
      className="inline-flex items-center gap-1.5 text-meta text-text-muted"
    >
      <RefreshCw size={13} aria-hidden="true" className="animate-spin" />
      Refreshing
    </span>
  );
}
