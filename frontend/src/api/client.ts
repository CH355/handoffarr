import { ApiError } from "./errors";
import { auditMark, byteLength } from "@/perf/audit";

type RequestPriority = 1 | 2 | 3;

function classifyRequest(path: string): RequestPriority {
  if (/^\/api\/(health|imports|torrents)(\/|$|\?)/.test(path)) return 1;
  if (/^\/api\/debug\/(qbit|radarr|seerr)(\/|$|\?)/.test(path)) return 1;
  if (/^\/api\/(storage|cleanup|recovery-agent\/queue)(\/|$|\?)/.test(path)) return 2;
  return 3;
}

async function yieldForPriority(priority: RequestPriority, signal?: AbortSignal) {
  if (priority === 1 || typeof window === "undefined") return;
  if (signal?.aborted) throw new DOMException("Request aborted", "AbortError");
  await new Promise<void>((resolve) => {
    if (priority === 2) {
      window.requestAnimationFrame(() => resolve());
      return;
    }
    const idle = window.requestIdleCallback;
    if (idle) idle(() => resolve(), { timeout: 250 });
    else window.setTimeout(resolve, 50);
  });
}

/* Single fetch wrapper per frontend-implementation-spec-v1.md §7.1.
   No feature calls fetch() directly. */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  const priority = classifyRequest(path);
  const startedAt = performance.now();
  auditMark("query_start", path, { method: init?.method ?? "GET", priority });
  try {
    await yieldForPriority(priority, init?.signal ?? undefined);
    let attempts = 0;
    do {
      response = await fetch(path, {
        ...init,
        headers: {
          Accept: "application/json",
          "X-Handoffarr-Priority": String(priority),
          ...(init?.headers ?? {}),
        },
      });
      if (response.status !== 503 || attempts >= 120) break;
      attempts += 1;
      await new Promise((resolve) => window.setTimeout(resolve, 500));
    } while (true);
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
      const body = (await response.json()) as {
        detail?: string;
        error?: string;
      };
      detail = body?.detail ?? body?.error;
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
