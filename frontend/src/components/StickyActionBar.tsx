import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

interface StickyActionBarProps {
  primary: ReactNode;
  meta?: ReactNode;
  secondary?: ReactNode;
  className?: string;
}

/* StickyActionBar — Mockups §3. Sits above the mobile bottom-tab bar via
   bottom padding; uses safe-area inset on devices that report one. */
export function StickyActionBar({ primary, meta, secondary, className }: StickyActionBarProps) {
  return (
    <div
      className={cn(
        "sticky bottom-16 z-30 mt-6 md:bottom-0",
        "border-t border-border bg-surface-raised shadow-elev-2",
        "rounded-t-lg",
        className,
      )}
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0)" }}
    >
      <div className="mx-auto flex w-full max-w-page flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:justify-between md:px-6">
        <div className="text-body text-text-muted">{meta}</div>
        <div className="flex items-center gap-2">
          {secondary}
          {primary}
        </div>
      </div>
    </div>
  );
}
