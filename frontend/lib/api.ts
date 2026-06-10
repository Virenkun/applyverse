import type {
  Application,
  ApplicationStatus,
  ApplicationWithJob,
  CompanyWithCounts,
  FilterOptions,
  Job,
  JobDetail,
  JobFilters,
  JobListResponse,
  ScrapeRun,
  SourceSetting,
  StatsOverview,
  TimelinePoint,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function qs(params: Record<string, unknown>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const s = search.toString();
  return s ? `?${s}` : "";
}

export const api = {
  jobs: {
    list: (filters: JobFilters = {}) =>
      request<JobListResponse>(`/jobs${qs({ ...filters })}`),
    get: (id: number) => request<JobDetail>(`/jobs/${id}`),
    filters: () => request<FilterOptions>(`/jobs/filters`),
    hide: (id: number) => request<Job>(`/jobs/${id}/hide`, { method: "POST" }),
    unhide: (id: number) =>
      request<Job>(`/jobs/${id}/unhide`, { method: "POST" }),
  },
  applications: {
    list: (status?: ApplicationStatus) =>
      request<ApplicationWithJob[]>(`/applications${qs({ status })}`),
    create: (job_id: number, status: ApplicationStatus = "saved") =>
      request<ApplicationWithJob>(`/applications`, {
        method: "POST",
        body: JSON.stringify({ job_id, status }),
      }),
    update: (id: number, patch: Partial<Application>) =>
      request<ApplicationWithJob>(`/applications/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    remove: (id: number) =>
      request<void>(`/applications/${id}`, { method: "DELETE" }),
  },
  companies: {
    list: (appliedOnly = false) =>
      request<CompanyWithCounts[]>(
        `/companies${qs({ applied_only: appliedOnly })}`,
      ),
    jobs: (id: number) => request<Job[]>(`/companies/${id}/jobs`),
  },
  stats: {
    overview: () => request<StatsOverview>(`/stats/overview`),
    timeline: (days = 30) =>
      request<TimelinePoint[]>(`/stats/timeline${qs({ days })}`),
  },
  settings: {
    sources: () => request<SourceSetting[]>(`/settings/sources`),
    updateSource: (source: string, enabled: boolean) =>
      request<SourceSetting>(`/settings/sources/${source}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      }),
  },
  scrape: {
    trigger: (source?: string) =>
      request<{ started: string | string[] }>(`/scrape/trigger${qs({ source })}`, {
        method: "POST",
      }),
    runs: (limit = 20) => request<ScrapeRun[]>(`/scrape/runs${qs({ limit })}`),
  },
};
