import type { LibraryArtifact } from "@/api/libraryApi";

/* Five approved status badges (Sprint 4 brief):
   Imported, Downloading, Stuck, Not found, Queued. */
export type LibraryItemStatus =
  | "imported"
  | "downloading"
  | "stuck"
  | "not_found"
  | "queued";

export type LibraryMediaType = "movie" | "show" | "music" | "other";

export interface LibraryItem {
  mediaId: string;
  title: string;
  mediaType: LibraryMediaType;
  rawMediaType: string | null;
  status: LibraryItemStatus;
  sizeBytes: number | null;
  observedAt: string | null;
  sourceApplication: string | null;
  libraryPath: string | null;
  artifact: LibraryArtifact;
}

export function classifyMediaType(raw: string | null | undefined): LibraryMediaType {
  const m = (raw ?? "").toLowerCase();
  if (!m) return "other";
  if (m.includes("movie") || m === "film") return "movie";
  if (m.includes("show") || m.includes("series") || m.includes("episode") || m.includes("tv"))
    return "show";
  if (m.includes("music") || m.includes("track") || m.includes("album") || m.includes("song"))
    return "music";
  return "other";
}

export function classifyStatus(artifact: LibraryArtifact): LibraryItemStatus {
  const lib = (artifact.library_status ?? "").toLowerCase();
  const imp = (artifact.import_status ?? "").toLowerCase();
  if (lib.includes("present")) return "imported";
  if (imp === "success" || imp === "imported") return "imported";
  if (imp === "downloading" || imp === "in_progress") return "downloading";
  if (imp === "stuck" || imp === "stalled") return "stuck";
  if (imp === "pending" || imp === "queued") return "queued";
  if (lib.includes("missing")) return "not_found";
  return "queued";
}

export function toLibraryItem(artifact: LibraryArtifact): LibraryItem {
  const mediaId = String(artifact.media_id ?? artifact.artifact_id ?? "");
  return {
    mediaId,
    title: artifact.media_title ?? mediaId ?? "Untitled",
    mediaType: classifyMediaType(artifact.media_type),
    rawMediaType: artifact.media_type ?? null,
    status: classifyStatus(artifact),
    sizeBytes:
      typeof artifact.file_size === "number" && artifact.file_size > 0
        ? artifact.file_size
        : null,
    observedAt: artifact.observed_at ?? null,
    sourceApplication: artifact.source_application ?? null,
    libraryPath: artifact.library_path ?? null,
    artifact,
  };
}
