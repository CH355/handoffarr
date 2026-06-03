import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/cn";

export type RecommendationVariant = "safe" | "judgment" | "notRecommended";

interface RecommendationCardProps {
  variant: RecommendationVariant;
  title: string;
  description: string;
  primaryStat: string;
  primaryStatLabel: string;
  secondaryStat?: string;
  secondaryStatLabel?: string;
  actionLabel?: string;
  actionTo?: string;
  actionDisabled?: boolean;
  meta?: ReactNode;
  children?: ReactNode;
}

const variantStyles: Record<RecommendationVariant, string> = {
  safe: "border-l-2 border-success",
  judgment: "border-l-2 border-caution",
  notRecommended: "border-l-2 border-critical",
};

/* RecommendationCard — Mockups §2. Three approved variants only.
   Stat figures inside are non-clickable; navigation is via the explicit action. */
export function RecommendationCard({
  variant,
  title,
  description,
  primaryStat,
  primaryStatLabel,
  secondaryStat,
  secondaryStatLabel,
  actionLabel,
  actionTo,
  actionDisabled,
  meta,
  children,
}: RecommendationCardProps) {
  return (
    <article
      aria-label={title}
      className={cn(
        "flex flex-col gap-4 rounded-lg bg-surface p-5 shadow-elev-1",
        variantStyles[variant],
      )}
    >
      <header className="flex flex-col gap-1">
        <h3 className="text-subtitle text-text">{title}</h3>
        <p className="text-body text-text-muted">{description}</p>
      </header>

      <dl className="flex flex-wrap gap-6">
        <div className="flex flex-col">
          <dt className="text-meta text-text-subtle">{primaryStatLabel}</dt>
          <dd className="text-title text-text [font-variant-numeric:tabular-nums]">
            {primaryStat}
          </dd>
        </div>
        {secondaryStat ? (
          <div className="flex flex-col">
            <dt className="text-meta text-text-subtle">{secondaryStatLabel}</dt>
            <dd className="text-title text-text [font-variant-numeric:tabular-nums]">
              {secondaryStat}
            </dd>
          </div>
        ) : null}
      </dl>

      {children}

      <footer className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-meta text-text-subtle">{meta}</div>
        {actionLabel && actionTo ? (
          <Link
            to={actionTo}
            aria-disabled={actionDisabled || undefined}
            tabIndex={actionDisabled ? -1 : undefined}
            className={cn(
              "inline-flex items-center rounded-md px-4 py-2 text-body font-medium",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent",
              actionDisabled
                ? "pointer-events-none bg-border text-text-subtle"
                : "bg-accent text-accent-on hover:bg-accent-hover",
            )}
          >
            {actionLabel}
          </Link>
        ) : null}
      </footer>
    </article>
  );
}
