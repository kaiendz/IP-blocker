import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, RefreshCw, Wifi, Cloud, Trash2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { DeviceOut, ForticloudCredentialOut, LogSource } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Label, Select } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Badge } from "@/components/ui/Badge";
import { Checkbox } from "@/components/ui/Checkbox";
import { SortHeader, toggleSort, type SortState } from "@/components/ui/SortHeader";
import { PageSpinner, EmptyState, Mono } from "@/components/ui/Misc";
import { cn, relativeTime } from "@/lib/utils";

const LOG_SOURCE_OPTIONS: { value: LogSource; label: string; hint: string }[] = [
  { value: "device_api", label: "Local", hint: "Direct from the FortiGate (read-only API)" },
  { value: "forticloud", label: "Cloud", hint: "Via FortiCloud (logs forwarded off-box)" },
];

type SortKey = "name" | "host" | "log_source" | "site_tag" | "last_polled_at";

function sortDevices(devices: DeviceOut[], sort: SortState<SortKey>): DeviceOut[] {
  const dir = sort.dir === "asc" ? 1 : -1;
  return [...devices].sort((a, b) => {
    const av = String(a[sort.key] ?? "");
    const bv = String(b[sort.key] ?? "");
    if (av < bv) return -1 * dir;
    if (av > bv) return 1 * dir;
    return 0;
  });
}

