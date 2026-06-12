"use client";

import Link from "next/link";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlarmClock, GripVertical } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { relativeDate, STATUS_STYLES } from "@/lib/format";
import type { ApplicationStatus, ApplicationWithJob } from "@/lib/types";
import { cn } from "@/lib/utils";

const COLUMNS: { status: ApplicationStatus; label: string }[] = [
  { status: "saved", label: "Saved" },
  { status: "applied", label: "Applied" },
  { status: "interviewing", label: "Interviewing" },
  { status: "offer", label: "Offer" },
  { status: "rejected", label: "Rejected" },
];

function AppCard({
  app,
  overlay = false,
}: {
  app: ApplicationWithJob;
  overlay?: boolean;
}) {
  const followupDue =
    app.next_followup_at && new Date(app.next_followup_at) <= new Date();
  return (
    <div
      className={cn(
        "rounded-md border bg-card p-3 shadow-xs",
        overlay && "rotate-2 shadow-md",
      )}
    >
      <div className="flex items-start gap-1.5">
        <GripVertical className="mt-0.5 size-3.5 shrink-0 text-muted-foreground/50" />
        <div className="min-w-0">
          <Link
            href={`/jobs/${app.job_id}`}
            className="line-clamp-2 text-sm font-medium leading-snug hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            {app.job.title}
          </Link>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {app.job.company.name}
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-1">
            <span className="text-xs text-muted-foreground">
              {app.applied_at
                ? `applied ${relativeDate(app.applied_at)}`
                : `saved ${relativeDate(app.created_at)}`}
            </span>
            {followupDue && (
              <Badge
                variant="outline"
                className="border-amber-200 bg-amber-50 text-amber-700"
              >
                <AlarmClock className="size-3" /> follow up
              </Badge>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function DraggableCard({ app }: { app: ApplicationWithJob }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: app.id,
  });
  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={cn("cursor-grab touch-none", isDragging && "opacity-30")}
    >
      <AppCard app={app} />
    </div>
  );
}

function Column({
  status,
  label,
  apps,
}: {
  status: ApplicationStatus;
  label: string;
  apps: ApplicationWithJob[];
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex min-h-[60vh] w-64 shrink-0 flex-col rounded-lg border bg-muted/40 transition-colors",
        isOver && "border-ring bg-accent",
      )}
    >
      <div className="flex items-center justify-between border-b px-3 py-2.5">
        <span
          className={cn(
            "rounded-md border px-2 py-0.5 text-xs font-medium capitalize",
            STATUS_STYLES[status],
          )}
        >
          {label}
        </span>
        <span className="text-xs text-muted-foreground">{apps.length}</span>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-2">
        {apps.map((app) => (
          <DraggableCard key={app.id} app={app} />
        ))}
        {apps.length === 0 && (
          <p className="m-auto text-xs text-muted-foreground">empty</p>
        )}
      </div>
    </div>
  );
}

export default function TrackerPage() {
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  );

  const { data: apps, isLoading } = useQuery({
    queryKey: ["applications", "all"],
    queryFn: () => api.applications.list(),
  });

  const move = useMutation({
    mutationFn: ({ id, status }: { id: number; status: ApplicationStatus }) =>
      api.applications.update(id, { status }),
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: ["applications", "all"] });
      const prev = queryClient.getQueryData<ApplicationWithJob[]>([
        "applications",
        "all",
      ]);
      queryClient.setQueryData<ApplicationWithJob[]>(
        ["applications", "all"],
        (old) => old?.map((a) => (a.id === id ? { ...a, status } : a)),
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(["applications", "all"], ctx.prev);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  const onDragStart = (e: DragStartEvent) => setActiveId(Number(e.active.id));
  const onDragEnd = (e: DragEndEvent) => {
    setActiveId(null);
    const { active, over } = e;
    if (!over) return;
    const id = Number(active.id);
    const status = over.id as ApplicationStatus;
    const current = apps?.find((a) => a.id === id);
    if (current && current.status !== status) {
      move.mutate({ id, status });
    }
  };

  const activeApp = apps?.find((a) => a.id === activeId);

  return (
    <div className="p-6">
      <h1 className="text-[1.9rem] text-ink">
        Application tracker
      </h1>
      <p className="mt-0.5 text-sm text-muted-foreground">
        Drag cards between columns to update status.
      </p>

      {isLoading ? (
        <div className="mt-4 flex gap-3">
          {COLUMNS.map((c) => (
            <Skeleton key={c.status} className="h-[60vh] w-64" />
          ))}
        </div>
      ) : (
        <DndContext
          sensors={sensors}
          onDragStart={onDragStart}
          onDragEnd={onDragEnd}
        >
          <div className="mt-4 flex gap-3 overflow-x-auto pb-4">
            {COLUMNS.map(({ status, label }) => (
              <Column
                key={status}
                status={status}
                label={label}
                apps={(apps ?? []).filter((a) => a.status === status)}
              />
            ))}
          </div>
          <DragOverlay>
            {activeApp ? <AppCard app={activeApp} overlay /> : null}
          </DragOverlay>
        </DndContext>
      )}
    </div>
  );
}
