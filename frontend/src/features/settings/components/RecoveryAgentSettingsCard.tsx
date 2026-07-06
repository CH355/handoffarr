import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getRecoveryAgentStatus,
  updateRecoveryAgentSettings,
} from "@/api/recoveryAgentApi";
import { SettingsCard } from "./SettingsCard";

export function RecoveryAgentSettingsCard() {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["recovery-agent", "status"],
    queryFn: getRecoveryAgentStatus,
  });
  const [enabled, setEnabled] = useState(true);
  const [interval, setInterval] = useState(15);
  useEffect(() => {
    if (query.data) {
      setEnabled(query.data.enabled);
      setInterval(query.data.interval_minutes);
    }
  }, [query.data]);
  const save = useMutation({
    mutationFn: () => updateRecoveryAgentSettings(enabled, interval),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: ["recovery-agent"] }),
  });
  return (
    <SettingsCard
      id="settings-recovery-agent"
      title="Recovery Agent"
      description="Evaluates downloads and generates plans. It never executes them."
    >
      <label className="flex items-center justify-between gap-4">
        <span className="text-body font-semibold text-text">Enabled</span>
        <input
          type="checkbox"
          checked={enabled}
          onChange={(event) => setEnabled(event.target.checked)}
          className="h-5 w-5 accent-accent"
        />
      </label>
      <label className="flex items-center justify-between gap-4 border-t border-border pt-3">
        <span className="text-body font-semibold text-text">
          Evaluation interval
        </span>
        <select
          value={interval}
          onChange={(event) => setInterval(Number(event.target.value))}
          className="rounded-md border border-border bg-surface px-3 py-2 text-text"
        >
          {[5, 10, 15, 30, 60].map((value) => (
            <option key={value} value={value}>
              {value} minutes
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        disabled={save.isPending || query.isLoading}
        onClick={() => save.mutate()}
        className="self-start rounded-md bg-accent px-4 py-2 text-body font-semibold text-accent-on disabled:opacity-60"
      >
        {save.isPending ? "Saving…" : "Save"}
      </button>
    </SettingsCard>
  );
}
