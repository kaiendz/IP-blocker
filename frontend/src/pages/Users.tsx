import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { UserOut, UserRole } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Label, Select } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Badge } from "@/components/ui/Badge";
import { EmptyState, PageSpinner } from "@/components/ui/Misc";
import { SortHeader, toggleSort, type SortState } from "@/components/ui/SortHeader";
import { formatDateTime, relativeTime } from "@/lib/utils";

const ROLE_TONE: Record<UserRole, "danger" | "info" | "neutral"> = {
  admin: "danger",
  analyst: "info",
  viewer: "neutral",
};

type SortKey = "email" | "full_name" | "role" | "last_login_at" | "created_at";

function sortUsers(users: UserOut[], sort: SortState<SortKey>): UserOut[] {
  const dir = sort.dir === "asc" ? 1 : -1;
  return [...users].sort((a, b) => {
    const av = String(a[sort.key] ?? "");
    const bv = String(b[sort.key] ?? "");
    if (av < bv) return -1 * dir;
    if (av > bv) return 1 * dir;
    return 0;
  });
}

export function UsersPage() {
  const { user: me } = useAuth();
  const toast = useToast();
  const confirm = useConfirm();
  const qc = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [sort, setSort] = useState<SortState<SortKey>>({ key: "email", dir: "asc" });

  const { data, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.get<UserOut[]>("/users"),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => api.patch(`/users/${id}`, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: UserRole }) => api.patch(`/users/${id}`, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/users/${id}`),
    onSuccess: () => {
      toast.push("User deleted");
      qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Failed to delete", "error"),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Users</h1>
          <p className="text-sm text-slate-400">Admin / Analyst / Viewer role-based access control.</p>
        </div>
        <Button variant="primary" onClick={() => setAddOpen(true)}>
          <Plus className="h-4 w-4" /> Add user
        </Button>
      </div>

      <Card>
        {isLoading ? (
          <PageSpinner />
        ) : !data || data.length === 0 ? (
          <EmptyState title="No users" />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-400">
                <SortHeader label="Email" sortKey="email" sort={sort} onSort={(k) => setSort((p) => toggleSort(p, k))} />
                <SortHeader label="Name" sortKey="full_name" sort={sort} onSort={(k) => setSort((p) => toggleSort(p, k))} />
                <SortHeader label="Role" sortKey="role" sort={sort} onSort={(k) => setSort((p) => toggleSort(p, k))} />
                <th className="px-4 py-2">Active</th>
                <SortHeader
                  label="Last login"
                  sortKey="last_login_at"
                  sort={sort}
                  onSort={(k) => setSort((p) => toggleSort(p, k))}
                />
                <SortHeader
                  label="Created"
                  sortKey="created_at"
                  sort={sort}
                  onSort={(k) => setSort((p) => toggleSort(p, k))}
                />
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortUsers(data, sort).map((u) => (
                <tr key={u.id} className="border-b border-slate-800/60 last:border-0">
                  <td className="px-4 py-2 text-slate-200">{u.email}</td>
                  <td className="px-4 py-2 text-slate-400">{u.full_name || "—"}</td>
                  <td className="px-4 py-2">
                    <Select
                      value={u.role}
                      disabled={u.id === me?.id}
                      onChange={(e) => roleMutation.mutate({ id: u.id, role: e.target.value as UserRole })}
                      className="w-28 py-1 text-xs"
                    >
                      <option value="admin">admin</option>
                      <option value="analyst">analyst</option>
                      <option value="viewer">viewer</option>
                    </Select>
                  </td>
                  <td className="px-4 py-2">
                    <button disabled={u.id === me?.id} onClick={() => toggleActiveMutation.mutate({ id: u.id, is_active: !u.is_active })}>
                      <Badge tone={u.is_active ? "success" : "neutral"}>{u.is_active ? "active" : "disabled"}</Badge>
                    </button>
                  </td>
                  <td className="px-4 py-2 text-slate-400">{relativeTime(u.last_login_at)}</td>
                  <td className="px-4 py-2 text-slate-400">{formatDateTime(u.created_at)}</td>
                  <td className="px-4 py-2 text-right">
                    {u.id !== me?.id && (
                      <Button
                        size="sm"
                        variant="ghost"
                        aria-label={`Delete user ${u.email}`}
                        title="Delete"
                        onClick={async () => {
                          const ok = await confirm({
                            title: "Delete this user?",
                            description: `${u.email} will immediately lose access — this can't be undone.`,
                            confirmLabel: "Delete user",
                            danger: true,
                          });
                          if (ok) deleteMutation.mutate(u.id);
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5 text-red-400" />
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {addOpen && <AddUserModal onClose={() => setAddOpen(false)} />}
    </div>
  );
}

function AddUserModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "viewer" as UserRole });

  const mutation = useMutation({
    mutationFn: () => api.post("/users", form),
    onSuccess: () => {
      toast.push("User created");
      qc.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
    onError: (e) => toast.push(e instanceof ApiError ? e.message : "Failed to create user", "error"),
  });

  return (
    <Modal open onClose={onClose} title="Add user">
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <div>
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div>
          <Label htmlFor="name">Full name</Label>
          <Input id="name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        </div>
        <div>
          <Label htmlFor="password">Temporary password</Label>
          <Input id="password" type="password" required minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </div>
        <div>
          <Label htmlFor="role">Role</Label>
          <Select id="role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}>
            <option value="viewer">Viewer — read only</option>
            <option value="analyst">Analyst — manage blacklist/rules/devices</option>
            <option value="admin">Admin — full access incl. users</option>
          </Select>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>
            Create user
          </Button>
        </div>
      </form>
    </Modal>
  );
}
