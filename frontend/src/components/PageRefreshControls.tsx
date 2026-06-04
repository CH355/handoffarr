import { RefreshCw } from "lucide-react";
import { formatRelativeTime } from "@/lib/formatRelativeTime";

export function PageRefreshControls({
  dataUpdatedAt,
  isFetching,
  onRefresh,
}: {
  dataUpdatedAt: number;
  isFetching: boolean;
  onRefresh: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3 text-meta text-text-muted">
      <span>Last updated {dataUpdatedAt ? formatRelativeTime(dataUpdatedAt) : "not yet"}</span>
      <button
        type="button"
        onClick={onRefresh}
        disabled={isFetching}
        className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-accent hover:bg-accent-quiet focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:cursor-wait disabled:opacity-60"
      >
        <RefreshCw size={13} aria-hidden="true" className={isFetching ? "animate-spin" : ""} />
        {isFetching ? "Refreshing" : "Refresh"}
      </button>
    </div>
  );
}
