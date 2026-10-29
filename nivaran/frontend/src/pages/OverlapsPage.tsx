import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { overlapsAPI } from '../lib/api';
import { PageEmptyState, PageErrorState } from '../components/PageState';
import type { OverlapResult } from '../types';
import { categoryLabel, formatDate, statusLabel } from '../lib/utils';
import { GitMerge, CheckCircle2, XCircle, AlertTriangle, ChevronRight, Info } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';

const DECISION_OPTIONS = [
  { value: 'confirmed_duplicate',   label: 'Confirmed Duplicate',       cls: 'btn-danger' },
  { value: 'related_independent',   label: 'Related but Independent',   cls: 'btn-secondary' },
  { value: 'unrelated',             label: 'Unrelated',                 cls: 'btn-secondary' },
  { value: 'deferred',              label: 'Defer Review',              cls: 'btn-ghost' },
  { value: 'escalated_for_review',  label: 'Escalate',                  cls: 'btn-secondary' },
];

function ScoreBar({ label, value, max = 35, color = 'bg-indigo-500' }: { label: string; value?: number; max?: number; color?: string }) {
  const pct = value !== undefined ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-[11px] mb-0.5">
        <span className="text-slate-500">{label}</span>
        <span className="text-slate-400">{value?.toFixed(1) ?? '—'} / {max}</span>
      </div>
      <div className="h-1.5 bg-slate-800 rounded-full">
        <div className={`h-1.5 ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function OverlapCard({ result, onDecision }: { result: OverlapResult; onDecision: () => void }) {
  const { canWrite, isAdmin, isReviewer } = useAuth();
  const [reason, setReason] = useState('');
  const [deciding, setDeciding] = useState(false);
  const [showDecide, setShowDecide] = useState(false);
  const canDecide = canWrite && (isAdmin || isReviewer);

  const decide = async (decision: string) => {
    if (!reason.trim()) { toast.error('Please provide a reason for your decision'); return; }
    setDeciding(true);
    try {
      await overlapsAPI.decision(result.id, { decision, reason });
      toast.success('Decision recorded');
      onDecision();
    } catch { toast.error('Failed to record decision'); }
    finally { setDeciding(false); }
  };

  const score = result.similarity_score;
  const scoreColor = score >= 70 ? 'text-rose-400' : score >= 45 ? 'text-amber-400' : 'text-slate-400';

  return (
    <div className="card space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className={`text-2xl font-bold font-mono ${scoreColor}`}>
            {score.toFixed(0)} / 100
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-200">Similarity Score (0–100)</p>
            <p className="text-[11px] text-slate-400">
              Detector: Rules-based (RapidFuzz baseline) · Algorithm: {result.algorithm_version}
            </p>
            <p className="text-[10px] text-slate-500">Heuristic similarity metric — not a duplicate probability</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {result.review_status === 'reviewed' ? (
            <span className="badge badge-success flex items-center gap-1"><CheckCircle2 size={10} /> Reviewed</span>
          ) : (
            <span className="badge badge-warning">Pending Review</span>
          )}
        </div>
      </div>

      {/* Score breakdown */}
      <div className="grid grid-cols-2 gap-2 p-3 bg-slate-800/40 rounded-lg">
        <ScoreBar label="Institution Match" value={result.institution_score} max={30} color="bg-violet-500" />
        <ScoreBar label="Description Similarity" value={result.description_score} max={35} color="bg-indigo-500" />
        <ScoreBar label="Category Match" value={result.category_score} max={15} color="bg-sky-500" />
        <ScoreBar label="Date Proximity" value={result.date_score} max={10} color="bg-emerald-500" />
        <ScoreBar label="Keyword Overlap" value={result.keyword_score} max={10} color="bg-amber-500" />
      </div>

      {/* Keywords */}
      {result.matching_keywords && result.matching_keywords.length > 0 && (
        <div>
          <p className="text-[11px] text-slate-500 mb-1.5">Shared keywords:</p>
          <div className="flex flex-wrap gap-1.5">
            {result.matching_keywords.map((kw) => (
              <span key={kw} className="px-2 py-0.5 rounded-md bg-indigo-500/20 text-indigo-300 text-[11px] border border-indigo-500/30">{kw}</span>
            ))}
          </div>
        </div>
      )}

      {/* Conflicts & missing */}
      {(result.conflicting_info || result.missing_data_notes) && (
        <div className="space-y-1.5">
          {result.conflicting_info && (
            <div className="flex items-start gap-2 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20">
              <AlertTriangle size={12} className="text-rose-400 shrink-0 mt-0.5" />
              <p className="text-[11px] text-rose-300">{result.conflicting_info}</p>
            </div>
          )}
          {result.missing_data_notes && (
            <div className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <Info size={12} className="text-amber-400 shrink-0 mt-0.5" />
              <p className="text-[11px] text-amber-300">{result.missing_data_notes}</p>
            </div>
          )}
        </div>
      )}

      {/* Complaint links & comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {[
          { label: 'Primary Complaint', c: result.primary_complaint },
          { label: 'Candidate Complaint', c: result.candidate_complaint },
        ].map(({ label, c }) => (
          <div key={label} className="p-3 rounded-lg bg-slate-800/60 border border-slate-700/60 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">{label}</span>
                {c?.category && (
                  <span className="badge badge-indigo text-[10px]">{categoryLabel(c.category)}</span>
                )}
              </div>
              {c ? (
                <>
                  <p className="text-xs text-slate-200 font-medium line-clamp-2">{c.title}</p>
                  <div className="mt-2 space-y-0.5 text-[11px] text-slate-400">
                    <p><span className="text-slate-500">ID:</span> <span className="font-mono text-slate-300">{c.complaint_id}</span></p>
                    <p className="truncate"><span className="text-slate-500">Institution:</span> {c.institution_name_snapshot || '—'}</p>
                  </div>
                </>
              ) : <p className="text-xs text-slate-500">—</p>}
            </div>
            {c && (
              <div className="mt-2.5 pt-2 border-t border-slate-700/40">
                <Link to={`/complaints/${c.id}`} className="text-[11px] text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1">
                  View Complaint Details <ChevronRight size={11} />
                </Link>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Existing decision */}
      {result.decision && (
        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
          <p className="text-xs font-semibold text-emerald-400 mb-1">Recorded Decision: {result.decision.replace(/_/g, ' ')}</p>
          <p className="text-[11px] text-emerald-300">{result.decision_reason}</p>
          <p className="text-[10px] text-emerald-700 mt-1">{formatDate(result.decided_at)}</p>
        </div>
      )}

      {/* Decision panel */}
      {canDecide && result.review_status === 'pending' && (
        <div className="pt-3 border-t border-slate-800 space-y-2">
          <p className="text-xs font-medium text-slate-400 mb-2">Record Decision (reason required — never automatic)</p>
          <textarea
            className="input text-xs h-16 resize-none"
            aria-label="Reason for overlap decision"
            placeholder="Reason for your decision…"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            {DECISION_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                className={`${opt.cls} text-xs py-1.5`}
                disabled={deciding}
                onClick={() => decide(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-slate-600">Complaints are never automatically merged or disposed based on similarity score alone.</p>
        </div>
      )}
    </div>
  );
}

export default function OverlapsPage() {
  const [results, setResults] = useState<OverlapResult[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState('pending');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await overlapsAPI.list({ review_status: filter || undefined, per_page: 50 });
      setResults(res.data.items);
      setTotal(res.data.total);
    } catch {
      setResults([]);
      setTotal(0);
      setError(true);
    } finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-5">
      <div className="page-header">
        <div>
          <h1 className="page-title">Overlap Detection</h1>
          <p className="page-subtitle">{error ? 'Overlap data unavailable' : loading ? 'Loading potential matches…' : `${total} potential matches · Similarity scores are review signals and require human review.`}</p>
        </div>
        <div className="flex gap-2">
          {[
            { v: 'pending', l: 'Pending Review' },
            { v: 'reviewed', l: 'Reviewed' },
            { v: '', l: 'All' },
          ].map(({ v, l }) => (
            <button key={v} onClick={() => setFilter(v)} aria-pressed={filter === v} className={filter === v ? 'btn-primary text-xs' : 'btn-secondary text-xs'}>{l}</button>
          ))}
        </div>
      </div>

      {/* Explainability notice */}
      <div className="card bg-indigo-500/5 border-indigo-500/20">
        <div className="flex items-start gap-3">
          <GitMerge size={16} className="text-indigo-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="text-sm font-semibold text-blue-900">Rules-based similarity review</p>
            <p className="text-sm text-slate-600 leading-relaxed">
              Similarity scores compare complaint attributes and help reviewers find possible relationships. A score is not a duplicate probability, a verified ML prediction, or a decision.
            </p>
            <p className="text-xs text-amber-900 font-medium">
              Reviewers make and record the decision. The system does not automatically merge or dispose of complaints based on similarity.
            </p>
          </div>
        </div>
      </div>

      {error ? <PageErrorState message="Overlap results could not be loaded." onRetry={() => void load()} /> : loading ? (
        <div className="text-center py-12 text-slate-500 text-sm">Analyzing overlaps…</div>
      ) : results.length === 0 ? (
        <PageEmptyState title="No overlap results" detail="No potential matches were returned for this review filter." />
      ) : (
        <div className="space-y-4">
          {results.map((r) => <OverlapCard key={r.id} result={r} onDecision={load} />)}
        </div>
      )}
    </div>
  );
}
