import { Sidebar } from "@/components/sidebar";

export default function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="flex min-h-screen w-full">
      <Sidebar />
      <main className="flex min-w-0 flex-1 flex-col bg-background">
        {children}
      </main>
    </div>
  );
}
