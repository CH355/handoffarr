import { CheckCircle2, Download, PauseCircle, HelpCircle, Clock, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import type { LibraryItemStatus } from "../types";

interface StatusBadgeProps {
  status: LibraryItemStatus;
  className?: string;
}

interface BadgeSpec {
  label: string;
  icon: LucideIcon;
  tone: string;
}

const SPEC: Record<LibraryItemStatus, BadgeSpec> = {
  imported: { label: "Imported", icon: CheckCircle2, tone: "text-success" },
  downloading: { label: "Downloading", icon: Download, tone: "text-accent" },
  stuck: { label: "Stuck", icon: PauseCircle, tone: "text-caution" },
  not_found: { label: "Not found", icon: HelpCircle, tone: "text-critical" },
  queued: { label: "Queued", icon: Clock, tone: "text-text-muted" },
};

/* Icon + label per Sprint 4 brief: "No color-only states." */
export function StatusBadge({ status, className }: StatusBadgeProps) {
  const spec = SPEC[status];
  const Icon = spec.icon;
  return (
    <span
      role="status"
      aria-label={`Status: ${spec.label}`}
      className={cn(
        "inline-flex items-center gap-1 text-meta",
        spec.tone,
        className,
      )}
    >
      <Icon size={14} aria-hidden={true} />
      <span>{spec.label}</span>
    </span>
  );
}
