import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AuditLogOut, Page } from "@/lib/types";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { PageSpinner, EmptyState } from "@/components/ui/Misc";
import { SortHeader, toggleSort, type SortState } from "@/components/ui/SortHeader";
import { formatDateTime } from "@/lib/utils";

const PAGE_SIZE = 50;

type SortKey = "created_at" | "actor_label" | "action" | "target_type";

export function AuditLogPage() {
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<SortState<SortKey>>({ key: "created_at", dir: "desc" });

  const { data, isLoading } = useQuery({
    queryKey: ["audit-log", page, sort.key, sort.dir],
    queryFn: () =>
      api.get<Page<AuditLogOut>>(
        `/audit?page=${page}&page_size=${PAGE_SIZE}&sort_by=${sort.key}&sort_dir=${sort.dir}`
      ),
  });
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  function onSort(key: SortKey) {
    setPage(1);
    setSort((prev) => toggleSort(prev, key));
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Audit Log</h1>
        <p className="text-sm text-slate-400">Every mutating action, by user or the system scheduler.</p>
      </div>

      <Card>
        {isLoading ? (
          <PageSpinner />
        ) : !data || data.items.length === 0 ? (
          <EmptyState title="No audit entries yet" />
        ) : (
          <>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-400">
                  <SortHeader label="Time" sortKey="created_at" sort={sort} onSort={onSort} />
                  <SortHeader label="Actor" sortKey="actor_label" sort={sort} onSort={onSort} />
                  <SortHeader label="Action" sortKey="action" sort={sort} onSort={onSort} />
                  <SortHeader label="Target" sortKey="target_type" sort={sort} onSort={onSort} />
                  <th className="px-4 py-2">IP</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((a) => (
                  <tr key={a.id} className="border-b border-slate-800/60 last:border-0">
                    <td className="px-4 py-2 text-slate-400">{formatDateTime(a.created_at)}</td>
                    <td className="px-4 py-2 text-slate-300">{a.actor_label}</td>
                    <td className="px-4 py-2 font-mono text-xs text-slate-200">{a.action}</td>
                    <td className="px-4 py-2 text-slate-400">
                      {a.target_type} {a.target_id && <span className="text-slate-400">({a.target_id.slice(0, 8)})</span>}
                    </td>
                    <td className="px-4 py-2 text-slate-400">{a.ip_address || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex items-center justify-between border-t border-slate-800 px-4 py-2.5 text-xs text-slate-400">
              <span>
                {data.total} entries — page {page} of {totalPages}
              </span>
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <Button size="sm" variant="ghost" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                  Next
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
