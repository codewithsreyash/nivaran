import { useEffect, useState, useCallback } from 'react';
import { auditAPI } from '../lib/api';
import type { AuditLog } from '../types';
import { formatDateTime } from '../lib/utils';
import { ClipboardList, Search } from 'lucide-react';
import { PageErrorState } from '../components/PageState';

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [resource, setResource] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await auditAPI.list({
        page, per_page: 30,
        resource_type: resource || undefined,
      });
      setLogs(res.data.items);
      setTotal(res.data.total);
      setPages(res.data.pages);
    } catch {
      setLogs([]);
      setTotal(0);
      setPages(1);
      setError(true);
    } finally { setLoading(false); }
  }, [page, resource]);

  useEffect(() => { load(); }, [load]);

  const actionColor: Record<string, string> = {
    'complaint': 'text-indigo-400',
    'user': 'text-emerald-400',
    'overlap': 'text-violet-400',
    'institution': 'text-amber-400',
  };

  return (
    <div className="space-y-5">
      <div className="page-header">
        <div>
          <h1 className="page-title">Audit History</h1>
          <p className="page-subtitle">{error ? 'Audit data unavailable' : loading ? 'Loading audit records…' : `${total} records · Action history`}</p>
        </div>
      </div>

      <div className="card flex gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            className="input pl-9 text-xs"
            aria-label="Filter audit records by resource type"
            placeholder="Filter by resource type (complaint, user, overlap, institution)…"
            value={resource}
            onChange={(e) => { setResource(e.target.value); setPage(1); }}
          />
        </div>
      </div>

      {error ? <PageErrorState message="Audit records could not be loaded." onRetry={() => void load()} /> : <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>User</th>
              <th>Action</th>
              <th>Resource Type</th>
              <th>Resource ID</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center py-10 text-slate-500">Loading…</td></tr>
            ) : logs.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-10 text-slate-500">No audit records found</td></tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id}>
                  <td className="text-[11px] text-slate-500 whitespace-nowrap">{formatDateTime(log.created_at)}</td>
                  <td className="text-xs text-slate-300">{log.user?.full_name ?? `#${log.user_id ?? '—'}`}</td>
                  <td>
                    <span className={`text-xs font-mono ${actionColor[log.resource_type ?? ''] ?? 'text-slate-400'}`}>
                      {log.action}
                    </span>
                  </td>
                  <td className="text-xs text-slate-500 capitalize">{log.resource_type ?? '—'}</td>
                  <td className="text-xs font-mono text-slate-500">{log.resource_id ?? '—'}</td>
                  <td>
                    {log.details && Object.keys(log.details).length > 0 ? (
                      <span className="text-[11px] text-slate-500 font-mono">
                        {JSON.stringify(log.details).slice(0, 50)}
                      </span>
                    ) : '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>}

      {pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-500">{total} total records</p>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="btn-secondary text-xs py-1.5 px-3">← Prev</button>
            <span className="text-xs text-slate-400 self-center">{page} / {pages}</span>
            <button disabled={page >= pages} onClick={() => setPage(page + 1)} className="btn-secondary text-xs py-1.5 px-3">Next →</button>
          </div>
        </div>
      )}
    </div>
  );
}
