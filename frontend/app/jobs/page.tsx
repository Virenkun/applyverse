"use client";

import { useMemo, useState } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { Loader2, Search, X } from "lucide-react";

import { JobCard } from "@/components/job-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { JobFilters } from "@/lib/types";

const PAGE_SIZE = 25;
const ANY = "__any__";

export default function JobsPage() {
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [workMode, setWorkMode] = useState(ANY);
  const [source, setSource] = useState(ANY);
  const [companyId, setCompanyId] = useState(ANY);
  const [postedDays, setPostedDays] = useState(ANY);

  const filters: JobFilters = useMemo(() => {
    const f: JobFilters = { page_size: PAGE_SIZE };
    if (q) f.q = q;
    if (workMode !== ANY) f.work_mode = workMode;
    if (source !== ANY) f.source = source;
    if (companyId !== ANY) f.company_id = Number(companyId);
    if (postedDays !== ANY) {
      const d = new Date();
      d.setDate(d.getDate() - Number(postedDays));
      f.posted_after = d.toISOString();
    }
    return f;
  }, [q, workMode, source, companyId, postedDays]);

  const filterOptions = useQuery({
    queryKey: ["jobs", "filter-options"],
    queryFn: api.jobs.filters,
  });

  const jobsQuery = useInfiniteQuery({
    queryKey: ["jobs", "list", filters],
    queryFn: ({ pageParam }) => api.jobs.list({ ...filters, page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (last) =>
      last.page * last.page_size < last.total ? last.page + 1 : undefined,
  });

  const jobs = jobsQuery.data?.pages.flatMap((p) => p.items) ?? [];
  const total = jobsQuery.data?.pages[0]?.total;
  const hasActiveFilters =
    q || workMode !== ANY || source !== ANY || companyId !== ANY || postedDays !== ANY;

  const clearFilters = () => {
    setSearch("");
    setQ("");
    setWorkMode(ANY);
    setSource(ANY);
    setCompanyId(ANY);
    setPostedDays(ANY);
  };

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-3 flex items-baseline justify-between">
        <h1 className="text-[1.9rem] text-ink">Jobs</h1>
        {total !== undefined && (
          <span className="tnum text-sm text-ink-mute">
            {total.toLocaleString()} jobs
          </span>
        )}
      </div>

      <form
        className="mt-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          setQ(search);
        }}
      >
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search title, description, tech stack…"
            className="bg-card pl-8"
          />
        </div>
        <Button type="submit">Search</Button>
      </form>

      <div className="mt-2 flex flex-wrap gap-2">
        <Select value={workMode} onValueChange={setWorkMode}>
          <SelectTrigger size="sm" className="bg-card">
            <SelectValue placeholder="Work mode" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ANY}>Any mode</SelectItem>
            {(filterOptions.data?.work_modes ?? []).map((m) => (
              <SelectItem key={m} value={m} className="capitalize">
                {m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={source} onValueChange={setSource}>
          <SelectTrigger size="sm" className="bg-card">
            <SelectValue placeholder="Source" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ANY}>Any source</SelectItem>
            {(filterOptions.data?.sources ?? []).map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={companyId} onValueChange={setCompanyId}>
          <SelectTrigger size="sm" className="max-w-44 bg-card">
            <SelectValue placeholder="Company" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ANY}>Any company</SelectItem>
            {(filterOptions.data?.companies ?? []).map((c) => (
              <SelectItem key={c.id} value={String(c.id)}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={postedDays} onValueChange={setPostedDays}>
          <SelectTrigger size="sm" className="bg-card">
            <SelectValue placeholder="Posted" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ANY}>Any time</SelectItem>
            <SelectItem value="1">Last 24h</SelectItem>
            <SelectItem value="7">Last week</SelectItem>
            <SelectItem value="30">Last month</SelectItem>
          </SelectContent>
        </Select>

        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            <X className="size-3.5" /> Clear
          </Button>
        )}
      </div>

      <div className="mt-4 space-y-3">
        {jobsQuery.isLoading &&
          Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-lg" />
          ))}
        {jobsQuery.isError && (
          <p className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            Failed to load jobs — is the API running? ({String(jobsQuery.error)})
          </p>
        )}
        {jobs.map((job) => (
          <JobCard key={job.id} job={job} />
        ))}
        {jobsQuery.isSuccess && jobs.length === 0 && (
          <p className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
            No jobs match these filters.
          </p>
        )}
      </div>

      {jobsQuery.hasNextPage && (
        <div className="mt-4 flex justify-center">
          <Button
            variant="outline"
            disabled={jobsQuery.isFetchingNextPage}
            onClick={() => jobsQuery.fetchNextPage()}
          >
            {jobsQuery.isFetchingNextPage && (
              <Loader2 className="size-4 animate-spin" />
            )}
            Load more
          </Button>
        </div>
      )}
    </div>
  );
}
