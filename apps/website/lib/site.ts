export const REPO_URL = process.env.NEXT_PUBLIC_REPO_URL ?? "https://github.com/MengqiLi0000/memorymesh";
export const DEMO_API = process.env.NEXT_PUBLIC_DEMO_API ?? "http://127.0.0.1:8765";

export const NAV = [
  { href: "/", label: "Overview" },
  { href: "/playground", label: "Playground" },
  { href: "/memory", label: "Memory" },
  { href: "/graph", label: "Graph" },
  { href: "/human-model", label: "Human Model" },
  { href: "/semantic-arena", label: "Semantic Arena" },
  { href: "/benchmarks", label: "Benchmarks" },
  { href: "/docs", label: "Docs" },
];

/** Module catalogue. Colors = Monopoly property groups (title-deed bands). `ink` = readable text on the color. */
export const MODULES = [
  { key: "memory", label: "Memory", href: "/memory", color: "var(--mono-darkblue)", ink: "#fff", desc: "Store and search what users say" },
  { key: "graph", label: "Temporal Graph", href: "/graph", color: "var(--mono-green)", ink: "#fff", desc: "Facts with valid-from / valid-to" },
  { key: "human", label: "Human Model", href: "/human-model", color: "var(--mono-red)", ink: "#fff", desc: "Observed and inferred user traits" },
  { key: "mind", label: "Theory of Mind", href: "/human-model#mind", color: "var(--mono-orange)", ink: "#111", desc: "Intent and knowledge hypotheses" },
  { key: "semantic", label: "Semantic Arena", href: "/semantic-arena", color: "var(--mono-pink)", ink: "#fff", desc: "Learn what a user means by a word" },
  { key: "context", label: "Context Engine", href: "/playground#context", color: "var(--mono-lightblue)", ink: "#111", desc: "Budgeted context with a trace" },
  { key: "agents", label: "Cross-Agent", href: "/playground", color: "var(--mono-brown)", ink: "#fff", desc: "Grants, scopes, revocation" },
  { key: "persona", label: "Persona Lab", href: "/docs/persona-lab", color: "var(--mono-yellow)", ink: "#111", desc: "Activation vectors (experimental)" },
] as const;

export const DEV_TOOLS = [
  { label: "Python SDK", href: "/docs/python-sdk" },
  { label: "TypeScript SDK", href: "/docs/typescript-sdk" },
  { label: "REST API", href: "/docs/rest-api" },
  { label: "MCP server", href: "/docs/mcp" },
  { label: "Local deployment", href: "/docs/local-deployment" },
] as const;
