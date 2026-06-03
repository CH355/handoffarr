import { SettingsCard, SettingsRow } from "./SettingsCard";

/* About / Version.

   Handoffarr does not expose a version, git commit, or build timestamp
   endpoint today. Per the sprint brief we "gracefully degrade if
   unavailable" rather than invent values. */
export function AboutCard() {
  return (
    <SettingsCard
      id="settings-about"
      title="About"
      description="Build metadata is not currently exposed by the backend."
    >
      <dl className="flex flex-col gap-3">
        <SettingsRow
          label="Application"
          value="Handoffarr"
          hint="Read-only dashboard tracing the Seerr → Radarr → qBittorrent hand-off."
        />
        <SettingsRow
          label="Version"
          value={<span className="text-text-muted">Not reported</span>}
        />
        <SettingsRow
          label="Git commit"
          value={<span className="text-text-muted">Not reported</span>}
        />
        <SettingsRow
          label="Build timestamp"
          value={<span className="text-text-muted">Not reported</span>}
        />
      </dl>
    </SettingsCard>
  );
}
