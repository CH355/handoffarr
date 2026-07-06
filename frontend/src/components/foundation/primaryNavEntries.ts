import { Home, Sparkles, Library, RefreshCcw, Bot, HeartPulse, Settings, type LucideIcon } from "lucide-react";

export interface PrimaryNavEntry {
  label: string;
  to: string;
  icon: LucideIcon;
}

export const PRIMARY_NAV_ENTRIES: readonly PrimaryNavEntry[] = [
  { label: "Home", to: "/", icon: Home },
  { label: "Recover space", to: "/recover", icon: Sparkles },
  { label: "Library", to: "/library", icon: Library },
  { label: "Recovery Center", to: "/torrents", icon: RefreshCcw },
  { label: "Recovery Agent", to: "/recovery-agent", icon: Bot },
  { label: "Health", to: "/health", icon: HeartPulse },
  { label: "Settings", to: "/settings", icon: Settings },
];
