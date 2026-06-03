import { Link } from "react-router-dom";
import { AlertOctagon, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/cn";

type BannerVariant = "critical" | "recover" | "stuck" | "idle";

interface PrimaryBannerProps {
  variant: BannerVariant;
  headline: string;
  accentNumeral?: string | undefined;
  subline?: string | undefined;
  actionLabel?: string | undefined;
  actionTo?: string | undefined;
  meta?: string | undefined;
}

/* Foundation §9.2 Primary Banner. Content drives meaning; banner background
   does not change between Recover / Stuck variants. */
export function PrimaryBanner({
  variant,
  headline,
  accentNumeral,
  subline,
  actionLabel,
  actionTo,
  meta,
}: PrimaryBannerProps) {
  const numeralClass =
    variant === "critical" ? "text-critical" : "text-accent";

  return (
    <section
      aria-labelledby="primary-banner-headline"
      className="flex flex-col gap-4 rounded-lg bg-surface p-6 shadow-elev-1 md:p-8"
    >
      <div className="flex items-start gap-3">
        {variant === "critical" ? (
          <AlertOctagon
            size={20}
            className="mt-2 shrink-0 text-critical"
            aria-hidden="true"
          />
        ) : variant === "idle" ? (
          <CheckCircle2
            size={20}
            className="mt-2 shrink-0 text-success"
            aria-hidden="true"
          />
        ) : null}
        <h2
          id="primary-banner-headline"
          className={cn(
            "text-display text-text",
            variant === "idle" && "font-semibold",
          )}
        >
          {accentNumeral ? (
            <>
              <span
                className={cn("font-bold tabular-nums", numeralClass)}
              >
                {accentNumeral}
              </span>{" "}
            </>
          ) : null}
          {headline}
        </h2>
      </div>

      {subline ? (
        <p className="text-body text-text-muted">{subline}</p>
      ) : null}

      {actionLabel && actionTo ? (
        <div className="flex">
          <Link
            to={actionTo}
            className="inline-flex h-10 items-center justify-center rounded-md bg-accent px-5 text-body font-semibold text-accent-on transition-colors duration-fast ease-out hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            {actionLabel}
          </Link>
        </div>
      ) : null}

      {meta ? <p className="text-meta text-text-subtle">{meta}</p> : null}
    </section>
  );
}
