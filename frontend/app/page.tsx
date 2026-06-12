import Link from "next/link";
import {
  ArrowRight,
  Bell,
  Globe2,
  KanbanSquare,
  Radar,
  Rocket,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";

const SOURCES = [
  "Greenhouse",
  "Lever",
  "Ashby",
  "SmartRecruiters",
  "Workable",
  "Recruitee",
  "LinkedIn",
  "Naukri",
  "RemoteOK",
  "WeWorkRemotely",
];

const FEATURES = [
  {
    icon: Radar,
    title: "Keyword-first discovery",
    body: "Tell Applyverse the roles you want — it searches the open web, finds every company hiring for them, and pulls their whole job board automatically.",
  },
  {
    icon: Globe2,
    title: "Ten sources, one feed",
    body: "ATS boards, LinkedIn, Naukri, remote boards — scraped on a schedule, deduplicated, and filtered down to only the roles that match your keywords.",
  },
  {
    icon: KanbanSquare,
    title: "Pipeline you can drag",
    body: "Saved → Applied → Interviewing → Offer. A kanban tracker with notes, resume versions, and follow-up reminders per application.",
  },
  {
    icon: Sparkles,
    title: "Search that understands roles",
    body: "Full-text search plus role and seniority facets — find bare “Software Engineer” postings with no senior/lead noise in one click.",
  },
  {
    icon: Bell,
    title: "Fresh by design",
    body: "Jobs unseen for two scrapes go inactive on their own, so the feed only ever shows postings that still exist.",
  },
  {
    icon: ShieldCheck,
    title: "Yours alone",
    body: "Self-hosted, single-user, password-gated. Your pipeline, notes, and history never leave your machine.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-card">
      {/* Nav */}
      <header className="absolute inset-x-0 top-0 z-10">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <div className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-[0_1px_2px_rgba(0,55,112,0.25)]">
              <Rocket className="size-4" />
            </span>
            <span className="display text-lg text-ink">Applyverse</span>
          </div>
          <Button asChild size="sm">
            <Link href="/login">Sign in</Link>
          </Button>
        </div>
      </header>

      {/* Mesh hero */}
      <section className="mesh">
        <div className="mx-auto max-w-6xl px-6 pb-24 pt-36">
          <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-ink-secondary/80">
            Personal job-hunting infrastructure
          </p>
          <h1 className="display mt-4 max-w-3xl text-[3.5rem] leading-[1.03] text-ink max-md:text-4xl">
            Every job on the internet.
            <br />
            One universe. Yours.
          </h1>
          <p className="mt-5 max-w-xl text-lg font-light leading-relaxed text-ink-secondary">
            Applyverse scrapes ten job sources around the clock, keeps only the
            roles you care about, and tracks every application from saved to
            offer.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button asChild size="lg">
              <Link href="/login">
                Open your universe <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <a href="#features">See how it works</a>
            </Button>
          </div>
        </div>
      </section>

      {/* Source strip */}
      <section className="border-b border-border bg-card">
        <div className="mx-auto max-w-6xl px-6 py-6">
          <div className="flex flex-wrap items-center gap-x-8 gap-y-2">
            <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-ink-mute">
              Pulling from
            </span>
            {SOURCES.map((s) => (
              <span key={s} className="text-sm font-light text-ink-mute">
                {s}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="bg-background">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <h2 className="display max-w-2xl text-[2rem] text-ink">
            Built like infrastructure,
            <br />
            not another job board.
          </h2>
          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <div
                key={title}
                className="rounded-xl border border-border bg-card p-8 shadow-[0_1px_3px_rgba(0,55,112,0.08)]"
              >
                <span className="flex size-9 items-center justify-center rounded-lg bg-brand-wash">
                  <Icon className="size-4.5 text-brand" />
                </span>
                <h3 className="mt-5 text-lg text-ink">{title}</h3>
                <p className="mt-2 text-sm font-light leading-relaxed text-ink-mute">
                  {body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Dark band */}
      <section className="bg-navy-900">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <div className="grid items-center gap-10 lg:grid-cols-2">
            <div>
              <h2 className="display text-[2rem] text-white">
                The numbers do the hunting.
              </h2>
              <p className="mt-3 max-w-md text-sm font-light leading-relaxed text-white/70">
                Scrapers run every few hours. Discovery finds new company
                boards daily from your keywords. You just open the feed and
                apply.
              </p>
              <Button asChild size="lg" className="mt-8">
                <Link href="/login">
                  Start tracking <ArrowRight className="size-4" />
                </Link>
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                ["10", "sources scraped"],
                ["8,000+", "live jobs indexed"],
                ["400+", "companies discovered"],
                ["4–6h", "refresh cycle"],
              ].map(([n, label]) => (
                <div
                  key={label}
                  className="rounded-xl border border-white/10 bg-white/5 p-6"
                >
                  <div className="tnum text-3xl font-light text-white">{n}</div>
                  <div className="mt-1 text-xs uppercase tracking-wide text-white/60">
                    {label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Cream interlude */}
      <section className="bg-card">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <div className="rounded-xl bg-cream p-12 text-center">
            <h2 className="display text-[2rem] text-ink">
              Stop refreshing job boards.
            </h2>
            <p className="mx-auto mt-3 max-w-md text-sm font-light text-ink-secondary">
              Let Applyverse refresh them for you — and only show the ones
              worth your time.
            </p>
            <Button asChild size="lg" className="mt-7">
              <Link href="/login">
                Open the dashboard <ArrowRight className="size-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-card">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-10">
          <div className="flex items-center gap-2">
            <span className="flex size-6 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Rocket className="size-3" />
            </span>
            <span className="text-sm text-ink-mute">
              Applyverse — self-hosted job hunting
            </span>
          </div>
          <span className="text-xs text-ink-mute">
            Runs entirely on your machine.
          </span>
        </div>
      </footer>
    </div>
  );
}
