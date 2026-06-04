import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import {
  putCleanupSettings,
  type CleanupSettings,
  type SettingsResponse,
} from "@/api/settingsApi";
import { SettingsCard, SettingsRow } from "./SettingsCard";
import { useUnsavedChangesWarning } from "../hooks/useUnsavedChangesWarning";

interface Props {
  data: CleanupSettings | undefined;
  isLoading: boolean;
  isError: boolean;
  editable: boolean;
}

export function CleanupSettingsCard({ data, isLoading, isError, editable }: Props) {
  const [draft, setDraft] = useState<CleanupSettings | null>(data ?? null);
  const [saved, setSaved] = useState(false);
  const queryClient = useQueryClient();
  useEffect(() => setDraft(data ?? null), [data]);
  const dirty = Boolean(data && draft && JSON.stringify(data) !== JSON.stringify(draft));
  useUnsavedChangesWarning(dirty);
  const mutation = useMutation({
    mutationFn: putCleanupSettings,
    onSuccess: (response) => {
      queryClient.setQueryData<SettingsResponse>(["settings", "editable"], response);
      setDraft(response.cleanup);
      setSaved(true);
    },
  });
  const set = <K extends keyof CleanupSettings>(key: K, value: CleanupSettings[K]) => {
    setSaved(false);
    setDraft((current) => current ? { ...current, [key]: value } : current);
  };

  return (
    <SettingsCard
      id="settings-cleanup"
      title="Cleanup Rules"
      description={editable ? "Execution gates persisted to config.yaml." : "Read-only in Normal Mode. Enable Expert Mode to edit cleanup rules."}
    >
      {isLoading ? <LoadingState rows={4} label="Loading cleanup configuration" /> :
      isError || !data || !draft ? <ErrorState title="Couldn't load cleanup configuration" description="The settings endpoint is unreachable." /> :
      editable ? (
        <form className="flex flex-col gap-3" onSubmit={(event) => { event.preventDefault(); mutation.mutate(draft); }}>
          <ToggleRow label="Cleanup execution" hint="Master gate. When disabled, every execute request is rejected." checked={draft.enabled} onChange={(value) => set("enabled", value)} />
          <ToggleRow label="Single-item execution" checked={draft.allow_single_item_execution} onChange={(value) => set("allow_single_item_execution", value)} />
          <ToggleRow label="Batch execution" checked={draft.allow_batch_execution} onChange={(value) => set("allow_batch_execution", value)} />
          <ToggleRow label="Require confirmation phrase" checked={draft.require_confirmation_phrase} onChange={(value) => set("require_confirmation_phrase", value)} />
          <ToggleRow label="Require batch dry-run" checked={draft.require_batch_dry_run} onChange={(value) => set("require_batch_dry_run", value)} />
          <SettingsRow label="Max items per request" value={draft.max_items_per_request} hint="Fixed safety invariant. Single-item execution requests must contain exactly one item." />
          <NumberRow label="Max items per batch" value={draft.max_batch_items} min={1} max={1000} onChange={(value) => set("max_batch_items", value)} />
          <FormActions dirty={dirty} pending={mutation.isPending} saved={saved} error={mutation.isError} onCancel={() => { setDraft(data); setSaved(false); mutation.reset(); }} />
        </form>
      ) : (
        <dl className="flex flex-col gap-3">
          <SettingsRow label="Cleanup execution" value={<YesNo value={data.enabled} />} />
          <SettingsRow label="Single-item execution" value={<YesNo value={data.allow_single_item_execution} />} />
          <SettingsRow label="Batch execution" value={<YesNo value={data.allow_batch_execution} />} />
          <SettingsRow label="Max items per batch" value={data.max_batch_items} />
          <SettingsRow label="Max items per request" value={data.max_items_per_request} />
          <SettingsRow label="Require confirmation phrase" value={<YesNo value={data.require_confirmation_phrase} />} />
          <SettingsRow label="Require batch dry-run" value={<YesNo value={data.require_batch_dry_run} />} />
        </dl>
      )}
    </SettingsCard>
  );
}

function YesNo({ value }: { value: boolean }) {
  return <span className={value ? "text-success" : "text-text-muted"}>{value ? "Enabled" : "Disabled"}</span>;
}

function ToggleRow({ label, hint, checked, onChange }: { label: string; hint?: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex items-start justify-between gap-4 border-t border-border pt-3 first:border-t-0 first:pt-0">
      <span className="flex flex-col">
        <span className="text-body font-semibold text-text">{label}</span>
        {hint ? <span className="text-meta text-text-muted">{hint}</span> : null}
      </span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="mt-1 h-5 w-5 accent-accent" />
    </label>
  );
}

function NumberRow({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (value: number) => void }) {
  return (
    <label className="flex items-center justify-between gap-4 border-t border-border pt-3">
      <span className="text-body font-semibold text-text">{label}</span>
      <input aria-label={label} type="number" min={min} max={max} required value={value} onChange={(event) => onChange(Number(event.target.value))} className="h-9 w-28 rounded-md border border-border bg-bg px-3 text-right text-body text-text" />
    </label>
  );
}

function FormActions({ dirty, pending, saved, error, onCancel }: { dirty: boolean; pending: boolean; saved: boolean; error: boolean; onCancel: () => void }) {
  return (
    <div className="flex flex-wrap items-center justify-end gap-3 border-t border-border pt-4">
      <span className="mr-auto text-meta text-text-muted">
        {error ? "Couldn't save settings." : saved ? "Settings saved." : dirty ? "Unsaved changes" : "No unsaved changes"}
      </span>
      {saved || error ? <div role={error ? "alert" : "status"} className={`fixed bottom-5 right-5 z-50 rounded-lg px-4 py-3 text-body shadow-elev-2 ${error ? "bg-critical-quiet text-critical" : "bg-success-quiet text-success"}`}>{error ? "Couldn't save cleanup rules." : "Cleanup rules saved."}</div> : null}
      <button type="button" disabled={!dirty || pending} onClick={onCancel} className="rounded-md px-4 py-2 text-body font-semibold text-text-muted disabled:opacity-50">Cancel</button>
      <button type="submit" disabled={!dirty || pending} className="rounded-md bg-accent px-4 py-2 text-body font-semibold text-accent-on disabled:opacity-50">{pending ? "Saving..." : "Save"}</button>
    </div>
  );
}
