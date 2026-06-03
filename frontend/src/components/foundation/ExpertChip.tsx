import { useModeStore } from "@/app/stores/useModeStore";

export function ExpertChip() {
  const mode = useModeStore((s) => s.mode);
  if (mode !== "expert") return null;
  return (
    <span
      aria-label="Expert mode active"
      className="inline-flex items-center rounded-pill bg-accent-quiet px-[10px] py-[6px] text-meta font-semibold text-accent"
      style={{ letterSpacing: "0.08em" }}
    >
      EXPERT
    </span>
  );
}
