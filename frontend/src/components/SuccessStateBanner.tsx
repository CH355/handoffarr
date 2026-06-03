import type { ReactNode } from "react";
import { CheckCircle2, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/cn";

interface SuccessStateBannerProps {
  variant?: "success" | "partial-fail";
  title: string;
  description?: string;
  meta?: string;
  actions?: ReactNode;
}

/* SuccessStateBanner — Foundation §9, Roadmap success-with-Undo pattern.
   Renders inline below the action that produced it. */
export function SuccessStateBanner({
  variant = "success",
  title,
  description,
  meta,
  actions,
}: SuccessStateBannerProps) {
  const isPartial = variant === "partial-fail";
  const Icon = isPartial ? AlertTriangle : CheckCircle2;
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "flex flex-col gap-3 rounded-lg p-4 md:flex-row md:items-start md:justify-between",
        isPartial ? "bg-caution-quiet" : "bg-success-quiet",
      )}
    >
      <div className="flex items-start gap-3">
        <Icon
          size={20}
          aria-hidden="true"
          className={cn("mt-0.5", isPartial ? "text-caution" : "text-success")}
        />
        <div className="flex flex-col gap-1">
          <p className="text-subtitle text-text">{title}</p>
          {description ? (
            <p className="text-body text-text-muted">{description}</p>
          ) : null}
          {meta ? <p className="text-meta text-text-subtle">{meta}</p> : null}
        </div>
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}
