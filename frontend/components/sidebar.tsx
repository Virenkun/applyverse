"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Briefcase,
  Building2,
  KanbanSquare,
  LayoutDashboard,
  LogOut,
  Rocket,
  Settings,
} from "lucide-react";

import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/tracker", label: "Tracker", icon: KanbanSquare },
  { href: "/companies", label: "Companies", icon: Building2 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const logout = async () => {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => null);
    router.push("/login");
    router.refresh();
  };

  return (
    <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <div className="flex h-16 items-center gap-2.5 px-5">
        <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-[0_1px_2px_rgba(0,55,112,0.25)]">
          <Rocket className="size-4" />
        </span>
        <span className="display text-lg text-ink">Applyverse</span>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 px-3 py-2">
        <p className="px-3 pb-1.5 pt-2 text-[10px] font-medium uppercase tracking-[0.12em] text-ink-mute">
          Workspace
        </p>
        {NAV.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-ink-mute transition-colors hover:bg-accent hover:text-ink",
                active &&
                  "bg-brand-wash font-medium text-brand-press hover:bg-brand-wash hover:text-brand-press",
              )}
            >
              {active && (
                <span className="absolute left-0 top-1/2 h-5 w-0.75 -translate-y-1/2 rounded-r-full bg-primary" />
              )}
              <Icon
                className={cn(
                  "size-4 transition-colors",
                  active
                    ? "text-brand"
                    : "text-ink-mute group-hover:text-ink",
                )}
              />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto space-y-2 px-4 py-4">
        <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2.5">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-2 animate-ping rounded-full bg-emerald-400 opacity-60" />
            <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
          </span>
          <span className="text-xs text-ink-mute">Scrapers running</span>
        </div>
        <button
          onClick={logout}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-ink-mute transition-colors hover:bg-accent hover:text-ink"
        >
          <LogOut className="size-4" /> Sign out
        </button>
      </div>
    </aside>
  );
}
