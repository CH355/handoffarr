import type { ReactNode } from "react";
import { AlertOctagon } from "lucide-react";

interface ErrorStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

/* Foundation §10.3 — section-level error: state what failed and what to do. */
export function ErrorState({ title, description, action }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex flex-col gap-3 rounded-lg bg-critical-quiet p-5 text-text"
    >
      <div className="flex items-start gap-3">
        <AlertOctagon size={20} className="mt-0.5 text-critical" aria-hidden="true" />
        <div className="flex flex-col gap-1">
          <p className="text-subtitle">{title}</p>
          {description ? <p className="text-body text-text-muted">{description}</p> : null}
        </div>
      </div>
      {action ? <div className="flex justify-end">{action}</div> : null}
    </div>
  );
}
