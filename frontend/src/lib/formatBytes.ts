const UNITS = ["B", "KB", "MB", "GB", "TB", "PB"] as const;

/* Compact human-readable bytes. Foundation §5 typographic numerals are
   tabular at the body level; this returns a single string. */
export function formatBytes(bytes: number | null | undefined, fractionDigits = 1): string {
  if (bytes == null || !Number.isFinite(bytes)) return "—";
  if (bytes <= 0) return "0 B";
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < UNITS.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  const digits = unitIndex === 0 ? 0 : fractionDigits;
  return `${value.toFixed(digits)} ${UNITS[unitIndex]}`;
}
