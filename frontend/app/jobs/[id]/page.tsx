"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import DOMPurify from "isomorphic-dompurify";
import { ArrowLeft, ExternalLink, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { relativeDate, salaryRange, STATUS_STYLES, WORK_MODE_STYLES } from "@/lib/format";
import type { ApplicationStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUSES: ApplicationStatus[] = [
  "saved",
  "applied",
  "interviewing",
  "offer",
  "rejected",
];

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const jobId = Number(id);
  const queryClient = useQueryClient();

  const { data: job, isLoading } = useQuery({
    queryKey: ["jobs", "detail", jobId],
    queryFn: () => api.jobs.get(jobId),
  });

  const application = job?.application ?? null;
  const [notes, setNotes] = useState("");
  const [resumeVersion, setResumeVersion] = useState("");
  const [followup, setFollowup] = useState("");

  useEffect(() => {
    setNotes(application?.notes ?? "");
    setResumeVersion(application?.resume_version ?? "");
    setFollowup(
      application?.next_followup_at
        ? application.next_followup_at.slice(0, 10)
        : "",
    );
  }, [application?.id, application?.notes, application?.resume_version, application?.next_followup_at]);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["jobs"] });
    queryClient.invalidateQueries({ queryKey: ["applications"] });
    queryClient.invalidateQueries({ queryKey: ["stats"] });
  };

  const createApp = useMutation({
    mutationFn: (status: ApplicationStatus) =>
      api.applications.create(jobId, status),
    onSuccess: invalidate,
  });
  const updateApp = useMutation({
    mutationFn: (patch: Parameters<typeof api.applications.update>[1]) =>
      api.applications.update(application!.id, patch),
    onSuccess: invalidate,
  });
  const deleteApp = useMutation({
    mutationFn: () => api.applications.remove(application!.id),
    onSuccess: invalidate,
  });

  if (isLoading || !job) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-6">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  const salary = salaryRange(job.salary_min, job.salary_max, job.currency);

  return (
    <div className="mx-auto max-w-5xl p-6">
      <Link
        href="/jobs"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> Back to jobs
      </Link>

      <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{job.title}</h1>
          <p className="mt-1 text-muted-foreground">
            {job.company.name}
            {job.location ? ` · ${job.location}` : ""} · posted{" "}
            {relativeDate(job.posted_at ?? job.scraped_at)}
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <Badge
              variant="outline"
              className={cn("capitalize", WORK_MODE_STYLES[job.work_mode])}
            >
              {job.work_mode}
            </Badge>
            {salary && <Badge variant="outline">{salary}</Badge>}
            {!job.is_active && <Badge variant="destructive">inactive</Badge>}
            {(job.tags ?? []).map((t) => (
              <Badge key={t} variant="secondary" className="font-normal">
                {t}
              </Badge>
            ))}
          </div>
        </div>
        {job.canonical_url && (
          <Button asChild>
            <a href={job.canonical_url} target="_blank" rel="noreferrer">
              Apply on {job.sources[0]?.source ?? "source"}{" "}
              <ExternalLink className="size-4" />
            </a>
          </Button>
        )}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_320px]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Job description</CardTitle>
          </CardHeader>
          <CardContent>
            {job.description_html ? (
              <div
                className="job-description text-foreground/90"
                dangerouslySetInnerHTML={{
                  __html: DOMPurify.sanitize(job.description_html),
                }}
              />
            ) : job.description ? (
              <p className="job-description whitespace-pre-wrap">{job.description}</p>
            ) : (
              <p className="text-sm text-muted-foreground">
                No description scraped — open the original posting.
              </p>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Application</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {application === null ? (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    className="flex-1"
                    disabled={createApp.isPending}
                    onClick={() => createApp.mutate("saved")}
                  >
                    Save
                  </Button>
                  <Button
                    className="flex-1"
                    disabled={createApp.isPending}
                    onClick={() => createApp.mutate("applied")}
                  >
                    Mark applied
                  </Button>
                </div>
              ) : (
                <>
                  <div className="space-y-1.5">
                    <Label>Status</Label>
                    <Select
                      value={application.status}
                      onValueChange={(v) =>
                        updateApp.mutate({ status: v as ApplicationStatus })
                      }
                    >
                      <SelectTrigger className="w-full capitalize">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {STATUSES.map((s) => (
                          <SelectItem key={s} value={s} className="capitalize">
                            {s}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label>Resume version</Label>
                    <Input
                      value={resumeVersion}
                      onChange={(e) => setResumeVersion(e.target.value)}
                      onBlur={() =>
                        updateApp.mutate({ resume_version: resumeVersion })
                      }
                      placeholder="e.g. backend-v3.pdf"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Next follow-up</Label>
                    <Input
                      type="date"
                      value={followup}
                      onChange={(e) => {
                        setFollowup(e.target.value);
                        updateApp.mutate({
                          next_followup_at: e.target.value
                            ? new Date(e.target.value).toISOString()
                            : null,
                        });
                      }}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Notes</Label>
                    <Textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      onBlur={() => updateApp.mutate({ notes })}
                      placeholder="Referral, recruiter name, interview prep…"
                      rows={4}
                    />
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full text-destructive hover:text-destructive"
                    disabled={deleteApp.isPending}
                    onClick={() => deleteApp.mutate()}
                  >
                    <Trash2 className="size-3.5" /> Remove from tracker
                  </Button>
                </>
              )}
            </CardContent>
          </Card>

          {application && application.status_history.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="space-y-2">
                  {[...application.status_history].reverse().map((h, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm">
                      <Badge
                        variant="outline"
                        className={cn("capitalize", STATUS_STYLES[h.status])}
                      >
                        {h.status}
                      </Badge>
                      <span className="text-muted-foreground">
                        {relativeDate(h.at)}
                      </span>
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Sources</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {job.sources.map((s) => (
                <div key={s.source} className="flex items-center justify-between text-sm">
                  <span className="capitalize">{s.source}</span>
                  {s.url && (
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-blue-600 hover:underline"
                    >
                      open <ExternalLink className="size-3" />
                    </a>
                  )}
                </div>
              ))}
              <p className="pt-1 text-xs text-muted-foreground">
                Last seen {relativeDate(job.scraped_at)}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
