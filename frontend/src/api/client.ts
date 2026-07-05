import { ApiError } from "./errors";
import { auditMark, byteLength } from "@/perf/audit";

/* Single fetch wrapper per frontend-implementation-spec-v1.md §7.1.
   No feature calls fetch() directly. */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  const startedAt = performance.now();
  auditMark("query_start", path, { method: init?.method ?? "GET" });
  try {
    response = await fetch(path, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch (err) {
    auditMark("query_finish", path, {
      ok: false,
      duration_ms: performance.now() - startedAt,
      error: err instanceof Error ? err.message : "Network error",
    });
    const message = err instanceof Error ? err.message : "Network error";
    throw new ApiError(message, 0);
  }

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body?.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(
      detail ?? `Request failed (${response.status})`,
      response.status,
      detail,
    );
  }

  const textStartedAt = performance.now();
  const body = await response.text();
  const parseStartedAt = performance.now();
  const parsed = JSON.parse(body) as T;
  auditMark("query_finish", path, {
    ok: true,
    status: response.status,
    duration_ms: performance.now() - startedAt,
    body_read_ms: parseStartedAt - textStartedAt,
    json_parse_ms: performance.now() - parseStartedAt,
    payload_bytes: byteLength(body),
  });
  return parsed;
}
