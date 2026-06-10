import { formatDistanceToNowStrict } from "date-fns";

export function relativeDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return formatDistanceToNowStrict(new Date(iso), { addSuffix: true });
  } catch {
    return "—";
  }
}

export function salaryRange(
  min: number | null,
  max: number | null,
  currency: string | null,
): string | null {
  if (!min && !max) return null;
  const fmt = (n: number) =>
    n >= 1000 ? `${Math.round(n / 1000)}k` : String(n);
  const cur = currency ? `${currency} ` : "";
  if (min && max) return `${cur}${fmt(min)}–${fmt(max)}`;
  return `${cur}${fmt((min ?? max)!)}`;
}

export const WORK_MODE_STYLES: Record<string, string> = {
  remote: "bg-emerald-50 text-emerald-700 border-emerald-200",
  hybrid: "bg-amber-50 text-amber-700 border-amber-200",
  onsite: "bg-sky-50 text-sky-700 border-sky-200",
  unknown: "bg-muted text-muted-foreground border-border",
};

export const STATUS_STYLES: Record<string, string> = {
  saved: "bg-muted text-muted-foreground border-border",
  applied: "bg-blue-50 text-blue-700 border-blue-200",
  interviewing: "bg-violet-50 text-violet-700 border-violet-200",
  offer: "bg-emerald-50 text-emerald-700 border-emerald-200",
  rejected: "bg-red-50 text-red-600 border-red-200",
};
