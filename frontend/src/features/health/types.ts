/* Health hierarchy per Sprint 5 brief and Mockups §7. */
export type HealthStatus = "healthy" | "warning" | "critical" | "unknown";

export interface IntegrationStatus {
  id: string;
  name: string;
  status: HealthStatus;
  summary: string;
  detail?: string | undefined;
  url?: string | undefined;
  warnings: string[];
  available: boolean;
}
