import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { SettingsCard } from "./SettingsCard";

export function DiagnosticsSettingsCard() {
  return (
    <SettingsCard
      id="settings-diagnostics"
      title="Diagnostics"
      description="View validation, collector, execution, and timeline details."
    >
      <Link
        to="/settings/diagnostics"
        className="flex items-center justify-between gap-4 rounded-md border border-border px-4 py-3 text-body font-semibold text-text transition-colors duration-fast hover:bg-surface-raised focus-visible:bg-surface-raised"
      >
        <span>Open Diagnostics</span>
        <ChevronRight size={18} aria-hidden="true" className="text-text-muted" />
      </Link>
    </SettingsCard>
  );
}
