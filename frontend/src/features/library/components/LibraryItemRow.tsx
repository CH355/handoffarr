import { useNavigate } from "react-router-dom";
import { Film, Tv, Music, FileQuestion } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import { formatBytes } from "@/lib/formatBytes";
import { formatRelativeTime } from "@/lib/formatRelativeTime";
import type { LibraryItem, LibraryMediaType } from "../types";

const MEDIA_ICON: Record<LibraryMediaType, typeof Film> = {
  movie: Film,
  show: Tv,
  music: Music,
  other: FileQuestion,
};

const MEDIA_LABEL: Record<LibraryMediaType, string> = {
  movie: "Movie",
  show: "Show",
  music: "Music",
  other: "Item",
};

interface LibraryItemRowProps {
  item: LibraryItem;
}

export function LibraryItemRow({ item }: LibraryItemRowProps) {
  const navigate = useNavigate();
  const Icon = MEDIA_ICON[item.mediaType];
  const sizeLabel = item.sizeBytes ? formatBytes(item.sizeBytes, 1) : "—";
  const timeLabel = item.observedAt ? formatRelativeTime(item.observedAt) : null;
  const target = `/library/${encodeURIComponent(item.mediaId)}`;

  const open = () => navigate(target);

  return (
    <button
      type="button"
      onClick={open}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          open();
        }
      }}
      aria-label={`Open details for ${item.title}`}
      className="flex w-full items-center gap-4 rounded-lg bg-surface px-4 py-3 text-left shadow-elev-1 transition-colors duration-fast hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
    >
      <span
        aria-hidden={true}
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-surface-raised text-text-muted"
      >
        <Icon size={18} />
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="truncate text-subtitle text-text">{item.title}</span>
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-meta text-text-muted">
          <span>{MEDIA_LABEL[item.mediaType]}</span>
          <span aria-hidden={true}>·</span>
          <span>{sizeLabel}</span>
          <span aria-hidden={true}>·</span>
          <StatusBadge status={item.status} />
          {timeLabel ? (
            <>
              <span aria-hidden={true}>·</span>
              <span>{timeLabel}</span>
            </>
          ) : null}
        </span>
      </span>
    </button>
  );
}
