import type { ReactNode } from "react";

interface SettingsCardProps {
  id: string;
  title: string;
  description?: string;
  children: ReactNode;
}

/* Mockups §8 — sectioned card with small-caps tracked title, sequential
   layout. Used by every Settings section so spacing and heading style stay
   uniform across General / Integrations / Cleanup / Runtime / About. */
export function SettingsCard({ id, title, description, children }: SettingsCardProps) {
  const titleId = `${id}-title`;
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-4 rounded-lg bg-surface p-5 shadow-elev-1"
    >
      <header className="flex flex-col gap-1">
        <h2
          id={titleId}
          className="text-meta uppercase tracking-wide text-text-muted"
        >
          {title}
        </h2>
        {description ? (
          <p className="text-body text-text-muted">{description}</p>
        ) : null}
      </header>
      {children}
    </section>
  );
}

interface SettingsRowProps {
  label: string;
  value: ReactNode;
  hint?: string;
}

/* Single key/value row inside a SettingsCard. Label on the left, value on
   the right (tabular for numeric values). On mobile rows stack. */
export function SettingsRow({ label, value, hint }: SettingsRowProps) {
  return (
    <div className="flex flex-col gap-1 border-t border-border pt-3 first:border-t-0 first:pt-0 sm:flex-row sm:items-baseline sm:justify-between sm:gap-6">
      <div className="flex flex-col">
        <span className="text-body font-semibold text-text">{label}</span>
        {hint ? (
          <span className="text-meta text-text-muted">{hint}</span>
        ) : null}
      </div>
      <div className="text-body tabular-nums text-text sm:text-right">
        {value}
      </div>
    </div>
  );
}
