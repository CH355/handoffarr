import {
  Profiler,
  useEffect,
  useLayoutEffect,
  useRef,
  type ProfilerOnRenderCallback,
  type ReactNode,
} from "react";

type AuditEvent = {
  kind: string;
  name: string;
  at: number;
  details?: Record<string, unknown> | undefined;
};

declare global {
  interface Window {
    __HDO_PERF_AUDIT__?: AuditEvent[];
  }
}

const QUERY_PARAM = "perfAudit";
const STORAGE_KEY = "handoffarr.perfAudit";

export function auditEnabled(): boolean {
  if (typeof window === "undefined") return false;
  const params = new URLSearchParams(window.location.search);
  if (params.get(QUERY_PARAM) === "1") {
    window.localStorage.setItem(STORAGE_KEY, "1");
    return true;
  }
  if (params.get(QUERY_PARAM) === "0") {
    window.localStorage.removeItem(STORAGE_KEY);
    return false;
  }
  return window.localStorage.getItem(STORAGE_KEY) === "1";
}

export function auditMark(
  kind: string,
  name: string,
  details?: Record<string, unknown>,
): void {
  if (!auditEnabled()) return;
  const event = { kind, name, at: performance.now(), details };
  window.__HDO_PERF_AUDIT__ = window.__HDO_PERF_AUDIT__ ?? [];
  window.__HDO_PERF_AUDIT__.push(event);
  console.info("[handoffarr:perf]", event);
}

export function byteLength(value: string): number {
  return new Blob([value]).size;
}

export function measureSync<T>(
  kind: string,
  name: string,
  fn: () => T,
  details?: Record<string, unknown>,
): T {
  if (!auditEnabled()) return fn();
  const start = performance.now();
  try {
    return fn();
  } finally {
    auditMark(kind, name, {
      ...details,
      duration_ms: performance.now() - start,
    });
  }
}

export function useRenderAudit(name: string, details?: Record<string, unknown>): void {
  const count = useRef(0);
  count.current += 1;
  auditMark("render", name, { render_count: count.current, ...details });
  useEffect(() => {
    auditMark("render_commit", name, { render_count: count.current, ...details });
  });
}

export function useRouteAudit(
  name: string,
  dataReady: boolean,
  details?: Record<string, unknown>,
): void {
  const enteredAt = useRef(performance.now());
  const firstRender = useRef(false);
  const readyLogged = useRef(false);
  useRenderAudit(`route:${name}`, details);

  useLayoutEffect(() => {
    auditMark("route_entered", name, details);
    return () => {
      auditMark("route_unmounted", name, {
        ...details,
        mounted_ms: performance.now() - enteredAt.current,
      });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useLayoutEffect(() => {
    if (firstRender.current) return;
    firstRender.current = true;
    auditMark("route_first_render", name, {
      ...details,
      since_enter_ms: performance.now() - enteredAt.current,
    });
  });

  useEffect(() => {
    if (!dataReady || readyLogged.current) return;
    readyLogged.current = true;
    requestAnimationFrame(() => {
      auditMark("route_data_ready", name, {
        ...details,
        since_enter_ms: performance.now() - enteredAt.current,
      });
      requestAnimationFrame(() => {
        auditMark("route_fully_rendered", name, {
          ...details,
          since_enter_ms: performance.now() - enteredAt.current,
        });
      });
    });
  }, [dataReady, details, name]);
}

const onRender: ProfilerOnRenderCallback = (
  id,
  phase,
  actualDuration,
  baseDuration,
  startTime,
  commitTime,
) => {
  auditMark("component_render_cost", id, {
    phase,
    actual_duration_ms: actualDuration,
    base_duration_ms: baseDuration,
    start_time_ms: startTime,
    commit_time_ms: commitTime,
  });
};

export function AuditProfiler({
  id,
  children,
}: {
  id: string;
  children: ReactNode;
}) {
  if (!auditEnabled()) return <>{children}</>;
  return (
    <Profiler id={id} onRender={onRender}>
      {children}
    </Profiler>
  );
}
