import { request } from "./client";

/* Library API per frontend-implementation-spec-v1.md §7.2.
   Backed by app/main.py GET /api/library and GET /api/library/{media_id}. */

export interface LibraryArtifact {
  artifact_id?: string | null;
  media_id?: string | null;
  media_title?: string | null;
  media_type?: string | null;
  library_path?: string | null;
  file_exists?: boolean | null;
  file_size?: number | null;
  source_application?: string | null;
  observed_at?: string | null;
  library_status?: string | null;
  download_copy_present?: boolean | null;
  potential_cleanup_candidate?: boolean | null;
  import_status?: string | null;
  paths?: {
    library_path?: string | null;
    download_path?: string | null;
  };
  evidence?: Record<string, unknown>;
}

export interface LibrarySummary {
  present: number;
  missing: number;
  unknown: number;
  potential_cleanup_candidates: number;
  total: number;
}

export interface LibraryResponse {
  summary: LibrarySummary;
  present: LibraryArtifact[];
  missing: LibraryArtifact[];
  unknown: LibraryArtifact[];
  potential_cleanup_candidates: LibraryArtifact[];
  artifacts: LibraryArtifact[];
}

export function getLibrary(): Promise<LibraryResponse> {
  return request<LibraryResponse>("/api/library");
}

export interface LibraryMediaResponse {
  media_id: string;
  library_artifact: LibraryArtifact | null;
  library_status: string;
  paths: Record<string, string | null | undefined>;
  evidence: Record<string, unknown>;
}

export function getLibraryMedia(mediaId: string): Promise<LibraryMediaResponse> {
  return request<LibraryMediaResponse>(
    `/api/library/${encodeURIComponent(mediaId)}`,
  );
}
