import type { ReactNode } from "react";
import { CheckCircle2 } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

/* Foundation §10.1 — idle success. Centered column, calm and confident. */
export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="mx-auto flex max-w-[360px] flex-col items-center gap-3 py-12 text-center">
      <CheckCircle2 size={24} className="text-success" aria-hidden="true" />
      <p className="text-title text-text">{title}</p>
      {description ? <p className="text-meta text-text-muted">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
