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

// Soft indigo tag — the brand's pill-tag-soft, for departments / skills
export const TAG_STYLE =
  "border-transparent bg-brand-subtle/45 text-brand-press font-normal";

export const WORK_MODE_STYLES: Record<string, string> = {
  remote: "border-transparent bg-emerald-500/12 text-emerald-700",
  hybrid: "border-transparent bg-cream text-[#9b6829]",
  onsite: "border-transparent bg-brand-subtle/40 text-brand-press",
  unknown: "border-transparent bg-secondary text-muted-foreground",
};

export const STATUS_STYLES: Record<string, string> = {
  saved: "border-transparent bg-secondary text-ink-secondary",
  applied: "border-transparent bg-brand-subtle/45 text-brand-press",
  interviewing: "border-transparent bg-magenta/15 text-[#b4258f]",
  offer: "border-transparent bg-emerald-500/14 text-emerald-700",
  rejected: "border-transparent bg-ruby/12 text-ruby",
};
