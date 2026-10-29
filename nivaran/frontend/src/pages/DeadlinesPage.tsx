import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { deadlinesAPI } from '../lib/api';
import { formatDate, priorityBadge, priorityLabel } from '../lib/utils';
import { AlertTriangle, Clock, CheckCircle2 } from 'lucide-react';
import { PageErrorState } from '../components/PageState';

interface DeadlineItem {
  id: number; complaint_id: string; title: string; status: string;
  target_disposal_date: string; priority?: string; institution?: string;
}

export default function DeadlinesPage() {
  const [overdue, setOverdue] = useState<DeadlineItem[]>([]);
  const [upcoming, setUpcoming] = useState<DeadlineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const r = await deadlinesAPI.get();
      setOverdue(r.data.overdue);
      setUpcoming(r.data.due_within_7_days);
    } catch {
      setOverdue([]);
      setUpcoming([]);
      setError(true);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const Row = ({ item, overdue }: { item: DeadlineItem; overdue: boolean }) => (
    <Link
      to={`/complaints/${item.id}`}
      className="flex items-center gap-4 p-3 rounded-xl hover:bg-slate-800/50 transition-colors border border-transparent hover:border-slate-700/60 group"
    >
      <div className={`w-2 h-2 rounded-full shrink-0 ${overdue ? 'bg-rose-500' : 'bg-amber-400'}`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-200 truncate">{item.title}</p>
        <p className="text-[11px] text-slate-500 font-mono">{item.complaint_id}</p>
      </div>
      <div className="text-right shrink-0">
        <p className={`text-xs font-semibold ${overdue ? 'text-rose-400' : 'text-amber-400'}`}>
          {formatDate(item.target_disposal_date)}
        </p>
        {item.priority && (
          <span className={`${priorityBadge(item.priority as any)} mt-0.5`}>{priorityLabel(item.priority as any)}</span>
        )}
      </div>
    </Link>
  );

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-title">Deadlines & Alerts</h1>
          <p className="page-subtitle">{error ? 'Deadline data unavailable' : `${overdue.length} overdue · ${upcoming.length} due within 7 days`}</p>
        </div>
        <button onClick={() => void load()} disabled={loading} className="btn-secondary" aria-label="Refresh deadlines">Refresh</button>
      </div>

      {error && <PageErrorState message="Deadline data could not be loaded. The counts below are hidden until the request succeeds." onRetry={() => void load()} />}

      {/* Stats */}
      {!error && <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card bg-rose-500/10 border-rose-500/20 flex items-center gap-4">
          <AlertTriangle size={24} className="text-rose-400 shrink-0" />
          <div>
            <p className="text-2xl font-bold text-slate-100">{overdue.length}</p>
            <p className="text-xs text-slate-500">Overdue Cases</p>
          </div>
        </div>
        <div className="card bg-amber-500/10 border-amber-500/20 flex items-center gap-4">
          <Clock size={24} className="text-amber-400 shrink-0" />
          <div>
            <p className="text-2xl font-bold text-slate-100">{upcoming.length}</p>
            <p className="text-xs text-slate-500">Due in 7 Days</p>
          </div>
        </div>
        <div className="card bg-emerald-500/10 border-emerald-500/20 flex items-center gap-4">
          <CheckCircle2 size={24} className="text-emerald-400 shrink-0" />
          <div>
            <p className="text-2xl font-bold text-slate-100">{overdue.length + upcoming.length}</p>
            <p className="text-xs text-slate-500">Total Requiring Action</p>
          </div>
        </div>
      </div>}

      {!error && <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Overdue */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle size={16} className="text-rose-400" />
            <h2 className="text-sm font-semibold text-slate-300">Overdue Cases ({overdue.length})</h2>
          </div>
          {overdue.length === 0 ? (
            <p className="text-xs text-slate-500 py-4 text-center">No overdue cases. 🎉</p>
          ) : (
            <div className="space-y-0.5">
              {overdue.map((item) => <Row key={item.id} item={item} overdue={true} />)}
            </div>
          )}
        </div>

        {/* Upcoming */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Clock size={16} className="text-amber-400" />
            <h2 className="text-sm font-semibold text-slate-300">Due Within 7 Days ({upcoming.length})</h2>
          </div>
          {upcoming.length === 0 ? (
            <p className="text-xs text-slate-500 py-4 text-center">No upcoming deadlines this week.</p>
          ) : (
            <div className="space-y-0.5">
              {upcoming.map((item) => <Row key={item.id} item={item} overdue={false} />)}
            </div>
          )}
        </div>
      </div>}
    </div>
  );
}
