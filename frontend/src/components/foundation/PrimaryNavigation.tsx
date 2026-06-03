import { NavLink } from "react-router-dom";
import { cn } from "@/lib/cn";
import { PRIMARY_NAV_ENTRIES } from "./primaryNavEntries";

export function PrimaryNavigation() {
  return (
    <nav aria-label="Primary" className="hidden md:block">
      <ul className="flex items-center gap-1">
        {PRIMARY_NAV_ENTRIES.map((entry) => (
          <li key={entry.to}>
            <NavLink
              to={entry.to}
              end={entry.to === "/"}
              className={({ isActive }) =>
                cn(
                  "inline-flex items-center rounded-md px-3 py-2 text-body transition-colors duration-fast ease-out",
                  isActive
                    ? "bg-accent-quiet text-accent"
                    : "text-text-muted hover:bg-surface-raised hover:text-text",
                )
              }
            >
              {entry.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
