import { Link } from "react-router-dom";
import { Sun, Moon } from "lucide-react";
import { PrimaryNavigation } from "./PrimaryNavigation";
import { ModeChipSlot } from "./ModeChipSlot";
import { ExpertChip } from "./ExpertChip";
import { useThemeStore } from "@/app/stores/useThemeStore";

export function Header() {
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const ThemeIcon = theme === "dark" ? Sun : Moon;

  return (
    <header
      role="banner"
      className="sticky top-0 z-30 h-[56px] w-full border-b border-border bg-bg"
    >
      <div className="mx-auto flex h-full max-w-page items-center justify-between px-4 md:px-6">
        <Link
          to="/"
          aria-label="Handoffarr — Home"
          className="text-subtitle font-semibold tracking-tight text-text"
        >
          Handoffarr
        </Link>
        <PrimaryNavigation />
        <ModeChipSlot>
          <ExpertChip />
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-text-muted transition-colors duration-fast ease-out hover:bg-surface-raised hover:text-text"
          >
            <ThemeIcon size={16} aria-hidden="true" />
          </button>
        </ModeChipSlot>
      </div>
    </header>
  );
}
