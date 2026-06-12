"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, Lock, Rocket } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPending(true);
    setError(null);
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password }),
    }).catch(() => null);
    if (res?.ok) {
      router.push("/dashboard");
      router.refresh();
      return;
    }
    setError(res ? "Wrong password — try again." : "Network error.");
    setPending(false);
  };

  return (
    <div className="mesh flex min-h-screen flex-col">
      <header className="mx-auto flex h-16 w-full max-w-6xl items-center px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-[0_1px_2px_rgba(0,55,112,0.25)]">
            <Rocket className="size-4" />
          </span>
          <span className="display text-lg text-ink">Applyverse</span>
        </Link>
      </header>

      <div className="flex flex-1 items-start justify-center px-6 pb-24 pt-16">
        <div className="w-full max-w-sm rounded-xl border border-border bg-card p-8 shadow-[0_8px_24px_rgba(0,55,112,0.08),0_2px_6px_rgba(0,55,112,0.04)]">
          <h1 className="display text-2xl text-ink">Welcome back</h1>
          <p className="mt-1 text-sm font-light text-ink-mute">
            Enter your access password to open the dashboard.
          </p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  autoFocus
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="pl-8"
                />
              </div>
            </div>
            {error && <p className="text-sm text-ruby">{error}</p>}
            <Button type="submit" className="w-full" disabled={pending || !password}>
              {pending && <Loader2 className="size-4 animate-spin" />}
              Sign in
            </Button>
          </form>

          <p className="mt-5 text-xs font-light text-ink-mute">
            Self-hosted instance — the password is set with{" "}
            <code className="rounded bg-muted px-1 py-0.5">
              APPLYVERSE_PASSWORD
            </code>{" "}
            in your .env.
          </p>
        </div>
      </div>
    </div>
  );
}
