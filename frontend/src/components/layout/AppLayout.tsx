import { NavLink, Outlet, Navigate } from "react-router-dom";
import {
  LayoutDashboard,
  Server,
  ListChecks,
  ShieldBan,
  ShieldCheck,
  Radar,
  SlidersHorizontal,
  CloudUpload,
  Users,
  ScrollText,
  LogOut,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import type { UserRole } from "@/lib/types";

interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  minRole: UserRole;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Monitoring",
    items: [
      { to: "/", label: "Dashboard", icon: LayoutDashboard, minRole: "viewer" },
      { to: "/devices", label: "Devices", icon: Server, minRole: "viewer" },
      { to: "/events", label: "Events", icon: ListChecks, minRole: "viewer" },
    ],
  },
  {
    label: "Enforcement",
    items: [
      { to: "/blacklist", label: "Blacklist", icon: ShieldBan, minRole: "viewer" },
      { to: "/allowlist", label: "Allowlist", icon: ShieldCheck, minRole: "viewer" },
      { to: "/threat-intel", label: "Threat Intel", icon: Radar, minRole: "viewer" },
      { to: "/rules", label: "Detection Rules", icon: SlidersHorizontal, minRole: "viewer" },
      { to: "/azure-publish", label: "Azure Publish", icon: CloudUpload, minRole: "viewer" },
    ],
  },
  {
    label: "Admin",
    items: [
      { to: "/users", label: "Users", icon: Users, minRole: "admin" },
      { to: "/audit-log", label: "Audit Log", icon: ScrollText, minRole: "admin" },
    ],
  },
];

export function AppLayout() {
  const { user, loading, hasRole, logout } = useAuth();

  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <aside className="flex w-60 shrink-0 flex-col border-r border-slate-800 bg-slate-950">
        <div className="flex items-center gap-2 px-4 py-4">
          <ShieldBan className="h-5 w-5 text-brand-400" />
          <span className="text-sm font-semibold tracking-tight text-slate-100">IP Blacklister</span>
        </div>
        <nav className="flex-1 space-y-4 overflow-y-auto px-2 pt-1">
          {NAV_GROUPS.map((group) => {
            const items = group.items.filter((item) => hasRole(item.minRole));
            if (items.length === 0) return null;
            return (
              <div key={group.label}>
                <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                  {group.label}
                </p>
                <div className="space-y-0.5">
                  {items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.to === "/"}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500",
                          isActive
                            ? "bg-brand-600/15 text-brand-300"
                            : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                        )
                      }
                    >
                      <item.icon className="h-4 w-4" />
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}
        </nav>
        <div className="border-t border-slate-800 px-3 py-3">
          <div className="mb-2 truncate text-xs text-slate-400">
            <span className="text-slate-300">{user.full_name || user.email}</span>
            <br />
            <span className="uppercase tracking-wide">{user.role}</span>
          </div>
          <button
            onClick={logout}
            className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs text-slate-400 hover:bg-slate-900 hover:text-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto bg-slate-950">
        <div className="mx-auto max-w-7xl px-6 py-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
