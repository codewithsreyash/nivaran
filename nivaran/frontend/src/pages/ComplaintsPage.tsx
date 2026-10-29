import { useEffect, useState, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { complaintsAPI, bureausAPI } from '../lib/api';
import type { ComplaintListItem, Bureau, PriorityLevel } from '../types';
import {
  priorityBadge, priorityLabel, statusBadge, statusLabel,
  categoryLabel, formatDate, isOverdue, daysUntil
} from '../lib/utils';
import {
  Plus, Search, ChevronLeft, ChevronRight,
  AlertTriangle, List, LayoutGrid
} from 'lucide-react';
import CreateComplaintModal from '../components/CreateComplaintModal';
import { useAuth } from '../contexts/AuthContext';
import { PageEmptyState, PageErrorState } from '../components/PageState';

const STATUS_OPTIONS = [
  'registered','under_initial_review','under_process',
  'awaiting_information','transferred','escalated','disposed','closed'
];
const CATEGORY_OPTIONS = [
  'scholarship_financial','academic_examination','faculty_related',
  'infrastructure_facilities','regulatory_compliance','approval_related',
  'student_safety_welfare','administrative','other'
];

export default function ComplaintsPage() {
  const [params, setParams] = useSearchParams();
  const { canWrite } = useAuth();
  const [complaints, setComplaints] = useState<ComplaintListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [bureaus, setBureaus] = useState<Bureau[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');
  const [loadError, setLoadError] = useState(false);
  const [bureauLoadError, setBureauLoadError] = useState(false);

  const page = Number(params.get('page') ?? 1);
  const search = params.get('search') ?? '';
  const status = params.get('status') ?? '';
  const category = params.get('category') ?? '';
  const priority = params.get('priority') ?? '';

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const res = await complaintsAPI.list({
        page, per_page: 20, search: search || undefined,
        status: status || undefined, category: category || undefined, priority: priority || undefined,
        sort_by: 'registration_date', sort_desc: true,
      });
      setComplaints(res.data.items);
      setTotal(res.data.total);
      setPages(res.data.pages);
    } catch {
      setComplaints([]);
      setTotal(0);
      setPages(1);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [page, search, status, category, priority]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    bureausAPI.list().then((r) => setBureaus(r.data)).catch(() => setBureauLoadError(true));
  }, []);

  const setParam = (key: string, val: string) => {
    const next = new URLSearchParams(params);
    if (val) next.set(key, val); else next.delete(key);
    next.delete('page');
    setParams(next);
  };

  const effectivePriority = (c: ComplaintListItem) => c.assigned_priority_level ?? c.calculated_priority_level;
  const assignmentSummary = (c: ComplaintListItem) => {
    const bureauName = bureaus.find((bureau) => bureau.id === c.bureau_id)?.name;
    const bureau = c.bureau_id == null ? 'Unassigned bureau' : bureauName ?? `Bureau #${c.bureau_id}`;
    const officer = c.assigned_officer_id == null ? 'No officer assigned' : `Officer #${c.assigned_officer_id}`;
    return `${bureau} · ${officer}`;
  };

  return (
    <div className="space-y-5">
      <div className="page-header">
        <div>
          <h1 className="page-title">Complaint Management</h1>
          <p className="page-subtitle">{loadError ? 'Complaint data unavailable' : loading ? 'Loading complaint records…' : `${total} complaints · Records are scoped to your account`}</p>
        </div>
        <div className="flex items-center gap-2">
          {/* View mode toggle */}
          <div className="flex items-center gap-1 bg-slate-800 rounded-lg p-1">
            <button
              onClick={() => setViewMode('table')}
              className={`p-1.5 rounded transition-colors ${viewMode === 'table' ? 'bg-slate-700 text-slate-100' : 'text-slate-500 hover:text-slate-300'}`}
              title="Table view" aria-label="Table view" aria-pressed={viewMode === 'table'}
            >
              <List size={14} />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded transition-colors ${viewMode === 'grid' ? 'bg-slate-700 text-slate-100' : 'text-slate-500 hover:text-slate-300'}`}
              title="Card view" aria-label="Card view" aria-pressed={viewMode === 'grid'}
            >
              <LayoutGrid size={14} />
            </button>
          </div>
          {canWrite && (
            <button onClick={() => setShowCreate(true)} className="btn-primary">
              <Plus size={16} /> Register Complaint
            </button>
          )}
        </div>
      </div>

      {bureauLoadError && <p className="text-sm text-status-warning" role="status">Bureau options are unavailable; complaint registration may be limited.</p>}

      {/* Filters */}
      <div className="card flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            className="input pl-9"
            aria-label="Search complaints by reference, title, or institution"
            placeholder="Search complaints, ID, institution…"
            value={search}
            onChange={(e) => setParam('search', e.target.value)}
          />
        </div>
        <select className="select w-44" aria-label="Filter by status" value={status} onChange={(e) => setParam('status', e.target.value)}>
          <option value="">All Statuses</option>
          {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
        </select>
        <select className="select w-52" aria-label="Filter by category" value={category} onChange={(e) => setParam('category', e.target.value)}>
          <option value="">All Categories</option>
          {CATEGORY_OPTIONS.map((c) => <option key={c} value={c}>{categoryLabel(c as any)}</option>)}
        </select>
        <select className="select w-40" value={priority} aria-label="Filter by priority" onChange={(e) => setParam('priority', e.target.value)}>
          <option value="">All Priorities</option>
          {(['critical', 'high', 'medium', 'low'] as PriorityLevel[]).map((level) => <option key={level} value={level}>{priorityLabel(level)}</option>)}
        </select>
      </div>

      {/* Content: Grid or Table */}
      {loadError ? (
        <PageErrorState message="Complaint records could not be loaded. Existing filters are preserved so you can retry." onRetry={() => void load()} />
      ) : loading ? (
        viewMode === 'grid' ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="card">
                <div className="skeleton h-3 w-20 mb-3" />
                <div className="skeleton h-4 w-full mb-1" />
                <div className="skeleton h-4 w-3/4 mb-3" />
                <div className="skeleton h-3 w-28" />
              </div>
            ))}
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Complaint ID</th><th>Title</th><th>Category</th>
                  <th>Status</th><th>Priority</th><th>Institution</th>
                  <th>Bureau / Officer</th><th>Deadline</th><th>Registered</th>
                </tr>
              </thead>
              <tbody>
                <tr><td colSpan={9} className="text-center py-12 text-slate-500">Loading…</td></tr>
              </tbody>
            </table>
          </div>
        )
      ) : complaints.length === 0 ? (
        <PageEmptyState title="No complaints found" detail="Try adjusting the search or filters." />
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {complaints.map((c) => {
            const p = effectivePriority(c);
            const overdue = isOverdue(c.target_disposal_date, c.status);
            const borderColor =
              p === 'critical' ? 'border-rose-500' :
              p === 'high'     ? 'border-orange-500' :
              p === 'medium'   ? 'border-yellow-500' :
              'border-slate-700';
            return (
              <Link
                key={c.id}
                to={`/complaints/${c.id}`}
                className={`card border-l-4 ${borderColor} cursor-pointer hover:scale-[1.02] transition-all duration-200 hover:shadow-lg hover:shadow-black/30`}
              >
                <div className="flex items-start justify-between mb-2">
                  <span className="font-mono text-xs text-indigo-400">{c.complaint_id}</span>
                  <span className={priorityBadge(p)}>{priorityLabel(p)}</span>
                </div>
                <p className="text-sm font-medium text-slate-200 line-clamp-2 mb-2">{c.title}</p>
                <p className="text-xs text-slate-500 truncate mb-3">{c.institution_name_snapshot ?? '—'}</p>
                <p className="text-xs text-slate-600 mb-3">{assignmentSummary(c)}</p>
                <div className="flex items-center justify-between">
                  <span className={statusBadge(c.status)}>{statusLabel(c.status)}</span>
                  {c.target_disposal_date && (
                    <span className={`text-xs font-medium ${overdue ? 'text-rose-400' : 'text-slate-500'}`}>
                      {overdue ? '⚠ Overdue' : formatDate(c.target_disposal_date)}
                    </span>
                  )}
                </div>
              </Link>
            );
          })}
        </div>
      ) : (
        /* Table view */
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Complaint ID</th><th>Title</th><th>Category</th><th>Status</th>
                <th>Priority</th><th>Institution</th><th>Bureau / Officer</th><th>Deadline</th><th>Registered</th>
              </tr>
            </thead>
            <tbody>
              {complaints.map((c) => {
                const overdue = isOverdue(c.target_disposal_date, c.status);
                const days = daysUntil(c.target_disposal_date);
                return (
                  <tr key={c.id}>
                    <td>
                      <Link to={`/complaints/${c.id}`} className="font-mono text-indigo-400 hover:text-indigo-300 text-xs" onClick={(e) => e.stopPropagation()}>
                        {c.complaint_id}
                      </Link>
                    </td>
                    <td className="max-w-xs">
                      <Link to={`/complaints/${c.id}`} className="truncate block font-medium text-slate-800 text-sm hover:text-blue-800">{c.title || 'Untitled complaint'}</Link>
                    </td>
                    <td><span className="badge badge-neutral text-[10px]">{categoryLabel(c.category)}</span></td>
                    <td><span className={statusBadge(c.status)}>{statusLabel(c.status)}</span></td>
                    <td>
                      <span className={priorityBadge(effectivePriority(c))}>
                        {priorityLabel(effectivePriority(c))}
                      </span>
                    </td>
                    <td className="text-xs max-w-36">
                      <span className="truncate block">{c.institution_name_snapshot ?? '—'}</span>
                    </td>
                    <td className="text-xs">{assignmentSummary(c)}</td>
                    <td>
                      {c.target_disposal_date ? (
                        <span className={`flex items-center gap-1 text-xs ${overdue ? 'text-rose-400' : days !== null && days <= 3 ? 'text-amber-400' : 'text-slate-400'}`}>
                          {overdue && <AlertTriangle size={11} />}
                          {formatDate(c.target_disposal_date)}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="text-xs text-slate-500">{formatDate(c.registration_date)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {!loadError && pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-500">Showing {complaints.length} of {total}</p>
          <div className="flex items-center gap-2">
            <button disabled={page <= 1} onClick={() => setParam('page', String(page - 1))} className="btn-secondary py-1.5 px-3 text-xs">
              <ChevronLeft size={14} /> Prev
            </button>
            <span className="text-xs text-slate-400">{page} / {pages}</span>
            <button disabled={page >= pages} onClick={() => setParam('page', String(page + 1))} className="btn-secondary py-1.5 px-3 text-xs">
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {showCreate && (
        <CreateComplaintModal
          bureaus={bureaus}
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); void load(); }}
        />
      )}
    </div>
  );
}