export function DevicesPage() {
  const { hasRole } = useAuth();
  const toast = useToast();
  const confirm = useConfirm();
  const qc = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [credOpen, setCredOpen] = useState(false);
  const [sort, setSort] = useState<SortState<SortKey>>({ key: "name", dir: "asc" });

  const { data: devices, isLoading } = useQuery({
    queryKey: ["devices"],
    queryFn: () => api.get<DeviceOut[]>("/devices"),
    refetchInterval: 20_000,
  });
  const { data: creds } = useQuery({
    queryKey: ["forticloud-credentials"],
    queryFn: () => api.get<ForticloudCredentialOut[]>("/devices/forticloud-credentials"),
  });

  const testMutation = useMutation({
    mutationFn: (id: string) => api.post<{ ok: boolean; message: string }>(`/devices/${id}/test-connection`),
    onSuccess: (res) => toast.push(res.message, res.ok ? "success" : "error"),
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Test failed", "error"),
  });
  const pollMutation = useMutation({
    mutationFn: (id: string) => api.post<{ ok: boolean; message: string }>(`/devices/${id}/poll-now`),
    onSuccess: (res) => {
      toast.push(res.message, res.ok ? "success" : "error");
      qc.invalidateQueries({ queryKey: ["devices"] });
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Poll failed", "error"),
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/devices/${id}`),
    onSuccess: () => {
      toast.push("Device removed");
      qc.invalidateQueries({ queryKey: ["devices"] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">FortiGate Devices</h1>
          <p className="text-sm text-slate-400">Read-only log polling — the app never writes to these devices.</p>
        </div>
        {hasRole("admin") && (
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setCredOpen(true)}>
              <Cloud className="h-4 w-4" /> FortiCloud credentials
            </Button>
            <Button variant="primary" onClick={() => setAddOpen(true)}>
              <Plus className="h-4 w-4" /> Add device
            </Button>
          </div>
        )}
      </div>

      <Card>
        {isLoading ? (
          <PageSpinner />
        ) : !devices || devices.length === 0 ? (
          <EmptyState title="No devices yet" subtitle="Add a FortiGate to start pulling auth-failure logs." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-400">
                <SortHeader label="Name" sortKey="name" sort={sort} onSort={(k) => setSort((p) => toggleSort(p, k))} />
                <SortHeader label="Host" sortKey="host" sort={sort} onSort={(k) => setSort((p) => toggleSort(p, k))} />
                <SortHeader
                  label="Log source"
                  sortKey="log_source"
                  sort={sort}
                  onSort={(k) => setSort((p) => toggleSort(p, k))}
                />
                <SortHeader label="Site" sortKey="site_tag" sort={sort} onSort={(k) => setSort((p) => toggleSort(p, k))} />
                <SortHeader
                  label="Last poll"
                  sortKey="last_polled_at"
                  sort={sort}
                  onSort={(k) => setSort((p) => toggleSort(p, k))}
                />
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortDevices(devices, sort).map((d) => (
                <tr key={d.id} className="border-b border-slate-800/60 last:border-0">
                  <td className="px-4 py-2 font-medium text-slate-200">{d.name}</td>
                  <td className="px-4 py-2">
                    <Mono>
                      {d.host}:{d.port}
                    </Mono>
                  </td>
                  <td className="px-4 py-2">
                    <Badge tone={d.log_source === "device_api" ? "neutral" : "info"}>
                      {d.log_source === "device_api" ? "Local" : "Cloud"}
                    </Badge>
                  </td>
                  <td className="px-4 py-2 text-slate-400">{d.site_tag || "—"}</td>
                  <td className="px-4 py-2 text-slate-400">{relativeTime(d.last_polled_at)}</td>
                  <td className="px-4 py-2">
                    <Badge tone={d.last_poll_status.startsWith("ok") ? "success" : d.last_poll_status.startsWith("error") ? "danger" : "neutral"}>
                      {d.last_poll_status}
                    </Badge>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex justify-end gap-1.5">
                      <Button size="sm" variant="ghost" loading={testMutation.isPending} onClick={() => testMutation.mutate(d.id)} title="Test connection">
                        <Wifi className="h-3.5 w-3.5" />
                      </Button>
                      {hasRole("analyst") && (
                        <Button size="sm" variant="ghost" loading={pollMutation.isPending} onClick={() => pollMutation.mutate(d.id)} title="Poll now">
                          <RefreshCw className="h-3.5 w-3.5" />
                        </Button>
                      )}
                      {hasRole("admin") && (
                        <Button
                          size="sm"
                          variant="ghost"
                          aria-label={`Remove device ${d.name}`}
                          title="Delete"
                          onClick={async () => {
                            const ok = await confirm({
                              title: "Remove this device?",
                              description: `"${d.name}" will stop being polled for logs. Blacklist entries it already contributed stay in effect.`,
                              confirmLabel: "Remove",
                              danger: true,
                            });
                            if (ok) deleteMutation.mutate(d.id);
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

      {addOpen && <AddDeviceModal onClose={() => setAddOpen(false)} credentials={creds ?? []} />}
      {credOpen && <ForticloudCredentialsModal onClose={() => setCredOpen(false)} credentials={creds ?? []} />}
    </div>
  );
}

function AddDeviceModal({ onClose, credentials }: { onClose: () => void; credentials: ForticloudCredentialOut[] }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({
    name: "",
    host: "",
    port: 443,
    vdom: "root",
    api_token: "",
    verify_tls: true,
    site_tag: "",
    log_source: "device_api" as LogSource,
    forticloud_credential_id: "",
    forticloud_serial: "",
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/devices", {
        ...form,
        forticloud_credential_id: form.forticloud_credential_id || null,
      }),
    onSuccess: () => {
      toast.push("Device added");
      qc.invalidateQueries({ queryKey: ["devices"] });
      onClose();
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Failed to add device", "error"),
  });

  return (
    <Modal open onClose={onClose} title="Add FortiGate device" width="max-w-lg">
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="name">Name</Label>
            <Input id="name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="site">Site tag</Label>
            <Input id="site" value={form.site_tag} onChange={(e) => setForm({ ...form, site_tag: e.target.value })} placeholder="hq, branch-1, ..." />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-2">
            <Label htmlFor="host">Host / IP</Label>
            <Input id="host" required value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} placeholder="fw01.example.com" />
          </div>
          <div>
            <Label htmlFor="port">Port</Label>
            <Input id="port" type="number" value={form.port} onChange={(e) => setForm({ ...form, port: Number(e.target.value) })} />
          </div>
        </div>
        <fieldset>
          <legend className="mb-1 block text-xs font-medium text-slate-400">Log source</legend>
          <div className="grid grid-cols-2 gap-2">
            {LOG_SOURCE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                aria-pressed={form.log_source === opt.value}
                onClick={() => setForm({ ...form, log_source: opt.value })}
                className={cn(
                  "rounded-md border px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500",
                  form.log_source === opt.value
                    ? "border-brand-500 bg-brand-600/15"
                    : "border-slate-700 hover:border-slate-600 hover:bg-slate-800/50"
                )}
              >
                <div className={cn("text-sm font-semibold", form.log_source === opt.value ? "text-brand-300" : "text-slate-200")}>
                  {opt.label}
                </div>
                <div className="mt-0.5 text-xs text-slate-400">{opt.hint}</div>
              </button>
            ))}
          </div>
        </fieldset>
        {form.log_source === "device_api" ? (
          <>
            <div>
              <Label htmlFor="token">Read-only API token</Label>
              <Input id="token" type="password" value={form.api_token} onChange={(e) => setForm({ ...form, api_token: e.target.value })} placeholder="Create via System > Administrators > REST API Admin" />
            </div>
            <label className="flex items-center gap-2 text-xs text-slate-400">
              <Checkbox checked={form.verify_tls} onChange={(e) => setForm({ ...form, verify_tls: e.target.checked })} />
              Verify TLS certificate
            </label>
          </>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="cred">FortiCloud credential</Label>
              <Select id="cred" value={form.forticloud_credential_id} onChange={(e) => setForm({ ...form, forticloud_credential_id: e.target.value })}>
                <option value="">Select…</option>
                {credentials.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="serial">Device serial</Label>
              <Input id="serial" value={form.forticloud_serial} onChange={(e) => setForm({ ...form, forticloud_serial: e.target.value })} placeholder="FGT..." />
            </div>
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>
            Add device
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ForticloudCredentialsModal({ onClose, credentials }: { onClose: () => void; credentials: ForticloudCredentialOut[] }) {
  const qc = useQueryClient();
  const toast = useToast();
  const confirm = useConfirm();
  const [form, setForm] = useState({ name: "", client_id: "", client_secret: "", api_gateway: "https://customerapiauth.fortinet.com" });

  const createMutation = useMutation({
    mutationFn: () => api.post("/devices/forticloud-credentials", form),
    onSuccess: () => {
      toast.push("Credential saved");
      qc.invalidateQueries({ queryKey: ["forticloud-credentials"] });
      setForm({ name: "", client_id: "", client_secret: "", api_gateway: "https://customerapiauth.fortinet.com" });
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Failed to save credential", "error"),
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/devices/forticloud-credentials/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["forticloud-credentials"] }),
  });

  return (
    <Modal open onClose={onClose} title="FortiCloud credentials" width="max-w-lg">
      <div className="space-y-4">
        <ul className="space-y-1.5">
          {credentials.map((c) => (
            <li key={c.id} className="flex items-center justify-between rounded-md border border-slate-800 px-3 py-1.5 text-sm">
              <span>{c.name}</span>
              <Button
                size="sm"
                variant="ghost"
                aria-label={`Delete FortiCloud credential ${c.name}`}
                title="Delete"
                onClick={async () => {
                  const ok = await confirm({
                    title: "Delete this credential?",
                    description: `Any device linked to "${c.name}" will stop polling until you attach a different credential.`,
                    confirmLabel: "Delete",
                    danger: true,
                  });
                  if (ok) deleteMutation.mutate(c.id);
                }}
              >
                <Trash2 className="h-3.5 w-3.5 text-red-400" />
              </Button>
            </li>
          ))}
          {credentials.length === 0 && <p className="text-xs text-slate-400">No FortiCloud credentials saved yet.</p>}
        </ul>
        <form
          className="space-y-2 border-t border-slate-800 pt-3"
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
        >
          <Input required placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Input required placeholder="Client ID" value={form.client_id} onChange={(e) => setForm({ ...form, client_id: e.target.value })} />
          <Input required type="password" placeholder="Client secret" value={form.client_secret} onChange={(e) => setForm({ ...form, client_secret: e.target.value })} />
          <Input placeholder="API gateway" value={form.api_gateway} onChange={(e) => setForm({ ...form, api_gateway: e.target.value })} />
          <Button type="submit" variant="primary" loading={createMutation.isPending} className="w-full">
            Save credential
          </Button>
        </form>
      </div>
    </Modal>
  );
}
