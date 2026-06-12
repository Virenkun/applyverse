"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Briefcase,
  Building2,
  ChevronDown,
  ExternalLink,
  Search,
  X,
} from "lucide-react";

import { JobCard } from "@/components/job-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { STATUS_STYLES, TAG_STYLE } from "@/lib/format";
import type { CompanyWithCounts } from "@/lib/types";
import { cn } from "@/lib/utils";

function CompanyRow({ company }: { company: CompanyWithCounts }) {
  const [open, setOpen] = useState(false);
  const jobs = useQuery({
    queryKey: ["companies", company.id, "jobs"],
    queryFn: () => api.companies.jobs(company.id),
    enabled: open,
  });

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card shadow-[0_1px_3px_rgba(0,55,112,0.08)]">
      <button
        className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-accent/40"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-brand-wash">
          <Building2 className="size-4 text-brand" />
        </span>
        <span className="min-w-0 truncate font-medium text-ink">
          {company.name}
        </span>
        {company.ats_type && (
          <Badge variant="outline" className={cn("shrink-0", TAG_STYLE)}>
            {company.ats_type}
          </Badge>
        )}
        <span className="ml-auto flex shrink-0 items-center gap-3 text-sm text-ink-mute">
          {company.applications > 0 && (
            <Badge
              variant="outline"
              className={cn("tnum capitalize", STATUS_STYLES.applied)}
            >
              {company.applications} applied
            </Badge>
          )}
          <span className="tnum tabular-nums">
            {company.open_jobs} open
          </span>
          {company.website && (
            <a
              href={company.website}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-ink-mute transition-colors hover:text-brand"
              title="Company website"
            >
              <ExternalLink className="size-3.5" />
            </a>
          )}
          <ChevronDown
            className={cn(
              "size-4 text-ink-mute transition-transform",
              open && "rotate-180",
            )}
          />
        </span>
      </button>
      {open && (
        <div className="space-y-3 border-t border-border bg-background/40 p-4">
          {jobs.isLoading &&
            Array.from({ length: 2 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-lg" />
            ))}
          {(jobs.data ?? []).map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
          {jobs.isSuccess && jobs.data.length === 0 && (
            <p className="py-2 text-sm text-ink-mute">No active jobs.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function CompaniesPage() {
  const [appliedOnly, setAppliedOnly] = useState(false);
  const [search, setSearch] = useState("");

  const { data: companies, isLoading } = useQuery({
    queryKey: ["companies", { appliedOnly }],
    queryFn: () => api.companies.list(appliedOnly),
  });

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const list = companies ?? [];
    if (!q) return list;
    return list.filter((c) => c.name.toLowerCase().includes(q));
  }, [companies, search]);

  return (
    <div className="flex h-dvh flex-col">
      {/* Fixed header */}
      <div className="shrink-0 border-b border-border bg-background px-6 pb-3 pt-6">
        <div className="mx-auto max-w-4xl">
          <div className="mb-3 flex items-baseline justify-between">
            <h1 className="text-[1.9rem] text-ink">Companies</h1>
            {companies && (
              <span className="tnum text-sm text-ink-mute">
                {filtered.length.toLocaleString()}
                {search || appliedOnly ? " shown" : " companies"}
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <div className="relative min-w-48 flex-1">
              <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search companies…"
                className="bg-card pl-8"
              />
            </div>
            <Button
              variant={appliedOnly ? "default" : "outline"}
              size="default"
              onClick={() => setAppliedOnly((v) => !v)}
            >
              Applied only
            </Button>
            {(search || appliedOnly) && (
              <Button
                variant="ghost"
                size="default"
                onClick={() => {
                  setSearch("");
                  setAppliedOnly(false);
                }}
              >
                <X className="size-3.5" /> Clear
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Scroll region — stable gutter so card width never shifts on expand */}
      <div className="flex-1 overflow-y-auto px-6 py-4 scrollbar-gutter-stable">
        <div className="mx-auto max-w-4xl space-y-2">
          {isLoading &&
            Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-lg" />
            ))}
          {filtered.map((c) => (
            <CompanyRow key={c.id} company={c} />
          ))}
          {companies && filtered.length === 0 && (
            <div className="rounded-lg border border-dashed border-border py-16 text-center">
              <Briefcase className="mx-auto mb-2 size-6 text-ink-mute" />
              <p className="text-sm text-ink-mute">
                {search
                  ? `No companies match “${search}”.`
                  : "No companies yet."}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
