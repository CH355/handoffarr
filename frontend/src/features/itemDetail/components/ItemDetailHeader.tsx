import { Film, Tv, Music, FileQuestion } from "lucide-react";
import { StatusBadge } from "@/features/library/components/StatusBadge";
import { formatBytes } from "@/lib/formatBytes";
import {
  classifyMediaType,
  classifyStatus,
  type LibraryMediaType,
} from "@/features/library/types";
import type { LibraryArtifact } from "@/api/libraryApi";

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

interface ItemDetailHeaderProps {
  artifact: LibraryArtifact | null;
  fallbackTitle: string;
}

export function ItemDetailHeader({ artifact, fallbackTitle }: ItemDetailHeaderProps) {
  const mediaType = classifyMediaType(artifact?.media_type);
  const Icon = MEDIA_ICON[mediaType];
  const status = artifact ? classifyStatus(artifact) : "queued";
  const sizeBytes =
    typeof artifact?.file_size === "number" && artifact.file_size > 0
      ? artifact.file_size
      : null;
  const title = artifact?.media_title ?? fallbackTitle;

  return (
    <header className="flex items-start gap-4">
      <div
        aria-hidden={true}
        className="flex h-20 w-20 shrink-0 items-center justify-center rounded-md bg-surface-raised text-text-muted"
      >
        <Icon size={28} />
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <h2 className="truncate text-title text-text">{title}</h2>
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-meta text-text-muted">
          <span>{MEDIA_LABEL[mediaType]}</span>
          <span aria-hidden={true}>·</span>
          <span>{sizeBytes ? formatBytes(sizeBytes, 1) : "—"}</span>
          <span aria-hidden={true}>·</span>
          <StatusBadge status={status} />
        </p>
      </div>
    </header>
  );
}
