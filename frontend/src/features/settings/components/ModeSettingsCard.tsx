import { useModeStore } from "@/app/stores/useModeStore";
import { SettingsCard } from "./SettingsCard";

export function ModeSettingsCard() {
  const mode = useModeStore((s) => s.mode);
  const setMode = useModeStore((s) => s.setMode);
  const expert = mode === "expert";

  return (
    <SettingsCard
      id="settings-mode"
      title="Mode"
      description="Expert Mode shows diagnostics, lifecycle history, and source trails."
    >
      <label className="flex cursor-pointer items-start justify-between gap-5 border-t border-border pt-3">
        <span className="flex flex-col gap-1">
          <span className="text-body font-semibold text-text">Expert Mode</span>
          <span className="text-meta text-text-muted">
            Diagnostics is available only while Expert Mode is active.
          </span>
        </span>
        <span className="flex shrink-0 items-center gap-2">
          <input
            type="checkbox"
            checked={expert}
            onChange={(event) => setMode(event.target.checked ? "expert" : "normal")}
            className="h-5 w-5 accent-accent"
          />
          <span className="text-meta uppercase tracking-wide text-text-muted">
            {expert ? "On" : "Off"}
          </span>
        </span>
      </label>
    </SettingsCard>
  );
}
