import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CloudUpload, Copy } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { AzurePublishConfigOut, PublishedFeedPartOut } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { EmptyState, Mono, PageSpinner } from "@/components/ui/Misc";
import { formatDateTime } from "@/lib/utils";

export function AzurePublishPage() {
  const { hasRole } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();

  const { data: config, isLoading } = useQuery({
    queryKey: ["azure-config"],
    queryFn: () => api.get<AzurePublishConfigOut>("/azure-publish/config"),
  });
  const { data: parts } = useQuery({
    queryKey: ["azure-parts"],
    queryFn: () => api.get<PublishedFeedPartOut[]>("/azure-publish/parts"),
    refetchInterval: 20_000,
  });

  const [form, setForm] = useState({
    connection_string: "",
    sas_url: "",
    container_name: "fortigate-blacklist",
    blob_prefix: "blacklist/part-",
    chunk_size: 2000,
    sas_expiry_days: 7,
    publish_interval_minutes: 5,
    generate_sas: true,
    enabled: false,
  });

  useEffect(() => {
    if (config) {
      setForm((f) => ({
        ...f,
        container_name: config.container_name,
        blob_prefix: config.blob_prefix,
        chunk_size: config.chunk_size,
        sas_expiry_days: config.sas_expiry_days,
        publish_interval_minutes: config.publish_interval_minutes,
        generate_sas: config.generate_sas,
        enabled: config.enabled,
      }));
    }
  }, [config]);

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = { ...form };
      if (!payload.connection_string) delete payload.connection_string;
      if (!payload.sas_url) delete payload.sas_url;
      return api.put("/azure-publish/config", payload);
    },
    onSuccess: () => {
      toast.push("Azure publish settings saved");
      qc.invalidateQueries({ queryKey: ["azure-config"] });
      setForm((f) => ({ ...f, connection_string: "", sas_url: "" }));
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Failed to save", "error"),
  });

  const publishMutation = useMutation({
    mutationFn: () => api.post<{ ok: boolean; message: string }>("/azure-publish/publish-now"),
    onSuccess: (res) => {
      toast.push(res.message, res.ok ? "success" : "error");
      qc.invalidateQueries({ queryKey: ["azure-parts"] });
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Publish failed", "error"),
  });

  if (isLoading) return <PageSpinner />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Azure Publish</h1>
          <p className="text-sm text-slate-400">
            The only enforcement path: the blacklist is written here, and each FortiGate's own External Resource
            (Threat Feed) polls the blob URLs below. The app never writes to any firewall.
          </p>
        </div>
        {hasRole("analyst") && (
          <Button variant="primary" onClick={() => publishMutation.mutate()} loading={publishMutation.isPending}>
            <CloudUpload className="h-4 w-4" /> Publish now
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Storage settings"
            subtitle={
              config?.has_sas_url
                ? "Using a SAS URL (preferred over connection string, if both set)"
                : config?.has_connection_string
                  ? "Using a connection string"
                  : "No connection string or SAS URL set yet"
            }
          />
          <CardBody>
            <form
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                saveMutation.mutate();
              }}
            >
              <div>
                <Label htmlFor="sas-url">Container SAS URL {config?.has_sas_url && "(leave blank to keep current)"}</Label>
                <Input
                  id="sas-url"
                  type="password"
                  disabled={!hasRole("admin")}
                  value={form.sas_url}
                  onChange={(e) => setForm({ ...form, sas_url: e.target.value })}
                  placeholder="https://<account>.blob.core.windows.net/<container>?sv=...&sp=racwl&sig=..."
                />
                <p className="mt-1 text-xs text-slate-500">
                  Preferred: a container-level SAS URL with read/write/create/list permissions. Never exposes the
                  account key, and the container must already exist. Takes priority over the connection string
                  below if both are set.
                </p>
              </div>
              <div>
                <Label htmlFor="conn">Connection string {config?.has_connection_string && "(leave blank to keep current)"}</Label>
                <Input
                  id="conn"
                  type="password"
                  disabled={!hasRole("admin")}
                  value={form.connection_string}
                  onChange={(e) => setForm({ ...form, connection_string: e.target.value })}
                  placeholder="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
                />
                <p className="mt-1 text-xs text-slate-500">
                  Alternative to a SAS URL: grants full account-key access, and the app will create the container
                  automatically and generate/rotate its own per-blob read SAS tokens.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="container">Container name</Label>
                  <Input id="container" disabled={!hasRole("admin")} value={form.container_name} onChange={(e) => setForm({ ...form, container_name: e.target.value })} />
                </div>
                <div>
                  <Label htmlFor="prefix">Blob prefix</Label>
                  <Input id="prefix" disabled={!hasRole("admin")} value={form.blob_prefix} onChange={(e) => setForm({ ...form, blob_prefix: e.target.value })} />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <Label htmlFor="chunk">Chunk size</Label>
                  <Input id="chunk" type="number" disabled={!hasRole("admin")} value={form.chunk_size} onChange={(e) => setForm({ ...form, chunk_size: Number(e.target.value) })} />
                </div>
                <div>
                  <Label htmlFor="interval">Publish every (min)</Label>
                  <Input id="interval" type="number" disabled={!hasRole("admin")} value={form.publish_interval_minutes} onChange={(e) => setForm({ ...form, publish_interval_minutes: Number(e.target.value) })} />
                </div>
                <div>
                  <Label htmlFor="sas">SAS expiry (days)</Label>
                  <Input id="sas" type="number" disabled={!hasRole("admin")} value={form.sas_expiry_days} onChange={(e) => setForm({ ...form, sas_expiry_days: Number(e.target.value) })} />
                </div>
              </div>
              <div className="flex gap-4 pt-1">
                <label className="flex items-center gap-2 text-xs text-slate-400">
                  <input type="checkbox" disabled={!hasRole("admin")} checked={form.generate_sas} onChange={(e) => setForm({ ...form, generate_sas: e.target.checked })} />
                  Generate read SAS tokens for blob URLs
                </label>
                <label className="flex items-center gap-2 text-xs text-slate-400">
                  <input type="checkbox" disabled={!hasRole("admin")} checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} />
                  Publishing enabled
                </label>
              </div>
              {hasRole("admin") && (
                <Button type="submit" variant="primary" loading={saveMutation.isPending}>
                  Save settings
                </Button>
              )}
            </form>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Published blob parts" subtitle="Configure one FortiGate External Resource per URL below" />
          <CardBody className="p-0">
            {!parts || parts.length === 0 ? (
              <EmptyState title="Nothing published yet" subtitle="Save your Azure settings, enable publishing, then click Publish now." />
            ) : (
              <ul className="divide-y divide-slate-800">
                {parts.map((p) => (
                  <li key={p.part_index} className="px-4 py-3">
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-200">Part {p.part_index}</span>
                      <Badge tone="info">{p.entry_count} entries</Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <Mono>
                        <span className="break-all">{p.blob_url}</span>
                      </Mono>
                      <button
                        className="shrink-0 text-slate-400 hover:text-slate-300"
                        onClick={() => navigator.clipboard.writeText(p.blob_url)}
                        title="Copy URL"
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      Updated {formatDateTime(p.updated_at)}
                      {p.sas_expires_at && ` — SAS expires ${formatDateTime(p.sas_expires_at)}`}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
