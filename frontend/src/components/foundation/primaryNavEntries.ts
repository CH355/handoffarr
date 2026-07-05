import { Home, Sparkles, Library, Download, HeartPulse, Settings, type LucideIcon } from "lucide-react";

export interface PrimaryNavEntry {
  label: string;
  to: string;
  icon: LucideIcon;
}

export const PRIMARY_NAV_ENTRIES: readonly PrimaryNavEntry[] = [
  { label: "Home", to: "/", icon: Home },
  { label: "Recover space", to: "/recover", icon: Sparkles },
  { label: "Library", to: "/library", icon: Library },
  { label: "Downloads", to: "/torrents", icon: Download },
  { label: "Health", to: "/health", icon: HeartPulse },
  { label: "Settings", to: "/settings", icon: Settings },
];
