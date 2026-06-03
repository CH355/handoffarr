import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { SettingsCard, SettingsRow } from "./SettingsCard";

interface CleanupSettingsCardProps {
  config: Record<string, unknown> | undefined;
  isLoading: boolean;
  isError: boolean;
}

function bool(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  return null;
}

function num(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  return null;
}

function str(value: unknown): string | null {
  if (typeof value === "string" && value.length > 0) return value;
  return null;
}

function arr(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((v): v is string => typeof v === "string");
}

function YesNo({ value }: { value: boolean | null }) {
  if (value === null) return <span className="text-text-muted">Unknown</span>;
  return (
    <span className={value ? "text-success" : "text-text-muted"}>
      {value ? "Enabled" : "Disabled"}
    </span>
  );
}

/* Cleanup Settings.

   Pulls the live cleanup_execution.* block out of /api/cleanup/executions
   (cleanup_execution.config_status). Field names match app/config.py
   DEFAULTS["cleanup_execution"] exactly — no inventing. */
export function CleanupSettingsCard({
  config,
  isLoading,
  isError,
}: CleanupSettingsCardProps) {
  return (
    <SettingsCard
      id="settings-cleanup"
      title="Cleanup Rules"
      description="Execution gates from cleanup_execution.* in config.yaml. Read-only — Handoffarr never auto-deletes."
    >
      {isLoading ? (
        <LoadingState rows={3} label="Loading cleanup configuration" />
      ) : isError || !config ? (
        <ErrorState
          title="Couldn't load cleanup configuration"
          description="The /api/cleanup/executions endpoint is unreachable."
        />
      ) : (
        <dl className="flex flex-col gap-3">
          <SettingsRow
            label="Cleanup execution"
            value={<YesNo value={bool(config.enabled)} />}
            hint="Master gate. When disabled, every execute request is rejected."
          />
          <SettingsRow
            label="Single-item execution"
            value={<YesNo value={bool(config.allow_single_item_execution)} />}
          />
          <SettingsRow
            label="Batch execution"
            value={<YesNo value={bool(config.allow_batch_execution)} />}
          />
          <SettingsRow
            label="Max items per batch"
            value={num(config.max_batch_items) ?? "—"}
          />
          <SettingsRow
            label="Max items per request"
            value={num(config.max_items_per_request) ?? "—"}
          />
          <SettingsRow
            label="Allowed review class"
            value={str(config.allowed_review_class) ?? "—"}
          />
          <SettingsRow
            label="Require confirmation phrase"
            value={<YesNo value={bool(config.require_confirmation_phrase)} />}
          />
          <SettingsRow
            label="Require batch dry-run"
            value={<YesNo value={bool(config.require_batch_dry_run)} />}
          />
          <AllowedMatchStrengths values={arr(config.allowed_match_strengths)} />
        </dl>
      )}
    </SettingsCard>
  );
}

function AllowedMatchStrengths({ values }: { values: string[] }) {
  return (
    <div className="flex flex-col gap-2 border-t border-border pt-3">
      <span className="text-body font-semibold text-text">
        Allowed match strengths
      </span>
      {values.length === 0 ? (
        <span className="text-meta text-text-muted">None configured</span>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {values.map((v) => (
            <li
              key={v}
              className="rounded-pill border border-border bg-surface-raised px-3 py-1 text-meta text-text"
            >
              {v}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
