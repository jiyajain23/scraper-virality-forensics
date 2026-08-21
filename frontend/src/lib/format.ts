export function num(value: unknown, fallback = "—"): string {
  if (typeof value !== "number" || Number.isNaN(value)) return fallback;
  return Math.round(value).toLocaleString("en-US");
}

export function decimal(value: unknown, digits = 2, fallback = "—"): string {
  if (typeof value !== "number" || Number.isNaN(value)) return fallback;
  return value.toFixed(digits);
}

/** Accepts either 0–1 probability or 0–100 percent from the backend. */
export function toPercent(value: unknown): number | null {
  if (typeof value !== "number" || Number.isNaN(value)) return null;
  return value <= 1 ? value * 100 : value;
}

export function percentLabel(value: unknown, digits = 1, fallback = "—"): string {
  const pct = toPercent(value);
  if (pct === null) return fallback;
  return `${pct.toFixed(digits)}%`;
}

export function signedDelta(value: unknown, digits = 1): string | null {
  const pct = toPercent(value);
  if (pct === null) return null;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(digits)} pts`;
}

export function timeLabel(value: unknown): string {
  if (typeof value !== "string" && typeof value !== "number") return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

export function dateTimeLabel(value: unknown): string {
  if (typeof value !== "string" && typeof value !== "number") return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function hourWindow(hour: unknown): string | null {
  if (typeof hour !== "number" || Number.isNaN(hour)) return null;
  const start = String(Math.floor(hour)).padStart(2, "0");
  const end = String((Math.floor(hour) + 2) % 24).padStart(2, "0");
  return `${start}:00–${end}:00 UTC`;
}

export function domainFromUrl(url: unknown): string | null {
  if (typeof url !== "string" || !url) return null;
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}
