import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { formatBytes } from "@/lib/formatBytes";
import {
  putStorageSettings,
  type SettingsResponse,
  type StorageSettings,
} from "@/api/settingsApi";
import { SettingsCard, SettingsRow } from "./SettingsCard";
import { useUnsavedChangesWarning } from "../hooks/useUnsavedChangesWarning";

interface Props {
  data: StorageSettings | undefined;
  isLoading: boolean;
  isError: boolean;
  editable: boolean;
}

export function RuntimeSettingsCard({ data, isLoading, isError, editable }: Props) {
  const [draft, setDraft] = useState<StorageSettings | null>(data ?? null);
  const [saved, setSaved] = useState(false);
  const queryClient = useQueryClient();
  useEffect(() => setDraft(data ?? null), [data]);
  const dirty = Boolean(data && draft && JSON.stringify(data) !== JSON.stringify(draft));
  const valid = Boolean(draft && draft.critical_free_bytes > 0 && draft.warning_free_bytes > draft.critical_free_bytes && draft.completed_torrent_count >= 0 && draft.retained_bytes >= 0);
  useUnsavedChangesWarning(dirty);
  const mutation = useMutation({
    mutationFn: putStorageSettings,
    onSuccess: (response) => {
      queryClient.setQueryData<SettingsResponse>(["settings", "editable"], response);
      setDraft(response.storage);
      setSaved(true);
    },
  });
  const set = (key: keyof StorageSettings, value: number) => {
    setSaved(false);
    setDraft((current) => current ? { ...current, [key]: value } : current);
  };

  return (
    <SettingsCard
      id="settings-runtime"
      title="Runtime Limits"
      description={editable ? "Storage thresholds persisted to config.yaml." : "Read-only in Normal Mode. Enable Expert Mode to edit runtime limits."}
    >
      {isLoading ? <LoadingState rows={3} label="Loading runtime limits" /> :
      isError || !data || !draft ? <ErrorState title="Couldn't load runtime limits" description="The settings endpoint is unreachable." /> :
      editable ? (
        <form className="flex flex-col gap-3" onSubmit={(event) => { event.preventDefault(); if (valid) mutation.mutate(draft); }}>
          <ByteInput label="Storage warning threshold" value={draft.warning_free_bytes} onChange={(value) => set("warning_free_bytes", value)} />
          <ByteInput label="Storage critical threshold" value={draft.critical_free_bytes} onChange={(value) => set("critical_free_bytes", value)} />
          <ByteInput label="Retained torrents size threshold" value={draft.retained_bytes} allowZero onChange={(value) => set("retained_bytes", value)} />
          <CountInput label="Retained torrents count threshold" value={draft.completed_torrent_count} onChange={(value) => set("completed_torrent_count", value)} />
          {!valid ? <p role="alert" className="text-meta text-critical">Warning threshold must exceed critical threshold. Values cannot be negative.</p> : null}
          <div className="flex flex-wrap items-center justify-end gap-3 border-t border-border pt-4">
            <span className="mr-auto text-meta text-text-muted">{mutation.isError ? "Couldn't save settings." : saved ? "Settings saved." : dirty ? "Unsaved changes" : "No unsaved changes"}</span>
            {saved || mutation.isError ? <div role={mutation.isError ? "alert" : "status"} className={`fixed bottom-5 right-5 z-50 rounded-lg px-4 py-3 text-body shadow-elev-2 ${mutation.isError ? "bg-critical-quiet text-critical" : "bg-success-quiet text-success"}`}>{mutation.isError ? "Couldn't save runtime limits." : "Runtime limits saved."}</div> : null}
            <button type="button" disabled={!dirty || mutation.isPending} onClick={() => { setDraft(data); setSaved(false); mutation.reset(); }} className="rounded-md px-4 py-2 text-body font-semibold text-text-muted disabled:opacity-50">Cancel</button>
            <button type="submit" disabled={!dirty || !valid || mutation.isPending} className="rounded-md bg-accent px-4 py-2 text-body font-semibold text-accent-on disabled:opacity-50">{mutation.isPending ? "Saving..." : "Save"}</button>
          </div>
        </form>
      ) : (
        <dl className="flex flex-col gap-3">
          <SettingsRow label="Storage warning threshold" value={formatBytes(data.warning_free_bytes)} />
          <SettingsRow label="Storage critical threshold" value={formatBytes(data.critical_free_bytes)} />
          <SettingsRow label="Retained torrents size threshold" value={formatBytes(data.retained_bytes)} />
          <SettingsRow label="Retained torrents count threshold" value={data.completed_torrent_count} />
        </dl>
      )}
    </SettingsCard>
  );
}

function ByteInput({ label, value, allowZero = false, onChange }: { label: string; value: number; allowZero?: boolean; onChange: (value: number) => void }) {
  return (
    <label className="flex flex-col gap-1 border-t border-border pt-3 first:border-t-0 first:pt-0 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
      <span className="text-body font-semibold text-text">{label}</span>
      <span className="flex items-center gap-3">
        <input type="number" aria-label={`${label} in bytes`} required min={allowZero ? 0 : 1} value={value} onChange={(event) => onChange(Number(event.target.value))} className="h-9 w-52 rounded-md border border-border bg-bg px-3 text-right text-body text-text" />
        <span className="w-20 text-right text-meta text-text-muted">{formatBytes(value)}</span>
      </span>
    </label>
  );
}

function CountInput({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <label className="flex items-center justify-between gap-4 border-t border-border pt-3">
      <span className="text-body font-semibold text-text">{label}</span>
      <input type="number" aria-label={label} required min={0} max={1_000_000} value={value} onChange={(event) => onChange(Number(event.target.value))} className="h-9 w-32 rounded-md border border-border bg-bg px-3 text-right text-body text-text" />
    </label>
  );
}
