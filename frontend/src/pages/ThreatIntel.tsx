import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, RefreshCw, Trash2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { ThreatIntelFormat, ThreatIntelSourceOut } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Label, Select } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Badge } from "@/components/ui/Badge";
import { PageSpinner, EmptyState } from "@/components/ui/Misc";
import { relativeTime } from "@/lib/utils";

export function ThreatIntelPage() {
  const { hasRole } = useAuth();
  const toast = useToast();
  const confirm = useConfirm();
  const qc = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["threat-intel"],
    queryFn: () => api.get<ThreatIntelSourceOut[]>("/threat-intel"),
    refetchInterval: 30_000,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => api.patch(`/threat-intel/${id}`, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["threat-intel"] }),
  });
  const fetchNowMutation = useMutation({
    mutationFn: (id: string) => api.post<{ ok: boolean; message: string }>(`/threat-intel/${id}/fetch-now`),
    onSuccess: (res) => {
      toast.push(res.message, res.ok ? "success" : "error");
      qc.invalidateQueries({ queryKey: ["threat-intel"] });
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Fetch failed", "error"),
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/threat-intel/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["threat-intel"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Threat Intel Sources</h1>
          <p className="text-sm text-slate-400">
            Reputable public IP blocklists. A few free plaintext feeds are seeded — enable the ones you want.
          </p>
        </div>
        {hasRole("admin") && (
          <Button variant="primary" onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" /> Add source
          </Button>
        )}
      </div>

      <Card>
        {isLoading ? (
          <PageSpinner />
        ) : !data || data.length === 0 ? (
          <EmptyState title="No sources configured" />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">URL</th>
                <th className="px-4 py-2">Indicators</th>
                <th className="px-4 py-2">Last fetch</th>
                <th className="px-4 py-2">Enabled</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((s) => (
                <tr key={s.id} className="border-b border-slate-800/60 last:border-0">
                  <td className="px-4 py-2 font-medium text-slate-200">{s.name}</td>
                  <td className="max-w-xs truncate px-4 py-2 text-slate-400">{s.url}</td>
                  <td className="px-4 py-2 text-slate-300">{s.indicator_count}</td>
                  <td className="px-4 py-2 text-slate-400" title={s.last_fetch_status}>
                    {relativeTime(s.last_fetch_at)}
                  </td>
                  <td className="px-4 py-2">
                    {hasRole("admin") ? (
                      <button onClick={() => toggleMutation.mutate({ id: s.id, enabled: !s.enabled })}>
                        <Badge tone={s.enabled ? "success" : "neutral"}>{s.enabled ? "enabled" : "disabled"}</Badge>
                      </button>
                    ) : (
                      <Badge tone={s.enabled ? "success" : "neutral"}>{s.enabled ? "enabled" : "disabled"}</Badge>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <div className="flex justify-end gap-1.5">
                      {hasRole("analyst") && (
                        <Button size="sm" variant="ghost" loading={fetchNowMutation.isPending} onClick={() => fetchNowMutation.mutate(s.id)} title="Fetch now">
                          <RefreshCw className="h-3.5 w-3.5" />
                        </Button>
                      )}
                      {hasRole("admin") && (
                        <Button
                          size="sm"
                          variant="ghost"
                          aria-label={`Delete threat intel source ${s.name}`}
                          title="Delete"
                          onClick={async () => {
                            const ok = await confirm({
                              title: "Delete threat intel source?",
                              description: `"${s.name}" will stop being fetched. Indicators it already contributed to the blacklist are not removed automatically.`,
                              confirmLabel: "Delete",
                              danger: true,
                            });
                            if (ok) deleteMutation.mutate(s.id);
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-red-400" />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {addOpen && <AddSourceModal onClose={() => setAddOpen(false)} />}
    </div>
  );
}

function AddSourceModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({
    name: "",
    url: "",
    format: "plain_ip_list" as ThreatIntelFormat,
    api_key: "",
    refresh_interval_minutes: 60,
  });

  const mutation = useMutation({
    mutationFn: () => api.post("/threat-intel", form),
    onSuccess: () => {
      toast.push("Source added");
      qc.invalidateQueries({ queryKey: ["threat-intel"] });
      onClose();
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Failed to add source", "error"),
  });

  return (
    <Modal open onClose={onClose} title="Add threat intel source">
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <div>
          <Label htmlFor="name">Name</Label>
          <Input id="name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div>
          <Label htmlFor="url">Feed URL</Label>
          <Input id="url" required value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="https://example.org/blocklist.txt" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="format">Format</Label>
            <Select id="format" value={form.format} onChange={(e) => setForm({ ...form, format: e.target.value as ThreatIntelFormat })}>
              <option value="plain_ip_list">Plain IP list</option>
              <option value="csv">CSV (IP in first column)</option>
              <option value="json">JSON (array of IPs/objects)</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="refresh">Refresh interval (min)</Label>
            <Input
              id="refresh"
              type="number"
              value={form.refresh_interval_minutes}
              onChange={(e) => setForm({ ...form, refresh_interval_minutes: Number(e.target.value) })}
            />
          </div>
        </div>
        <div>
          <Label htmlFor="key">API key (optional, sent as Bearer token)</Label>
          <Input id="key" type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>
            Add source
          </Button>
        </div>
      </form>
    </Modal>
  );
}
