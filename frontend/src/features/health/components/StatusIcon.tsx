import { AlertOctagon, AlertTriangle, CheckCircle2, HelpCircle } from "lucide-react";
import type { HealthStatus } from "../types";
import { cn } from "@/lib/cn";

interface StatusIconProps {
  status: HealthStatus;
  size?: number;
  className?: string;
}

const META: Record<HealthStatus, { label: string; tone: string }> = {
  healthy: { label: "Healthy", tone: "text-success" },
  warning: { label: "Warning", tone: "text-caution" },
  critical: { label: "Critical", tone: "text-critical" },
  unknown: { label: "Unknown", tone: "text-text-muted" },
};

export function StatusIcon({ status, size = 18, className }: StatusIconProps) {
  const meta = META[status];
  const Icon =
    status === "healthy"
      ? CheckCircle2
      : status === "warning"
        ? AlertTriangle
        : status === "critical"
          ? AlertOctagon
          : HelpCircle;
  return (
    <Icon
      size={size}
      className={cn("shrink-0", meta.tone, className)}
      role="img"
      aria-label={meta.label}
    />
  );
}

export function statusLabel(status: HealthStatus): string {
  return META[status].label;
}
