import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldBan, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { AuthEventOut, Page } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import { Card, CardBody } from "@/components/ui/Card";
import { Input, Select } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Checkbox } from "@/components/ui/Checkbox";
import { SortHeader, toggleSort, type SortState } from "@/components/ui/SortHeader";
import { PageSpinner, EmptyState, Mono } from "@/components/ui/Misc";
import { formatDateTime } from "@/lib/utils";

const PAGE_SIZE = 25;

type SortKey = "event_time" | "src_ip" | "username" | "vpn_type" | "action";

export function EventsPage() {
  const { hasRole } = useAuth();
  const toast = useToast();
  const confirm = useConfirm();
  const qc = useQueryClient();
  const [srcIp, setSrcIp] = useState("");
  const [vpnType, setVpnType] = useState("");
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<SortState<SortKey>>({ key: "event_time", dir: "desc" });
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const params = new URLSearchParams({
    page: String(page),
    page_size: String(PAGE_SIZE),
    sort_by: sort.key,
    sort_dir: sort.dir,
  });
  if (srcIp) params.set("src_ip", srcIp);
  if (vpnType) params.set("vpn_type", vpnType);
  if (action) params.set("action", action);

  const { data, isLoading } = useQuery({
    queryKey: ["events", srcIp, vpnType, action, page, sort.key, sort.dir],
    queryFn: () => api.get<Page<AuthEventOut>>(`/events?${params.toString()}`),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const selectableIds = (data?.items ?? []).filter((e) => e.action !== "success").map((e) => e.id);
  const allSelected = selectableIds.length > 0 && selectableIds.every((id) => selected.has(id));
  const someSelected = selectableIds.some((id) => selected.has(id));
  const selectedIps = [
    ...new Set((data?.items ?? []).filter((e) => selected.has(e.id)).map((e) => e.src_ip)),
  ];

  function toggleOne(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((prev) => {
      if (allSelected) return new Set();
      return new Set([...prev, ...selectableIds]);
    });
  }

  function onSort(key: SortKey) {
    setSort((prev) => toggleSort(prev, key));
  }

  const bulkBlacklistMutation = useMutation({
    mutationFn: async (ips: string[]) => {
      const results = await Promise.allSettled(
        ips.map((ip) =>
          api.post("/blacklist", {
            ip_or_cidr: ip,
            reason_detail: "manually blacklisted from Events",
            ttl_hours: 24,
          })
        )
      );
      const failed = results.filter((r) => r.status === "rejected").length;
      return { succeeded: results.length - failed, failed };
    },
    onSuccess: ({ succeeded, failed }) => {
      if (succeeded > 0) toast.push(`Blacklisted ${succeeded} IP${succeeded === 1 ? "" : "s"}`);
      if (failed > 0) toast.push(`${failed} IP${failed === 1 ? "" : "s"} failed (may already be listed)`, "error");
      setSelected(new Set());
      qc.invalidateQueries({ queryKey: ["blacklist"] });
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Bulk blacklist failed", "error"),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Auth Events</h1>
        <p className="text-sm text-slate-400">Normalized login events pulled from FortiGate / FortiCloud.</p>
      </div>

      <Card>
        <CardBody className="flex flex-wrap items-end gap-3 border-b border-slate-800">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Source IP</label>
            <Input
              value={srcIp}
              onChange={(e) => {
                setPage(1);
                setSrcIp(e.target.value);
              }}
              placeholder="1.2.3.4"
              className="w-40"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">VPN type</label>
            <Select
              value={vpnType}
              onChange={(e) => {
                setPage(1);
                setVpnType(e.target.value);
              }}
              className="w-36"
            >
              <option value="">All</option>
              <option value="sslvpn">SSL VPN</option>
              <option value="ike">IKE/IPsec</option>
              <option value="admin">Admin</option>
            </Select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Action</label>
            <Select
              value={action}
              onChange={(e) => {
                setPage(1);
                setAction(e.target.value);
              }}
              className="w-36"
            >
              <option value="">All</option>
              <option value="failed">Failed</option>
              <option value="locked">Locked</option>
              <option value="success">Success</option>
            </Select>
          </div>
        </CardBody>

        {hasRole("analyst") && someSelected && (
          <div className="flex items-center justify-between border-b border-slate-800 bg-brand-600/10 px-4 py-2.5">
            <span className="text-sm text-brand-200">
              {selected.size} event{selected.size === 1 ? "" : "s"} selected · {selectedIps.length} unique IP
              {selectedIps.length === 1 ? "" : "s"}
            </span>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>
                <X className="h-3.5 w-3.5" /> Clear
              </Button>
              <Button
                size="sm"
                variant="danger"
                loading={bulkBlacklistMutation.isPending}
                onClick={async () => {
                  const ok = await confirm({
                    title: `Blacklist ${selectedIps.length} IP${selectedIps.length === 1 ? "" : "s"}?`,
                    description: "They'll be added to the blacklist for 24h and published to the Azure feed on the next publish cycle.",
                    confirmLabel: "Blacklist",
                    danger: true,
                  });
                  if (ok) bulkBlacklistMutation.mutate(selectedIps);
                }}
              >
                <ShieldBan className="h-3.5 w-3.5" /> Blacklist selected
              </Button>
            </div>
          </div>
        )}

        {isLoading ? (
          <PageSpinner />
        ) : !data || data.items.length === 0 ? (
          <EmptyState title="No events found" subtitle="Once devices are polling, failed logins will show up here." />
        ) : (
          <>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-400">
                  {hasRole("analyst") && (
                    <th className="w-10 px-4 py-2">
                      <Checkbox
                        aria-label="Select all failed/locked events on this page"
                        checked={allSelected}
                        indeterminate={someSelected && !allSelected}
                        onChange={toggleAll}
                        disabled={selectableIds.length === 0}
                      />
                    </th>
                  )}
                  <SortHeader label="Time" sortKey="event_time" sort={sort} onSort={onSort} />
                  <SortHeader label="Source IP" sortKey="src_ip" sort={sort} onSort={onSort} />
                  <SortHeader label="User" sortKey="username" sort={sort} onSort={onSort} />
                  <SortHeader label="Type" sortKey="vpn_type" sort={sort} onSort={onSort} />
                  <SortHeader label="Action" sortKey="action" sort={sort} onSort={onSort} />
                  <th className="px-4 py-2">Detail</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((e) => (
                  <tr key={e.id} className="border-b border-slate-800/60 last:border-0">
                    {hasRole("analyst") && (
                      <td className="px-4 py-2">
                        {e.action !== "success" && (
                          <Checkbox
                            aria-label={`Select event from ${e.src_ip}`}
                            checked={selected.has(e.id)}
                            onChange={() => toggleOne(e.id)}
                          />
                        )}
                      </td>
                    )}
                    <td className="px-4 py-2 text-slate-400">{formatDateTime(e.event_time)}</td>
                    <td className="px-4 py-2">
                      <Mono>{e.src_ip}</Mono>
                    </td>
                    <td className="px-4 py-2 text-slate-300">{e.username || "—"}</td>
                    <td className="px-4 py-2 text-slate-400">{e.vpn_type}</td>
                    <td className="px-4 py-2">
                      <Badge tone={e.action === "failed" ? "danger" : e.action === "locked" ? "warning" : "success"}>{e.action}</Badge>
                    </td>
                    <td className="max-w-xs truncate px-4 py-2 text-slate-400">{e.reason_text}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex items-center justify-between border-t border-slate-800 px-4 py-2.5 text-xs text-slate-400">
              <span>
                {data.total} event(s) — page {page} of {totalPages}
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
