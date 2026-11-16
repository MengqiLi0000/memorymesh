"use client";
import { useEffect, useState } from "react";
import { useMesh } from "@/lib/api";

export function SettingsBar() {
  const { settings, setSettings, loaded, call } = useMesh();
  const [draft, setDraft] = useState(settings);
  const [state, setState] = useState<{ tone: "ok" | "bad" | "idle"; msg: string }>({ tone: "idle", msg: "" });
  const [showKey, setShowKey] = useState(false);

  useEffect(() => setDraft(settings), [settings]);

  useEffect(() => {
    if (!loaded) return;
    let live = true;
    call("GET", "/v1/status").then((r) => {
      if (!live) return;
      if (r.ok) setState({ tone: "ok", msg: `${r.data.principal.kind}:${r.data.principal.id} · LLM ${r.data.llm.enabled ? r.data.llm.provider : "off"}` });
      else setState({ tone: "bad", msg: r.status === 0 ? "API unreachable" : `${r.status} ${r.error}` });
    });
    return () => {
      live = false;
    };
  }, [loaded, call]);

  const dirty = draft.baseUrl !== settings.baseUrl || draft.apiKey !== settings.apiKey || draft.userId !== settings.userId;
  const field = "rounded-md border border-line bg-bg px-2 py-1 text-[13px] outline-none focus:border-accent";

  return (
    <div className="sticky top-14 z-20 border-b border-line bg-panel/95 backdrop-blur">
      <form
        className="mx-auto flex max-w-[90rem] flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2 sm:px-6"
        onSubmit={(e) => {
          e.preventDefault();
          setSettings(draft);
        }}
      >
        <label className="flex items-center gap-1.5 text-[12px] text-faint">
          API
          <input className={`${field} mono w-56`} value={draft.baseUrl} onChange={(e) => setDraft({ ...draft, baseUrl: e.target.value })} />
        </label>
        <label className="flex items-center gap-1.5 text-[12px] text-faint">
          Key
          <input
            className={`${field} mono w-48`}
            type={showKey ? "text" : "password"}
            placeholder="owner or agent key"
            value={draft.apiKey}
            onChange={(e) => setDraft({ ...draft, apiKey: e.target.value })}
          />
          <button type="button" className="text-[11px] text-faint hover:text-fg" onClick={() => setShowKey(!showKey)}>
            {showKey ? "hide" : "show"}
          </button>
        </label>
        <label className="flex items-center gap-1.5 text-[12px] text-faint">
          User
          <input className={`${field} mono w-28`} value={draft.userId} onChange={(e) => setDraft({ ...draft, userId: e.target.value })} />
        </label>
        <button
          type="submit"
          disabled={!dirty}
          className="rounded-md bg-accent px-3 py-1 text-[12px] font-medium text-accent-fg disabled:opacity-40"
        >
          Save
        </button>
        <span className={`ml-auto flex items-center gap-1.5 text-[12px] ${state.tone === "ok" ? "text-ok" : state.tone === "bad" ? "text-bad" : "text-faint"}`}>
          <span className={`inline-block h-1.5 w-1.5 rounded-full ${state.tone === "ok" ? "bg-ok" : state.tone === "bad" ? "bg-bad" : "bg-faint"}`} />
          {state.msg || "checking…"}
        </span>
      </form>
    </div>
  );
}
