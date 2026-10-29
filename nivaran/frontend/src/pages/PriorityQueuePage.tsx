import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { priorityAPI } from '../lib/api';
import { priorityBadge, priorityLabel, statusLabel, formatDate } from '../lib/utils';
import { AlertTriangle } from 'lucide-react';
import { PageErrorState, PageEmptyState } from '../components/PageState';

interface QueueItem {
  id: number; complaint_id: string; title: string; category: string;
  status: string; institution_name?: string; bureau?: string; officer?: string;
  target_disposal_date?: string; is_overdue: boolean;
  days_since_last_action?: number; calculated_priority_score?: number;
  calculated_priority_level?: string; assigned_priority_level?: string;
  priority_explanation?: string; next_required_action?: string;
}

export default function PriorityQueuePage() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await priorityAPI.queue({ per_page: 50, min_level: filter || undefined });
      setItems(res.data.items);
      setTotal(res.data.total);
    } catch {
      setItems([]);
      setError(true);
    } finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const effectiveLevel = (item: QueueItem) => (item.assigned_priority_level ?? item.calculated_priority_level) as any;

  return (
    <div className="space-y-5">
      <div className="page-header">
        <div>
          <h1 className="page-title">Priority Queue</h1>
          <p className="page-subtitle">{error ? 'Queue data unavailable' : loading ? 'Loading priority queue…' : `${total} active cases sorted by urgency`}</p>
        </div>
        <div className="flex gap-2">
          {['', 'critical', 'high'].map((l) => (
            <button
              key={l}
              onClick={() => setFilter(l)}
              className={filter === l ? 'btn-primary text-xs' : 'btn-secondary text-xs'}
              aria-pressed={filter === l}
            >
              {l === '' ? 'All priorities' : l === 'critical' ? 'Critical' : 'High and above'}
            </button>
          ))}
        </div>
      </div>

      {/* Queue items */}
      <div className="space-y-2">
        {error ? <PageErrorState message="Priority queue data could not be loaded." onRetry={() => void load()} /> : loading ? (
          <div className="text-center py-12 text-slate-500 text-sm">Loading queue…</div>
        ) : items.length === 0 ? (
          <PageEmptyState title="No cases in this queue" detail="Try another priority filter or return when new cases are available." />
        ) : (
          items.map((item) => {
            const level = effectiveLevel(item);
            return (
              <Link
                key={item.id}
                to={`/complaints/${item.id}`}
                className="card flex items-start gap-4 hover:border-slate-700 transition-colors block"
              >
                <div className="flex flex-col items-center gap-1 shrink-0">
                  <span className={priorityBadge(level)}>{priorityLabel(level)}</span>
                  {item.calculated_priority_score !== undefined && (
                    <span className="text-[11px] text-slate-600 font-mono">{item.calculated_priority_score.toFixed(0)}/100</span>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium text-slate-200 truncate">{item.title}</p>
                      <p className="text-xs text-slate-500 font-mono">{item.complaint_id}</p>
                    </div>
                    <div className="text-right shrink-0">
                      {item.target_disposal_date && (
                        <p className={`text-xs ${item.is_overdue ? 'text-rose-400' : 'text-slate-400'}`}>
                          {item.is_overdue && <span>⚠ </span>}
                          {formatDate(item.target_disposal_date)}
                        </p>
                      )}
                      {item.days_since_last_action !== null && item.days_since_last_action !== undefined && (
                        <p className="text-[11px] text-slate-600 mt-0.5">{item.days_since_last_action}d since action</p>
                      )}
                    </div>
                  </div>
                  {item.priority_explanation && (
                    <p className="text-xs text-slate-500 mt-1.5 line-clamp-2">{item.priority_explanation}</p>
                  )}
                  <div className="flex items-center gap-3 mt-2 flex-wrap">
                    <span className="text-[11px] text-slate-600">{item.status.replace(/_/g, ' ')}</span>
                    {item.bureau && <span className="text-[11px] text-slate-600">· {item.bureau}</span>}
                    {item.institution_name && <span className="text-[11px] text-slate-600">· {item.institution_name}</span>}
                    {item.next_required_action && (
                      <span className="text-[11px] text-indigo-400">→ {item.next_required_action}</span>
                    )}
                  </div>
                </div>
              </Link>
            );
          })
        )}
      </div>
    </div>
  );
}
