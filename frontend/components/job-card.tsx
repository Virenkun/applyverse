"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Bookmark,
  BookmarkCheck,
  ExternalLink,
  Send,
  ThumbsDown,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import {
  relativeDate,
  salaryRange,
  STATUS_STYLES,
  TAG_STYLE,
  WORK_MODE_STYLES,
} from "@/lib/format";
import type { Job } from "@/lib/types";
import { cn } from "@/lib/utils";

export function JobCard({ job }: { job: Job }) {
  const queryClient = useQueryClient();
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["jobs"] });
    queryClient.invalidateQueries({ queryKey: ["applications"] });
    queryClient.invalidateQueries({ queryKey: ["stats"] });
  };

  const save = useMutation({
    mutationFn: () => api.applications.create(job.id, "saved"),
    onSuccess: invalidate,
  });
  const markApplied = useMutation({
    mutationFn: () =>
      job.application
        ? api.applications.update(job.application.id, { status: "applied" })
        : api.applications.create(job.id, "applied"),
    onSuccess: invalidate,
  });
  const hide = useMutation({
    mutationFn: () => api.jobs.hide(job.id),
    onSuccess: invalidate,
  });

  const salary = salaryRange(job.salary_min, job.salary_max, job.currency);
  const status = job.application?.status;

  return (
    <div className="group rounded-lg border bg-card p-4 transition-shadow hover:shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <Link
            href={`/jobs/${job.id}`}
            className="line-clamp-1 font-medium hover:underline"
          >
            {job.title}
          </Link>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm text-muted-foreground">
            <span className="font-medium text-foreground/80">
              {job.company.name}
            </span>
            {job.location && (
              <>
                <span>·</span>
                <span className="line-clamp-1">{job.location}</span>
              </>
            )}
            <span>·</span>
            <span>{relativeDate(job.posted_at ?? job.scraped_at)}</span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {status !== undefined && (
            <Badge
              variant="outline"
              className={cn("capitalize", STATUS_STYLES[status])}
            >
              {status}
            </Badge>
          )}
          {job.canonical_url && (
            <Button asChild size="sm">
              <a href={job.canonical_url} target="_blank" rel="noreferrer">
                Apply <ExternalLink className="size-3.5" />
              </a>
            </Button>
          )}
        </div>
      </div>

      {job.description_snippet && (
        <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">
          {job.description_snippet}
        </p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <Badge
          variant="outline"
          className={cn("capitalize", WORK_MODE_STYLES[job.work_mode])}
        >
          {job.work_mode}
        </Badge>
        {salary && (
          <Badge variant="outline" className="tnum">
            {salary}
          </Badge>
        )}
        {(job.tags ?? []).slice(0, 4).map((tag) => (
          <Badge key={tag} variant="outline" className={TAG_STYLE}>
            {tag}
          </Badge>
        ))}
        <span className="ml-auto flex items-center gap-1.5">
          {status === undefined && (
            <>
              <Button
                variant="ghost"
                size="sm"
                className="text-ink-mute hover:text-ruby"
                disabled={hide.isPending}
                onClick={() => hide.mutate()}
              >
                <ThumbsDown className="size-3.5" /> Not interested
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={save.isPending}
                onClick={() => save.mutate()}
              >
                <Bookmark className="size-3.5" /> Save
              </Button>
            </>
          )}
          {status === undefined || status === "saved" ? (
            <Button
              variant="outline"
              size="sm"
              disabled={markApplied.isPending}
              onClick={() => markApplied.mutate()}
            >
              {status === "saved" ? (
                <BookmarkCheck className="size-3.5" />
              ) : (
                <Send className="size-3.5" />
              )}
              Mark applied
            </Button>
          ) : null}
        </span>
      </div>
    </div>
  );
}
