"use client";
import { useEffect, useState } from "react";
import { useMesh, type ApiResult } from "@/lib/api";
import { Badge, Button, Empty, ErrorBox, Input, PageHead, fmtTime } from "@/components/ui";

export default function AuditPage() {
  const { call, loaded, settings } = useMesh();
  const [res, setRes] = useState<ApiResult<any[]> | null>(null);
  const [onlyUser, setOnlyUser] = useState(true);
  const [limit, setLimit] = useState(200);
  const [filter, setFilter] = useState("");
  const load = async () => setRes(await call("GET", "/v1/audit", { query: { user_id: onlyUser ? settings.userId : undefined, limit } }));
  useEffect(() => {
    if (loaded) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, call, settings.userId, onlyUser]);

  const rows = (res?.ok ? res.data : []).filter((r) => !filter || JSON.stringify(r).toLowerCase().includes(filter.toLowerCase()));
  return (
    <>
      <PageHead title="Audit Log" desc={<>Every authorization decision, allowed or denied. Owner key required. <code className="mono">GET /v1/audit</code></>}>
        <label className="flex items-center gap-1.5 text-[13px] text-muted">
          <input type="checkbox" checked={onlyUser} onChange={(e) => setOnlyUser(e.target.checked)} /> only {settings.userId}
        </label>
        <Input className="!w-20" type="number" value={limit} onChange={(e) => setLimit(Number(e.target.value))} />
        <Input className="!w-48" placeholder="filter" value={filter} onChange={(e) => setFilter(e.target.value)} />
        <Button onClick={load}>Refresh</Button>
      </PageHead>
      <ErrorBox res={res} />
      {res?.ok && rows.length === 0 && <Empty>No audit entries.</Empty>}
      {rows.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-line bg-panel">
          <table className="w-full text-[13px]">
            <thead className="border-b border-line text-left text-[11px] uppercase tracking-wider text-faint">
              <tr>
                <th className="px-3 py-2">Time</th><th className="px-3 py-2">Actor</th><th className="px-3 py-2">User</th>
                <th className="px-3 py-2">Action</th><th className="px-3 py-2">Result</th><th className="px-3 py-2">Resource / detail</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-line last:border-0 align-top">
                  <td className="whitespace-nowrap px-3 py-1.5 text-muted">{fmtTime(r.ts)}</td>
                  <td className="mono px-3 py-1.5 text-[12px]">{r.actor}</td>
                  <td className="mono px-3 py-1.5 text-[12px]">{r.user_id}</td>
                  <td className="mono px-3 py-1.5 text-[12px]">{r.action}</td>
                  <td className="px-3 py-1.5">{r.allowed ? <Badge tone="ok">allowed</Badge> : <Badge tone="bad">denied</Badge>}</td>
                  <td className="px-3 py-1.5 text-[12px] text-muted">
                    <div className="max-w-md truncate">{r.resource}</div>
                    {r.detail && Object.keys(r.detail).length > 0 && <div className="mono max-w-md truncate text-faint">{JSON.stringify(r.detail)}</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
