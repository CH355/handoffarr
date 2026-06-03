const MINUTE = 60;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;
const WEEK = 7 * DAY;

/* Foundation §5.5 — Normal Mode timestamps are relative. */
export function formatRelativeTime(
  value: string | number | Date | null | undefined,
  now: Date = new Date(),
): string {
  if (value == null || value === "") return "—";
  const date = value instanceof Date ? value : new Date(value);
  const ts = date.getTime();
  if (!Number.isFinite(ts)) return "—";

  const diffSeconds = Math.round((now.getTime() - ts) / 1000);
  if (diffSeconds < 30) return "just now";
  if (diffSeconds < HOUR) {
    const mins = Math.max(1, Math.round(diffSeconds / MINUTE));
    return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  }
  if (diffSeconds < DAY) {
    const hrs = Math.round(diffSeconds / HOUR);
    return `${hrs} hour${hrs === 1 ? "" : "s"} ago`;
  }
  if (diffSeconds < 2 * DAY) return "yesterday";
  if (diffSeconds < WEEK) {
    const days = Math.round(diffSeconds / DAY);
    return `${days} days ago`;
  }
  const weeks = Math.round(diffSeconds / WEEK);
  if (weeks < 5) return `${weeks} week${weeks === 1 ? "" : "s"} ago`;
  const months = Math.round(diffSeconds / (30 * DAY));
  if (months < 12) return `${months} month${months === 1 ? "" : "s"} ago`;
  const years = Math.round(diffSeconds / (365 * DAY));
  return `${years} year${years === 1 ? "" : "s"} ago`;
}
