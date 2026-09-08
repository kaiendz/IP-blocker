import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { DetectionRuleOut } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Badge } from "@/components/ui/Badge";
import { PageSpinner, EmptyState } from "@/components/ui/Misc";

const EVENT_TYPES = ["sslvpn", "ike", "admin"];

export function RulesPage() {
  const { hasRole } = useAuth();
  const toast = useToast();
  const confirm = useConfirm();
  const qc = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["rules"],
    queryFn: () => api.get<DetectionRuleOut[]>("/rules"),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => api.patch(`/rules/${id}`, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/rules/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Detection Rules</h1>
          <p className="text-sm text-slate-400">"N failed logins within M minutes" → auto-blacklist for a TTL.</p>
        </div>
        {hasRole("admin") && (
          <Button variant="primary" onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" /> Add rule
          </Button>
        )}
      </div>

      <Card>
        {isLoading ? (
          <PageSpinner />
        ) : !data || data.length === 0 ? (
          <EmptyState title="No detection rules" />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Event types</th>
                <th className="px-4 py-2">Threshold</th>
                <th className="px-4 py-2">Window</th>
                <th className="px-4 py-2">TTL</th>
                <th className="px-4 py-2">Enabled</th>
                {hasRole("admin") && <th className="px-4 py-2 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {data.map((r) => (
                <tr key={r.id} className="border-b border-slate-800/60 last:border-0">
                  <td className="px-4 py-2 font-medium text-slate-200">{r.name}</td>
                  <td className="px-4 py-2 text-slate-400">{r.event_types.join(", ")}</td>
                  <td className="px-4 py-2 text-slate-300">{r.threshold_count} failures</td>
                  <td className="px-4 py-2 text-slate-300">{r.window_minutes} min</td>
                  <td className="px-4 py-2 text-slate-300">{r.ttl_hours}h</td>
                  <td className="px-4 py-2">
                    {hasRole("admin") ? (
                      <button onClick={() => toggleMutation.mutate({ id: r.id, enabled: !r.enabled })}>
                        <Badge tone={r.enabled ? "success" : "neutral"}>{r.enabled ? "enabled" : "disabled"}</Badge>
                      </button>
                    ) : (
                      <Badge tone={r.enabled ? "success" : "neutral"}>{r.enabled ? "enabled" : "disabled"}</Badge>
                    )}
                  </td>
                  {hasRole("admin") && (
                    <td className="px-4 py-2 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        aria-label={`Delete rule ${r.name}`}
                        title="Delete"
                        onClick={async () => {
                          const ok = await confirm({
                            title: "Delete detection rule?",
                            description: `"${r.name}" will stop watching for brute-force logins. IPs it already blacklisted stay blacklisted until their TTL expires.`,
                            confirmLabel: "Delete",
                            danger: true,
                          });
                          if (ok) deleteMutation.mutate(r.id);
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5 text-red-400" />
                      </Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {addOpen && <AddRuleModal onClose={() => setAddOpen(false)} />}
    </div>
  );
}

function AddRuleModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [name, setName] = useState("");
  const [eventTypes, setEventTypes] = useState<string[]>(["sslvpn", "ike", "admin"]);
  const [threshold, setThreshold] = useState(5);
  const [window, setWindowMin] = useState(10);
  const [ttl, setTtl] = useState(24);

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/rules", {
        name,
        scope: "global",
        event_types: eventTypes,
        threshold_count: threshold,
        window_minutes: window,
        ttl_hours: ttl,
        enabled: true,
      }),
    onSuccess: () => {
      toast.push("Rule created");
      qc.invalidateQueries({ queryKey: ["rules"] });
      onClose();
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Failed to create rule", "error"),
  });

  function toggleType(t: string) {
    setEventTypes((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));
  }

  return (
    <Modal open onClose={onClose} title="Add detection rule">
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <div>
          <Label htmlFor="name">Name</Label>
          <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <Label>Event types</Label>
          <div className="flex gap-3 pt-1">
            {EVENT_TYPES.map((t) => (
              <label key={t} className="flex items-center gap-1.5 text-sm text-slate-300">
                <input type="checkbox" checked={eventTypes.includes(t)} onChange={() => toggleType(t)} />
                {t}
              </label>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label htmlFor="threshold">Threshold (fails)</Label>
            <Input id="threshold" type="number" min={1} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} />
          </div>
          <div>
            <Label htmlFor="window">Window (min)</Label>
            <Input id="window" type="number" min={1} value={window} onChange={(e) => setWindowMin(Number(e.target.value))} />
          </div>
          <div>
            <Label htmlFor="ttl">TTL (hours)</Label>
            <Input id="ttl" type="number" min={1} value={ttl} onChange={(e) => setTtl(Number(e.target.value))} />
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>
            Create rule
          </Button>
        </div>
      </form>
    </Modal>
  );
}
