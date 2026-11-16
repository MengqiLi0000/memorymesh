"use client";
import { useEffect, useState } from "react";

type Mode = "system" | "light" | "dark";

export function ThemeToggle() {
  const [mode, setMode] = useState<Mode>("system");
  useEffect(() => {
    try {
      const t = localStorage.getItem("mm-theme");
      if (t === "light" || t === "dark") setMode(t);
    } catch {}
  }, []);
  const cycle = () => {
    const next: Mode = mode === "system" ? "light" : mode === "light" ? "dark" : "system";
    setMode(next);
    const el = document.documentElement;
    if (next === "system") el.removeAttribute("data-theme");
    else el.setAttribute("data-theme", next);
    try {
      if (next === "system") localStorage.removeItem("mm-theme");
      else localStorage.setItem("mm-theme", next);
    } catch {}
  };
  return (
    <button
      onClick={cycle}
      className="rounded-md border border-line px-2.5 py-1 text-xs text-muted hover:text-fg"
      title="Theme: system, light, dark"
    >
      Theme: {mode}
    </button>
  );
}
