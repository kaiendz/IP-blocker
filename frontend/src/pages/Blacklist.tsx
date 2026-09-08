import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { BlacklistOut, BlacklistReason, BlacklistStatus, Page } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Label, Select } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Badge } from "@/components/ui/Badge";
import { Checkbox } from "@/components/ui/Checkbox";
import { SortHeader, toggleSort, type SortState } from "@/components/ui/SortHeader";
import { PageSpinner, EmptyState, Mono } from "@/components/ui/Misc";
import { formatDateTime } from "@/lib/utils";

const PAGE_SIZE = 50;

const REASON_TONE: Record<BlacklistReason, "danger" | "warning" | "info"> = {
  brute_force: "danger",
  threat_intel: "warning",
  manual: "info",
};

type SortKey = "ip_or_cidr" | "reason_type" | "created_at" | "expires_at" | "status";

export function BlacklistPage() {
  const { hasRole } = useAuth();
  const toast = useToast();
  const confirm = useConfirm();
  const qc = useQueryClient();
  const [status, setStatus] = useState<BlacklistStatus | "">("active");
  const [reason, setReason] = useState<BlacklistReason | "">("");
  const [q, setQ] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [sort, setSort] = useState<SortState<SortKey>>({ key: "created_at", dir: "desc" });
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const params = new URLSearchParams({
    page: "1",
    page_size: String(PAGE_SIZE),
    sort_by: sort.key,
    sort_dir: sort.dir,
  });
  if (status) params.set("status_filter", status);
  if (reason) params.set("reason_type", reason);
  if (q) params.set("q", q);

  const { data, isLoading } = useQuery({
    queryKey: ["blacklist", status, reason, q, sort.key, sort.dir],
    queryFn: () => api.get<Page<BlacklistOut>>(`/blacklist?${params.toString()}`),
    refetchInterval: 30_000,
  });

  const removableIds = (data?.items ?? []).filter((e) => e.status === "active").map((e) => e.id);
  const allSelected = removableIds.length > 0 && removableIds.every((id) => selected.has(id));
  const someSelected = removableIds.some((id) => selected.has(id));

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
      return new Set([...prev, ...removableIds]);
    });
  }

  function onSort(key: SortKey) {
    setSort((prev) => toggleSort(prev, key));
  }

  const removeMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/blacklist/${id}`),
    onSuccess: () => {
      toast.push("Entry removed");
      qc.invalidateQueries({ queryKey: ["blacklist"] });
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Failed to remove", "error"),
  });

  const bulkRemoveMutation = useMutation({
    mutationFn: (ids: string[]) => api.post<{ removed_count: number }>("/blacklist/bulk-remove", { ids }),
    onSuccess: (res) => {
      toast.push(`Removed ${res.removed_count} ${res.removed_count === 1 ? "entry" : "entries"}`);
      setSelected(new Set());
      qc.invalidateQueries({ queryKey: ["blacklist"] });
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Bulk remove failed", "error"),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Blacklist</h1>
          <p className="text-sm text-slate-400">Published to Azure Storage for FortiGates to pull as a threat feed.</p>
        </div>
        {hasRole("analyst") && (
          <Button variant="primary" onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" /> Add IP manually
          </Button>
        )}
      </div>

      <Card>
        <CardBody className="flex flex-wrap items-end gap-3 border-b border-slate-800">
          <div>
            <Label>Status</Label>
            <Select
              value={status}
              onChange={(e) => {
                setSelected(new Set());
                setStatus(e.target.value as BlacklistStatus | "");
              }}
              className="w-36"
            >
              <option value="active">Active</option>
              <option value="expired">Expired</option>
              <option value="removed">Removed</option>
              <option value="">All</option>
            </Select>
          </div>
          <div>
            <Label>Reason</Label>
            <Select value={reason} onChange={(e) => setReason(e.target.value as BlacklistReason | "")} className="w-40">
              <option value="">All</option>
              <option value="brute_force">Brute force</option>
              <option value="threat_intel">Threat intel</option>
              <option value="manual">Manual</option>
            </Select>
          </div>
          <div>
            <Label>Search</Label>
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="IP / CIDR" className="w-48" />
          </div>
        </CardBody>

        {hasRole("analyst") && someSelected && (
          <div className="flex items-center justify-between border-b border-slate-800 bg-brand-600/10 px-4 py-2.5">
            <span className="text-sm text-brand-200">
              {selected.size} {selected.size === 1 ? "entry" : "entries"} selected
            </span>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>
                <X className="h-3.5 w-3.5" /> Clear
              </Button>
              <Button
                size="sm"
                variant="danger"
                loading={bulkRemoveMutation.isPending}
                onClick={async () => {
                  const ok = await confirm({
                    title: `Remove ${selected.size} ${selected.size === 1 ? "entry" : "entries"}?`,
                    description: "These IPs will stop being published to the Azure feed and FortiGates will no longer block them.",
                    confirmLabel: "Remove all",
                    danger: true,
                  });
                  if (ok) bulkRemoveMutation.mutate([...selected]);
                }}
              >
                <Trash2 className="h-3.5 w-3.5" /> Remove selected
              </Button>
            </div>
          </div>
        )}

        {isLoading ? (
          <PageSpinner />
        ) : !data || data.items.length === 0 ? (
          <EmptyState title="No entries" subtitle="Nothing matches the current filters." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-400">
                {hasRole("analyst") && (
                  <th className="w-10 px-4 py-2">
                    <Checkbox
                      aria-label="Select all active entries"
                      checked={allSelected}
                      indeterminate={someSelected && !allSelected}
                      onChange={toggleAll}
                      disabled={removableIds.length === 0}
                    />
                  </th>
                )}
                <SortHeader label="IP / CIDR" sortKey="ip_or_cidr" sort={sort} onSort={onSort} />
                <SortHeader label="Reason" sortKey="reason_type" sort={sort} onSort={onSort} />
                <th className="px-4 py-2">Detail</th>
                <SortHeader label="Added" sortKey="created_at" sort={sort} onSort={onSort} />
                <SortHeader label="Expires" sortKey="expires_at" sort={sort} onSort={onSort} />
                <SortHeader label="Status" sortKey="status" sort={sort} onSort={onSort} />
                {hasRole("analyst") && <th className="px-4 py-2 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {data.items.map((entry) => (
                <tr key={entry.id} className="border-b border-slate-800/60 last:border-0">
                  {hasRole("analyst") && (
                    <td className="px-4 py-2">
                      {entry.status === "active" && (
                        <Checkbox
                          aria-label={`Select ${entry.ip_or_cidr}`}
                          checked={selected.has(entry.id)}
                          onChange={() => toggleOne(entry.id)}
                        />
                      )}
                    </td>
                  )}
                  <td className="px-4 py-2">
                    <Mono>{entry.ip_or_cidr}</Mono>
                  </td>
                  <td className="px-4 py-2">
                    <Badge tone={REASON_TONE[entry.reason_type]}>{entry.reason_type.replace("_", " ")}</Badge>
                  </td>
                  <td className="max-w-xs truncate px-4 py-2 text-slate-400">{entry.reason_detail}</td>
                  <td className="px-4 py-2 text-slate-400">{formatDateTime(entry.created_at)}</td>
                  <td className="px-4 py-2 text-slate-400">{entry.expires_at ? formatDateTime(entry.expires_at) : "permanent"}</td>
                  <td className="px-4 py-2">
                    <Badge tone={entry.status === "active" ? "success" : "neutral"}>{entry.status}</Badge>
                  </td>
                  {hasRole("analyst") && (
                    <td className="px-4 py-2 text-right">
                      {entry.status === "active" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          aria-label={`Remove ${entry.ip_or_cidr} from the blacklist`}
                          title="Remove"
                          onClick={async () => {
                            const ok = await confirm({
                              title: "Remove from blacklist?",
                              description: `${entry.ip_or_cidr} will stop being published to the Azure feed and FortiGates will no longer block it.`,
                              confirmLabel: "Remove",
                              danger: true,
                            });
                            if (ok) removeMutation.mutate(entry.id);
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-red-400" />
                        </Button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {addOpen && <AddBlacklistModal onClose={() => setAddOpen(false)} />}
    </div>
  );
}

function AddBlacklistModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [ip, setIp] = useState("");
  const [reasonDetail, setReasonDetail] = useState("manually added");
  const [ttlHours, setTtlHours] = useState<string>("24");

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/blacklist", {
        ip_or_cidr: ip,
        reason_detail: reasonDetail,
        ttl_hours: ttlHours ? Number(ttlHours) : null,
      }),
    onSuccess: () => {
      toast.push("IP blacklisted");
      qc.invalidateQueries({ queryKey: ["blacklist"] });
      onClose();
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Failed to add entry", "error"),
  });

  return (
    <Modal open onClose={onClose} title="Add IP to blacklist">
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <div>
          <Label htmlFor="ip">IP address or CIDR</Label>
          <Input id="ip" required value={ip} onChange={(e) => setIp(e.target.value)} placeholder="203.0.113.7 or 203.0.113.0/24" />
        </div>
        <div>
          <Label htmlFor="detail">Reason</Label>
          <Input id="detail" value={reasonDetail} onChange={(e) => setReasonDetail(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="ttl">Expires after (hours, blank = permanent)</Label>
          <Input id="ttl" type="number" value={ttlHours} onChange={(e) => setTtlHours(e.target.value)} />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>
            Add
          </Button>
        </div>
      </form>
    </Modal>
  );
}
