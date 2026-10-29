import { useEffect, useState } from 'react';
import { usersAPI, bureausAPI } from '../lib/api';
import type { User, Bureau } from '../types';
import { UserPlus, Shield, User as UserIcon, Eye } from 'lucide-react';
import toast from 'react-hot-toast';
import { formatDate } from '../lib/utils';
import { PageEmptyState, PageErrorState } from '../components/PageState';

const ROLE_OPTIONS = [
  { v: 'admin',               l: 'System Administrator' },
  { v: 'supervisory_reviewer',l: 'Supervisory Reviewer' },
  { v: 'bureau_officer',      l: 'Bureau Officer' },
  { v: 'read_only',           l: 'Read-Only Official' },
];
const ROLE_BADGES: Record<string, string> = {
  admin: 'badge-critical', supervisory_reviewer: 'badge-warning',
  bureau_officer: 'badge-info', read_only: 'badge-neutral',
};

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [bureaus, setBureaus] = useState<Bureau[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ username: '', email: '', full_name: '', password: '', role: 'bureau_officer', bureau_id: '' });
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [bureauError, setBureauError] = useState(false);

  const load = () => {
    setLoading(true);
    setLoadError(false);
    usersAPI.list().then((r) => setUsers(r.data)).catch(() => { setUsers([]); setLoadError(true); }).finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    bureausAPI.list().then((r) => setBureaus(r.data)).catch(() => setBureauError(true));
  }, []);

  const createUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.username || !form.password) { toast.error('Username and password required'); return; }
    setSaving(true);
    try {
      await usersAPI.create({ ...form, bureau_id: form.bureau_id ? Number(form.bureau_id) : undefined });
      toast.success('User created');
      setShowAdd(false);
      load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Failed to create user');
    } finally { setSaving(false); }
  };

  const toggleActive = async (u: User) => {
    try {
      await usersAPI.update(u.id, { is_active: !u.is_active });
      toast.success(`User ${u.is_active ? 'deactivated' : 'activated'}`);
      load();
    } catch { toast.error('Failed to update user'); }
  };

  return (
    <div className="space-y-5">
      <div className="page-header">
        <div>
          <h1 className="page-title">User Management</h1>
          <p className="page-subtitle">{loadError ? 'User data unavailable' : loading ? 'Loading user accounts…' : `${users.length} accounts · Administrator access`}</p>
        </div>
        <button onClick={() => setShowAdd(!showAdd)} className="btn-primary">
          <UserPlus size={16} /> Add User
        </button>
      </div>

      {showAdd && (
        <div className="card border-indigo-500/30">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Create New User</h3>
          <form onSubmit={createUser} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div><label className="label">Username *</label><input className="input text-xs" aria-label="Username" autoComplete="username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></div>
            <div><label className="label">Full Name</label><input className="input text-xs" aria-label="Full name" autoComplete="name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></div>
            <div><label className="label">Email</label><input className="input text-xs" aria-label="Email address" autoComplete="email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
            <div><label className="label">Password *</label><input className="input text-xs" aria-label="Temporary password" autoComplete="new-password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></div>
            <div>
              <label className="label">Role *</label>
              <select className="select text-xs" aria-label="User role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                {ROLE_OPTIONS.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Bureau / Cell</label>
              <select className="select text-xs" aria-label="Assigned bureau" value={form.bureau_id} onChange={(e) => setForm({ ...form, bureau_id: e.target.value })}>
                <option value="">— None —</option>
                {bureaus.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </div>
            {bureauError && <p className="col-span-full text-sm text-status-danger" role="alert">Bureau options could not be loaded. Retry the page before assigning a bureau.</p>}
            <div className="col-span-2 flex gap-3">
              <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary flex-1 justify-center text-xs">Cancel</button>
              <button type="submit" disabled={saving} className="btn-primary flex-1 justify-center text-xs">{saving ? 'Creating…' : 'Create User'}</button>
            </div>
          </form>
        </div>
      )}

      {loadError ? <PageErrorState message="User records could not be loaded." onRetry={load} /> : <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Username</th>
              <th>Role</th>
              <th>Bureau</th>
              <th>Status</th>
              <th>Joined</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="text-center py-10 text-slate-500">Loading…</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-10 text-slate-600">No user accounts returned.</td></tr>
            ) : (
              users.map((u) => (
                <tr key={u.id}>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-indigo-600/30 border border-indigo-600/50 flex items-center justify-center shrink-0">
                        <span className="text-indigo-300 text-[10px] font-bold">{u.full_name?.charAt(0) ?? 'U'}</span>
                      </div>
                      <span className="text-xs font-medium text-slate-200">{u.full_name}</span>
                    </div>
                  </td>
                  <td className="font-mono text-xs">{u.username}</td>
                  <td><span className={`badge ${ROLE_BADGES[u.role] ?? 'badge-neutral'} capitalize text-[10px]`}>{u.role.replace(/_/g, ' ')}</span></td>
                  <td className="text-xs text-slate-400">{u.bureau_id ? `Bureau #${u.bureau_id}` : '—'}</td>
                  <td>
                    <span className={`badge ${u.is_active ? 'badge-success' : 'badge-neutral'}`}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="text-xs text-slate-500">{formatDate(u.created_at)}</td>
                  <td>
                    <button onClick={() => toggleActive(u)} className="btn-ghost text-xs py-1 px-2">
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>}
    </div>
  );
}
