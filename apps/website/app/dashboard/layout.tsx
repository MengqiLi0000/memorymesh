import { SettingsProvider } from "@/lib/api";
import { DashNav } from "@/components/DashNav";
import { SettingsBar } from "@/components/SettingsBar";

export const metadata = { title: "Dashboard" };

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <SettingsProvider>
      <SettingsBar />
      <div className="mx-auto flex max-w-[90rem] flex-col gap-6 px-4 py-6 sm:px-6 md:flex-row">
        <DashNav />
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </SettingsProvider>
  );
}
