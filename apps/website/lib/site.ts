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
