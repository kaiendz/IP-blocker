import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import type { DashboardStats } from "@/lib/types";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { PageSpinner, StatTile, Mono } from "@/components/ui/Misc";

const REASON_COLORS: Record<string, string> = {
  brute_force: "#f87171",
  threat_intel: "#f59e0b",
  manual: "#38bdf8",
};

export function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => api.get<DashboardStats>("/dashboard/stats"),
    refetchInterval: 30_000,
  });

  if (isLoading || !data) return <PageSpinner />;

  const reasonData = Object.entries(data.blacklist_by_reason).map(([reason, count]) => ({ reason, count }));
  const offendersData = data.top_offenders_last_24h.slice(0, 8);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Dashboard</h1>
        <p className="text-sm text-slate-400">Live overview of brute-force detection and blacklist enforcement.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatTile label="Active blacklist" value={data.active_blacklist_count} />
        <StatTile
          label="Devices"
          value={`${data.devices_healthy}/${data.devices_total}`}
          hint="reporting healthy on last poll"
        />
        <StatTile label="Failed logins (24h)" value={data.events_last_24h} />
        <StatTile
          label="Published to Azure"
          value={data.published_entries}
          hint={`${data.published_parts} blob part(s)`}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Active blacklist by reason" />
          <CardBody>
            {reasonData.length === 0 ? (
              <p className="py-10 text-center text-sm text-slate-400">No active blacklist entries yet</p>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={reasonData} dataKey="count" nameKey="reason" innerRadius={50} outerRadius={80} paddingAngle={3}>
                    {reasonData.map((d) => (
                      <Cell key={d.reason} fill={REASON_COLORS[d.reason] ?? "#64748b"} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            )}
            <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-400">
              {reasonData.map((d) => (
                <span key={d.reason} className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full" style={{ background: REASON_COLORS[d.reason] ?? "#64748b" }} />
                  {d.reason.replace("_", " ")} ({d.count})
                </span>
              ))}
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Top offending IPs (24h)" subtitle="Failed SSL VPN / IKE / admin logins" />
          <CardBody>
            {offendersData.length === 0 ? (
              <p className="py-10 text-center text-sm text-slate-400">No failed logins recorded yet</p>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={offendersData} layout="vertical" margin={{ left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                  <XAxis type="number" stroke="#64748b" fontSize={11} allowDecimals={false} />
                  <YAxis type="category" dataKey="src_ip" stroke="#64748b" fontSize={11} width={100} />
                  <Tooltip
                    contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 12 }}
                    cursor={{ fill: "#1e293b55" }}
                  />
                  <Bar dataKey="fail_count" fill="#f87171" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader title="Top offending IPs — detail" />
        <CardBody className="p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-4 py-2">Source IP</th>
                <th className="px-4 py-2">Failed attempts (24h)</th>
              </tr>
            </thead>
            <tbody>
              {offendersData.map((o) => (
                <tr key={o.src_ip} className="border-b border-slate-800/60 last:border-0">
                  <td className="px-4 py-2">
                    <Mono>{o.src_ip}</Mono>
                  </td>
                  <td className="px-4 py-2 text-slate-300">{o.fail_count}</td>
                </tr>
              ))}
              {offendersData.length === 0 && (
                <tr>
                  <td colSpan={2} className="px-4 py-6 text-center text-slate-400">
                    Nothing to show yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardBody>
      </Card>
    </div>
  );
}
