import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";

interface EvidenceDrawerProps {
  open: boolean;
  onClose: () => void;
  label: string;
  triggerRef?: React.RefObject<HTMLElement>;
  children: ReactNode;
}

/* EvidenceDrawer — Sprint 3 stub per frontend-implementation-spec-v1.md §11.3.
   Full body lands in Sprint 4. Right-side drawer ≥md, bottom sheet on mobile.
   Focus is moved into the drawer on open and returned to triggerRef on close. */
export function EvidenceDrawer({
  open,
  onClose,
  label,
  triggerRef,
  children,
}: EvidenceDrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = (document.activeElement as HTMLElement | null) ?? null;
    panelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      const target = triggerRef?.current ?? previouslyFocused;
      target?.focus?.();
    };
  }, [open, onClose, triggerRef]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-bg/60 backdrop-blur-sm"
      />
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        className={cn(
          "relative ml-auto flex h-full w-full max-w-[480px] flex-col gap-4",
          "bg-surface-raised p-5 shadow-elev-3 outline-none",
          "md:rounded-l-lg",
        )}
      >
        <header className="flex items-start justify-between gap-3">
          <h2 className="text-subtitle text-text">{label}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close evidence drawer"
            className="rounded-md p-1 text-text-muted hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto pr-1 text-body text-text">{children}</div>
      </div>
    </div>
  );
}
