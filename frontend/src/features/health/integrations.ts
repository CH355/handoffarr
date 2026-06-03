import type { IntegrationProbe } from "@/api/healthApi";
import type { StorageResponse } from "@/api/storageApi";
import type { ImportsResponse } from "@/api/importsApi";
import type { IntegrationStatus, HealthStatus } from "./types";

/* Backend gap (Sprint 5): there is no /api/debug endpoint for Sonarr or
   Lidarr today, and probes do not expose a persisted "last successful
   contact" timestamp. We render only integrations present in the live
   backend response, per the sprint brief. */

export interface IntegrationSources {
  qbit?: IntegrationProbe | undefined;
  radarr?: IntegrationProbe | undefined;
  seerr?: IntegrationProbe | undefined;
  storage?: StorageResponse | undefined;
  imports?: ImportsResponse | undefined;
}

function probeStatus(probe: IntegrationProbe | undefined): HealthStatus {
  if (!probe) return "unknown";
  if (probe.enabled === false) return "unknown";
  if (probe.ok === true) {
    if (probe.warnings && probe.warnings.length > 0) return "warning";
    return "healthy";
  }
  if (probe.ok === false) return "critical";
  return "unknown";
}

function probeSummary(probe: IntegrationProbe | undefined, healthy: string): string {
  if (!probe) return "No data yet";
  if (probe.enabled === false) return "Not configured";
  if (probe.ok === true) {
    if (probe.warnings && probe.warnings.length > 0) {
      return `${probe.warnings.length} warning${probe.warnings.length === 1 ? "" : "s"}`;
    }
    return healthy;
  }
  if (probe.ok === false) return probe.error || "Unreachable";
  return "Status unknown";
}

function fromProbe(
  id: string,
  name: string,
  probe: IntegrationProbe | undefined,
  healthyCopy: string,
): IntegrationStatus {
  return {
    id,
    name,
    status: probeStatus(probe),
    summary: probeSummary(probe, healthyCopy),
    detail: probe?.error || undefined,
    url: probe?.url,
    warnings: probe?.warnings ?? [],
    available: probe !== undefined,
  };
}

function storageIntegration(storage: StorageResponse | undefined): IntegrationStatus {
  const summary = storage?.summary;
  const status: HealthStatus = summary?.health ?? "unknown";
  let copy = "No storage data";
  if (summary) {
    if (status === "healthy") copy = "Capacity within thresholds";
    else if (status === "warning") copy = "Capacity nearing threshold";
    else if (status === "critical") copy = "Capacity exhausted";
    else copy = "Capacity unknown";
  }
  return {
    id: "storage",
    name: "Storage",
    status,
    summary: copy,
    warnings: [],
    available: storage !== undefined,
  };
}

function importsIntegration(imports: ImportsResponse | undefined): IntegrationStatus {
  if (!imports) {
    return {
      id: "imports",
      name: "Import History",
      status: "unknown",
      summary: "No import data",
      warnings: [],
      available: false,
    };
  }
  const counts = imports.summary || imports.counts;
  const failed = counts?.failed ?? 0;
  const pending = counts?.pending ?? 0;
  const total = counts?.total ?? 0;
  let status: HealthStatus = "healthy";
  let summary = total === 0 ? "No imports recorded" : "All imports succeeded";
  if (failed > 0) {
    status = "warning";
    summary = `${failed} failed import${failed === 1 ? "" : "s"}`;
  } else if (pending > 0) {
    status = "warning";
    summary = `${pending} pending import${pending === 1 ? "" : "s"}`;
  }
  return {
    id: "imports",
    name: "Import History",
    status,
    summary,
    warnings: [],
    available: true,
  };
}

export function buildIntegrations(sources: IntegrationSources): IntegrationStatus[] {
  const list: IntegrationStatus[] = [];
  if (sources.qbit) list.push(fromProbe("qbittorrent", "qBittorrent", sources.qbit, "Connected"));
  if (sources.radarr) list.push(fromProbe("radarr", "Radarr", sources.radarr, "Connected"));
  if (sources.seerr) list.push(fromProbe("seerr", "Overseerr", sources.seerr, "Connected"));
  if (sources.storage) list.push(storageIntegration(sources.storage));
  if (sources.imports) list.push(importsIntegration(sources.imports));
  return list;
}

export function rollupStatus(list: IntegrationStatus[]): HealthStatus {
  if (list.some((i) => i.status === "critical")) return "critical";
  if (list.some((i) => i.status === "warning")) return "warning";
  if (list.length === 0) return "unknown";
  if (list.every((i) => i.status === "healthy")) return "healthy";
  return "unknown";
}

export function countByStatus(list: IntegrationStatus[]): Record<HealthStatus, number> {
  const counts: Record<HealthStatus, number> = {
    healthy: 0,
    warning: 0,
    critical: 0,
    unknown: 0,
  };
  for (const i of list) counts[i.status] += 1;
  return counts;
}
