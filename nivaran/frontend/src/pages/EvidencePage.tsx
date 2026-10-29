import { useCallback, useEffect, useState } from 'react';
import { complaintsAPI } from '../lib/api';
import { Link } from 'react-router-dom';
import { Shield, CheckCircle2, AlertCircle, Clock, RefreshCw } from 'lucide-react';
import { formatDate } from '../lib/utils';
import toast from 'react-hot-toast';
import { PageEmptyState, PageErrorState } from '../components/PageState';

interface EvidenceItem {
  id: number;
  complaint_id: string;
  title: string;
  completeness_score?: number;
  evidence_assessment_status?: string;
  institution_name_snapshot?: string;
}

export default function EvidencePage() {
  const [complaints, setComplaints] = useState<EvidenceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [assessing, setAssessing] = useState<number | null>(null);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await complaintsAPI.list({ per_page: 50, status: undefined });
      setComplaints(res.data.items);
    } catch {
      setComplaints([]);
      setError(true);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const assess = async (id: number) => {
    setAssessing(id);
    try {
      await complaintsAPI.assess(id);
      toast.success('Assessment updated');
      load();
    } catch { toast.error('Assessment failed'); }
    finally { setAssessing(null); }
  };

  const scoreColor = (score?: number) => {
    if (!score) return 'bg-slate-700';
    if (score >= 80) return 'bg-emerald-500';
    if (score >= 50) return 'bg-amber-500';
    return 'bg-rose-500';
  };

  const statusIcon = (status?: string) => {
    if (!status) return <Clock size={13} className="text-slate-500" />;
    if (status.toLowerCase().includes('complete')) return <CheckCircle2 size={13} className="text-emerald-400" />;
    if (status.toLowerCase().includes('incomplete')) return <AlertCircle size={13} className="text-rose-400" />;
    return <Clock size={13} className="text-amber-400" />;
  };

  return (
    <div className="space-y-5">
      <div className="page-header">
        <div>
          <h1 className="page-title">Evidence Review</h1>
          <p className="page-subtitle">Complaint completeness and evidence quality assessment</p>
        </div>
        <button onClick={load} className="btn-secondary"><RefreshCw size={14} /> Refresh</button>
      </div>

      {/* Info */}
      <div className="card bg-indigo-500/5 border-indigo-500/20">
        <div className="flex items-start gap-3">
          <Shield size={16} className="text-indigo-400 shrink-0 mt-0.5" />
          <p className="text-xs text-slate-400">
            Evidence completeness is assessed using a rules-based checklist.
            Each complaint is scored on description quality, institution linkage, date consistency, document count, and required field coverage.
            Human review of assessment results is always required before action.
          </p>
        </div>
      </div>

      {error ? <PageErrorState message="Complaint evidence data could not be loaded." onRetry={() => void load()} /> : loading ? (
        <div className="text-center py-12 text-slate-500 text-sm">Loading…</div>
      ) : complaints.length === 0 ? (
        <PageEmptyState title="No complaints available for evidence review" detail="The complaint list returned no records." />
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Complaint</th>
                <th>Institution</th>
                <th>Completeness</th>
                <th>Assessment Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {complaints.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link to={`/complaints/${c.id}`} className="font-mono text-indigo-400 hover:text-indigo-300 text-xs block">
                      {c.complaint_id}
                    </Link>
                    <p className="text-xs text-slate-400 truncate max-w-48">{c.title}</p>
                  </td>
                  <td className="text-xs text-slate-400 max-w-36">
                    <span className="truncate block">{c.institution_name_snapshot ?? '—'}</span>
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-slate-800 rounded-full max-w-24">
                        <div
                          className={`h-2 rounded-full transition-all ${scoreColor(c.completeness_score)}`}
                          style={{ width: `${c.completeness_score ?? 0}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-400">{c.completeness_score?.toFixed(0) ?? '—'}%</span>
                    </div>
                  </td>
                  <td>
                    <div className="flex items-center gap-1.5">
                      {statusIcon(c.evidence_assessment_status)}
                      <span className="text-xs text-slate-400">{c.evidence_assessment_status ?? 'Not assessed'}</span>
                    </div>
                  </td>
                  <td>
                    <button
                      onClick={() => assess(c.id)}
                      disabled={assessing === c.id}
                      className="btn-secondary py-1 px-2 text-xs"
                    >
                      {assessing === c.id ? 'Assessing…' : 'Run Assessment'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
