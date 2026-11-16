import fs from "node:fs";
import path from "node:path";
import { MODULES, REPO_URL } from "@/lib/site";
import TemplateGrid, { type Template } from "./clone/TemplateGrid";

/** Real starter templates from /templates (manifest: templates/templates.json). */
export default function CloneTemplates() {
  const file = path.join(process.cwd(), "..", "..", "templates", "templates.json");
  const raw: Omit<Template, "color" | "ink">[] = JSON.parse(fs.readFileSync(file, "utf8"));
  const items: Template[] = raw.map((t) => {
    const m = MODULES.find((x) => x.key === t.module) ?? MODULES[0];
    return { ...t, color: m.color, ink: m.ink };
  });
  return <TemplateGrid items={items} repo={REPO_URL} />;
}
