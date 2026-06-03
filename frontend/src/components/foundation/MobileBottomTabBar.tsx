import { NavLink } from "react-router-dom";
import { cn } from "@/lib/cn";
import { PRIMARY_NAV_ENTRIES } from "./primaryNavEntries";

export function MobileBottomTabBar() {
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-bg md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <ul className="mx-auto flex h-16 max-w-page items-stretch">
        {PRIMARY_NAV_ENTRIES.map((entry) => {
          const Icon = entry.icon;
          return (
            <li key={entry.to} className="flex flex-1">
              <NavLink
                to={entry.to}
                end={entry.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "flex flex-1 flex-col items-center justify-center gap-1 text-meta transition-colors duration-fast ease-out",
                    isActive ? "text-accent" : "text-text-muted",
                  )
                }
              >
                <Icon size={20} aria-hidden="true" />
                <span>{entry.label}</span>
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
