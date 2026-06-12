"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlarmClock,
  ArrowRight,
  Briefcase,
  CalendarCheck,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { JobCard } from "@/components/job-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

function StatCard({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  hint?: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Card className="gap-2 py-4">
      <CardHeader className="flex flex-row items-center justify-between px-5">
        <CardTitle className="text-xs font-medium uppercase tracking-wide text-ink-mute">
          {label}
        </CardTitle>
        <Icon className="size-4 text-brand" />
      </CardHeader>
      <CardContent className="px-5">
        <div className="tnum text-[2rem] font-light leading-none text-ink">
          {value}
        </div>
        {hint && <p className="mt-1.5 text-xs text-ink-mute">{hint}</p>}
      </CardContent>
    </Card>
  );
}

export default function OverviewPage() {
  const stats = useQuery({ queryKey: ["stats", "overview"], queryFn: api.stats.overview });
  const timeline = useQuery({
    queryKey: ["stats", "timeline"],
    queryFn: () => api.stats.timeline(30),
  });
  const recentJobs = useQuery({
    queryKey: ["jobs", "recent"],
    queryFn: () => api.jobs.list({ page_size: 5 }),
  });

  const s = stats.data;

  return (
    <div>
      <div className="mesh border-b border-border">
        <div className="mx-auto max-w-5xl px-6 pb-16 pt-10">
          <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-ink-secondary/70">
            Dashboard
          </p>
          <h1 className="mt-1 text-[2.5rem] text-ink">Overview</h1>
          <p className="mt-1 text-sm text-ink-secondary">
            Your job pipeline at a glance.
          </p>
        </div>
      </div>

      <div className="mx-auto -mt-10 max-w-5xl px-6 pb-10">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {s ? (
          <>
            <StatCard
              label="New jobs today"
              value={s.jobs_new_today.toLocaleString()}
              hint={`${s.jobs_active.toLocaleString()} active total`}
              icon={Sparkles}
            />
            <StatCard
              label="Applied this week"
              value={s.applied_this_week}
              hint={`${s.applications_total} tracked total`}
              icon={CalendarCheck}
            />
            <StatCard
              label="Interviewing"
              value={s.interviewing}
              hint={`${s.offers} offer${s.offers === 1 ? "" : "s"}`}
              icon={MessageSquare}
            />
            <StatCard
              label="Response rate"
              value={s.response_rate !== null ? `${Math.round(s.response_rate * 100)}%` : "—"}
              hint={
                s.followups_due > 0
                  ? `${s.followups_due} follow-up${s.followups_due === 1 ? "" : "s"} due`
                  : "no follow-ups due"
              }
              icon={AlarmClock}
            />
          </>
        ) : (
          Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))
        )}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Jobs scraped — last 30 days</CardTitle>
          </CardHeader>
          <CardContent>
            {timeline.data ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={timeline.data}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(d: string) => d.slice(5)}
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis fontSize={11} tickLine={false} axisLine={false} width={40} />
                  <Tooltip />
                  <Bar dataKey="jobs_scraped" name="jobs" fill="var(--chart-2)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Skeleton className="h-55" />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Applications — last 30 days</CardTitle>
          </CardHeader>
          <CardContent>
            {timeline.data ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={timeline.data}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(d: string) => d.slice(5)}
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis fontSize={11} tickLine={false} axisLine={false} width={40} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="applications" fill="var(--chart-1)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Skeleton className="h-55" />
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-medium">Latest jobs</h2>
          <Link
            href="/jobs"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            All jobs <ArrowRight className="size-3.5" />
          </Link>
        </div>
        <div className="space-y-3">
          {recentJobs.data ? (
            recentJobs.data.items.map((job) => <JobCard key={job.id} job={job} />)
          ) : (
            <Skeleton className="h-32" />
          )}
          {recentJobs.data?.items.length === 0 && (
            <Card>
              <CardContent className="py-10 text-center text-sm text-muted-foreground">
                <Briefcase className="mx-auto mb-2 size-6" />
                No jobs yet — trigger a scrape from Settings.
              </CardContent>
            </Card>
          )}
        </div>
      </div>
      </div>
    </div>
  );
}
