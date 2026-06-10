"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, PlayCircle, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { relativeDate } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [triggered, setTriggered] = useState<string | null>(null);

  const sources = useQuery({
    queryKey: ["settings", "sources"],
    queryFn: api.settings.sources,
  });
  const runs = useQuery({
    queryKey: ["scrape", "runs"],
    queryFn: () => api.scrape.runs(15),
    refetchInterval: 10_000,
  });

  const toggle = useMutation({
    mutationFn: ({ source, enabled }: { source: string; enabled: boolean }) =>
      api.settings.updateSource(source, enabled),
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: ["settings", "sources"] }),
  });

  const trigger = useMutation({
    mutationFn: (source?: string) => api.scrape.trigger(source),
    onSuccess: (_d, source) => {
      setTriggered(source ?? "all sources");
      setTimeout(() => setTriggered(null), 5000);
      setTimeout(
        () => queryClient.invalidateQueries({ queryKey: ["scrape", "runs"] }),
        2000,
      );
    },
  });

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
        <Button disabled={trigger.isPending} onClick={() => trigger.mutate(undefined)}>
          <PlayCircle className="size-4" /> Scrape all now
        </Button>
      </div>
      {triggered && (
        <p className="mt-2 text-sm text-emerald-600">
          Scrape of {triggered} started — runs appear below as they finish.
        </p>
      )}

      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-base">Sources</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {sources.isLoading && <Skeleton className="h-40" />}
          {(sources.data ?? []).map((s) => (
            <div
              key={s.source}
              className="flex flex-wrap items-center gap-2 rounded-md px-2 py-2 hover:bg-muted/50"
            >
              <span className="w-36 text-sm font-medium capitalize">{s.source}</span>
              {!s.available && (
                <Badge variant="outline" className="font-normal text-muted-foreground">
                  needs ENABLE_{s.source.toUpperCase()}=true
                </Badge>
              )}
              {s.last_run && (
                <span className="text-xs text-muted-foreground">
                  last run {relativeDate(s.last_run.started_at)} ·{" "}
                  {s.last_run.status === "ok"
                    ? `${s.last_run.jobs_found} jobs (${s.last_run.jobs_new} new)`
                    : s.last_run.status}
                </span>
              )}
              <span className="ml-auto flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={!s.available || !s.enabled || trigger.isPending}
                  onClick={() => trigger.mutate(s.source)}
                  title="Run this source now"
                >
                  <PlayCircle className="size-4" />
                </Button>
                <Button
                  variant={s.enabled ? "default" : "outline"}
                  size="sm"
                  className="w-16"
                  disabled={toggle.isPending}
                  onClick={() =>
                    toggle.mutate({ source: s.source, enabled: !s.enabled })
                  }
                >
                  {s.enabled ? "On" : "Off"}
                </Button>
              </span>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Recent scrape runs</CardTitle>
        </CardHeader>
        <CardContent>
          {runs.isLoading && <Skeleton className="h-32" />}
          <div className="space-y-1.5">
            {(runs.data ?? []).map((r) => (
              <div key={r.id} className="flex items-center gap-2 text-sm">
                {r.status === "ok" ? (
                  <CheckCircle2 className="size-4 text-emerald-600" />
                ) : r.status === "error" ? (
                  <XCircle className="size-4 text-red-500" />
                ) : (
                  <Loader2 className="size-4 animate-spin text-muted-foreground" />
                )}
                <span className="w-36 capitalize">{r.source}</span>
                <span className="text-muted-foreground">
                  {relativeDate(r.started_at)}
                </span>
                <span
                  className={cn(
                    "ml-auto text-muted-foreground",
                    r.status === "error" && "max-w-64 truncate text-red-500",
                  )}
                  title={r.error ?? undefined}
                >
                  {r.status === "ok"
                    ? `${r.jobs_found} found · ${r.jobs_new} new · ${r.jobs_updated} updated`
                    : r.status === "error"
                      ? r.error
                      : "running…"}
                </span>
              </div>
            ))}
            {runs.isSuccess && runs.data.length === 0 && (
              <p className="text-sm text-muted-foreground">No runs yet.</p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Target companies</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          ATS scrapers poll the companies in{" "}
          <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
            backend/companies.yaml
          </code>
          . Add an entry with the company&apos;s ATS (greenhouse, lever, ashby,
          smartrecruiters, recruitee, workable) and board slug, then run{" "}
          <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
            python -m app.seed
          </code>{" "}
          and trigger a scrape.
        </CardContent>
      </Card>
    </div>
  );
}
