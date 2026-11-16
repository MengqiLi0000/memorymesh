import { DocsSidebar } from "@/components/DocsSidebar";

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex max-w-7xl gap-10 px-4 sm:px-6">
      <DocsSidebar />
      <main className="min-w-0 flex-1 py-10">
        <article className="prose">{children}</article>
      </main>
    </div>
  );
}
