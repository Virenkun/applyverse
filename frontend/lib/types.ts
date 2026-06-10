export interface Company {
  id: number;
  name: string;
  website: string | null;
  logo_url: string | null;
  ats_type: string | null;
  glassdoor_rating: number | null;
  notes: string | null;
}

export interface CompanyWithCounts extends Company {
  open_jobs: number;
  applications: number;
}

export interface JobSource {
  source: string;
  url: string | null;
}

export type ApplicationStatus =
  | "saved"
  | "applied"
  | "interviewing"
  | "offer"
  | "rejected";

export interface Application {
  id: number;
  job_id: number;
  status: ApplicationStatus;
  applied_at: string | null;
  resume_version: string | null;
  cover_letter_used: boolean;
  notes: string | null;
  next_followup_at: string | null;
  status_history: { status: string; at: string }[];
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: number;
  title: string;
  company: Company;
  location: string | null;
  work_mode: "remote" | "hybrid" | "onsite" | "unknown";
  salary_min: number | null;
  salary_max: number | null;
  currency: string | null;
  tags: string[] | null;
  canonical_url: string | null;
  posted_at: string | null;
  scraped_at: string;
  is_active: boolean;
  is_hidden: boolean;
  sources: JobSource[];
  application: Application | null;
  description_snippet: string | null;
}

export interface JobDetail extends Job {
  description: string | null;
  description_html: string | null;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApplicationWithJob extends Application {
  job: Job;
}

export interface StatsOverview {
  jobs_new_today: number;
  jobs_active: number;
  applications_total: number;
  applied_this_week: number;
  interviewing: number;
  offers: number;
  response_rate: number | null;
  followups_due: number;
}

export interface TimelinePoint {
  date: string;
  applications: number;
  jobs_scraped: number;
}

export interface ScrapeRun {
  id: number;
  source: string;
  started_at: string;
  finished_at: string | null;
  jobs_found: number;
  jobs_new: number;
  jobs_updated: number;
  status: string;
  error: string | null;
}

export interface SourceSetting {
  source: string;
  enabled: boolean;
  available: boolean;
  last_run: ScrapeRun | null;
}

export interface FilterOptions {
  sources: string[];
  work_modes: string[];
  companies: { id: number; name: string }[];
}

export interface JobFilters {
  q?: string;
  location?: string;
  work_mode?: string;
  source?: string;
  company_id?: number;
  posted_after?: string;
  active?: boolean;
  saved_only?: boolean;
  page?: number;
  page_size?: number;
}
