import "server-only";
import { codeToHtml } from "shiki";

/** Server-side syntax highlighting (Shiki, github-light). Use in Server Components only. */
export async function highlight(code: string, lang: string): Promise<string> {
  return codeToHtml(code, { lang, theme: "github-light" });
}
