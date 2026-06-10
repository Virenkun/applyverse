"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Building2, ChevronDown, ChevronRight, ExternalLink } from "lucide-react";

import { JobCard } from "@/components/job-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { CompanyWithCounts } from "@/lib/types";

function CompanyRow({ company }: { company: CompanyWithCounts }) {
  const [open, setOpen] = useState(false);
  const jobs = useQuery({
    queryKey: ["companies", company.id, "jobs"],
    queryFn: () => api.companies.jobs(company.id),
    enabled: open,
  });

  return (
    <div className="rounded-lg border bg-card">
      <button
        className="flex w-full items-center gap-3 p-4 text-left"
        onClick={() => setOpen((o) => !o)}
      >
        {open ? (
          <ChevronDown className="size-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-4 text-muted-foreground" />
        )}
        <Building2 className="size-4 text-muted-foreground" />
        <span className="font-medium">{company.name}</span>
        {company.ats_type && (
          <Badge variant="secondary" className="font-normal">
            {company.ats_type}
          </Badge>
        )}
        <span className="ml-auto flex items-center gap-3 text-sm text-muted-foreground">
          {company.applications > 0 && (
            <Badge variant="outline" className="border-blue-200 bg-blue-50 text-blue-700">
              {company.applications} application{company.applications === 1 ? "" : "s"}
            </Badge>
          )}
          <span>{company.open_jobs} open</span>
          {company.website && (
            <a
              href={company.website}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="hover:text-foreground"
            >
              <ExternalLink className="size-3.5" />
            </a>
          )}
        </span>
      </button>
      {open && (
        <div className="space-y-3 border-t p-4">
          {jobs.isLoading && <Skeleton className="h-24" />}
          {(jobs.data ?? []).map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
          {jobs.isSuccess && jobs.data.length === 0 && (
            <p className="text-sm text-muted-foreground">No active jobs.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function CompaniesPage() {
  const [appliedOnly, setAppliedOnly] = useState(false);
  const { data: companies, isLoading } = useQuery({
    queryKey: ["companies", { appliedOnly }],
    queryFn: () => api.companies.list(appliedOnly),
  });

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Companies</h1>
        <Button
          variant={appliedOnly ? "default" : "outline"}
          size="sm"
          onClick={() => setAppliedOnly((v) => !v)}
        >
          Applied only
        </Button>
      </div>

      <div className="mt-4 space-y-2">
        {isLoading &&
          Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        {(companies ?? []).map((c) => (
          <CompanyRow key={c.id} company={c} />
        ))}
        {companies?.length === 0 && (
          <p className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
            No companies yet.
          </p>
        )}
      </div>
    </div>
  );
}
