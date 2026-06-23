import { SettingsCard, SettingsRow } from "./SettingsCard";

/* About / Version.

   Handoffarr does not expose a version, git commit, or build timestamp
   endpoint today. Keep the normal Settings surface clean by showing only
   metadata that actually exists. */
export function AboutCard() {
  return (
    <SettingsCard
      id="settings-about"
      title="About"
      description="Handoffarr is a read-only dashboard for handoff, import, and cleanup visibility."
    >
      <dl className="flex flex-col gap-3">
        <SettingsRow
          label="Application"
          value="Handoffarr"
          hint="Traces the Seerr, Radarr, qBittorrent, library, and cleanup handoff."
        />
      </dl>
    </SettingsCard>
  );
}
