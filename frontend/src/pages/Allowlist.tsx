import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { AllowlistOut } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { PageSpinner, EmptyState, Mono } from "@/components/ui/Misc";
import { formatDateTime } from "@/lib/utils";

export function AllowlistPage() {
  const { hasRole } = useAuth();
  const toast = useToast();
  const confirm = useConfirm();
  const qc = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["allowlist"],
    queryFn: () => api.get<AllowlistOut[]>("/allowlist"),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/allowlist/${id}`),
    onSuccess: () => {
      toast.push("Entry removed");
      qc.invalidateQueries({ queryKey: ["allowlist"] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Allowlist</h1>
          <p className="text-sm text-slate-400">
            These IPs/CIDRs are never blacklisted or published — plus a hardcoded RFC1918/loopback safety net.
          </p>
        </div>
        {hasRole("analyst") && (
          <Button variant="primary" onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" /> Add to allowlist
          </Button>
        )}
      </div>

      <Card>
        {isLoading ? (
          <PageSpinner />
        ) : !data || data.length === 0 ? (
          <EmptyState title="No allowlist entries" subtitle="Add trusted office/admin IPs here to guarantee they're never blocked." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-4 py-2">IP / CIDR</th>
                <th className="px-4 py-2">Note</th>
                <th className="px-4 py-2">Added by</th>
                <th className="px-4 py-2">Added</th>
                {hasRole("analyst") && <th className="px-4 py-2 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {data.map((entry) => (
                <tr key={entry.id} className="border-b border-slate-800/60 last:border-0">
                  <td className="px-4 py-2">
                    <Mono>{entry.ip_or_cidr}</Mono>
                  </td>
                  <td className="px-4 py-2 text-slate-400">{entry.note || "—"}</td>
                  <td className="px-4 py-2 text-slate-400">{entry.created_by}</td>
                  <td className="px-4 py-2 text-slate-400">{formatDateTime(entry.created_at)}</td>
                  {hasRole("analyst") && (
                    <td className="px-4 py-2 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        aria-label={`Remove ${entry.ip_or_cidr} from the allowlist`}
                        title="Remove"
                        onClick={async () => {
                          const ok = await confirm({
                            title: "Remove from allowlist?",
                            description: `${entry.ip_or_cidr} will lose its blanket protection and could be auto-blacklisted again if it matches a detection rule or threat-intel feed.`,
                            confirmLabel: "Remove",
                            danger: true,
                          });
                          if (ok) removeMutation.mutate(entry.id);
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

      {addOpen && <AddAllowlistModal onClose={() => setAddOpen(false)} />}
    </div>
  );
}

function AddAllowlistModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [ip, setIp] = useState("");
  const [note, setNote] = useState("");

  const mutation = useMutation({
    mutationFn: () => api.post("/allowlist", { ip_or_cidr: ip, note }),
    onSuccess: () => {
      toast.push("Added to allowlist");
      qc.invalidateQueries({ queryKey: ["allowlist"] });
      onClose();
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Failed to add", "error"),
  });

  return (
    <Modal open onClose={onClose} title="Add to allowlist">
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
          <Label htmlFor="note">Note</Label>
          <Input id="note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="HQ office IP" />
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
