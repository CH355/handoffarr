import { useEffect, useId, useRef, useState } from "react";
import { cn } from "@/lib/cn";

interface InlineConfirmationStripProps {
  expectedPhrase: string;
  prompt: string;
  helpText?: string;
  confirmLabel: string;
  cancelLabel?: string;
  destructive?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/* InlineConfirmationStrip — Foundation §9.10 / Blueprint v1.1 C1.
   A strip, not a card: confirmation lives inline next to the action it confirms.
   Confirm is disabled until the typed phrase matches exactly. */
export function InlineConfirmationStrip({
  expectedPhrase,
  prompt,
  helpText,
  confirmLabel,
  cancelLabel = "Cancel",
  destructive = true,
  busy = false,
  onConfirm,
  onCancel,
}: InlineConfirmationStripProps) {
  const inputId = useId();
  const helpId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState("");
  const matches = value === expectedPhrase;

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <div
      role="group"
      aria-label="Confirm action"
      className={cn(
        "flex flex-col gap-3 border-l-2 px-4 py-3",
        destructive ? "border-critical bg-critical-quiet" : "border-accent bg-accent-quiet",
      )}
    >
      <div className="flex flex-col gap-1">
        <label htmlFor={inputId} className="text-body text-text">
          {prompt}
        </label>
        <p id={helpId} className="text-meta text-text-muted">
          {helpText ?? (
            <>
              Type <span className="font-mono text-text">{expectedPhrase}</span> to confirm.
            </>
          )}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <input
          id={inputId}
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          aria-describedby={helpId}
          autoComplete="off"
          spellCheck={false}
          className={cn(
            "flex-1 min-w-[200px] rounded-md border bg-surface px-3 py-2 font-mono text-body text-text",
            "border-border focus-visible:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent",
          )}
        />
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="rounded-md px-3 py-2 text-body text-text hover:bg-surface focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-60"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={!matches || busy}
            className={cn(
              "rounded-md px-4 py-2 text-body font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50",
              destructive
                ? "bg-critical text-accent-on hover:bg-critical/90"
                : "bg-accent text-accent-on hover:bg-accent-hover",
            )}
          >
            {busy ? "Working…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
