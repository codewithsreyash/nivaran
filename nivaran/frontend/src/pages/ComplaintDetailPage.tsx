import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  complaintsAPI, bureausAPI
} from '../lib/api';
import type { Complaint, CaseAction, PriorityAssessment, Bureau, EvidenceAssessment, OverlapResult } from '../types';
import {
  statusBadge, statusLabel, priorityBadge, priorityLabel,
  categoryLabel, formatDate, formatDateTime, isOverdue
} from '../lib/utils';
import {
  ArrowLeft, AlertTriangle, CheckCircle2, Clock, Zap, GitMerge,
  Shield, BarChart3, Send, RefreshCw, Info, ChevronRight, FileQuestion
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import { PageErrorState } from '../components/PageState';

export default function ComplaintDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { canWrite } = useAuth();
  const [complaint, setComplaint] = useState<Complaint | null>(null);
  const [actions, setActions] = useState<CaseAction[]>([]);
  const [priority, setPriority] = useState<PriorityAssessment | null>(null);
  const [assessment, setAssessment] = useState<EvidenceAssessment | null>(null);
  const [overlaps, setOverlaps] = useState<OverlapResult[]>([]);
  const [bureaus, setBureaus] = useState<Bureau[]>([]);
  const [assignments, setAssignments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [bureauLoadError, setBureauLoadError] = useState(false);
  const [addingAction, setAddingAction] = useState(false);
  const [actionText, setActionText] = useState('');
  const [actionType, setActionType] = useState('follow_up.sent');
  const [calculatingPriority, setCalculatingPriority] = useState(false);
  const [detectingOverlap, setDetectingOverlap] = useState(false);
  const [assessingEvidence, setAssessingEvidence] = useState(false);

  const load = async () => {
    setLoading(true);
    setLoadError(false);
    setComplaint(null);
    setActions([]);
    setPriority(null);
    setAssessment(null);
    setOverlaps([]);
    setAssignments([]);
    try {
      const [cRes, aRes, pRes, eRes, oRes, asRes] = await Promise.all([
        complaintsAPI.get(Number(id)),
        complaintsAPI.getActions(Number(id)),
        complaintsAPI.priorityHistory(Number(id)),
        complaintsAPI.getAssessment(Number(id)),
        complaintsAPI.getOverlaps(Number(id)),
        complaintsAPI.getAssignments(Number(id)),
      ]);
      setComplaint(cRes.data);
      setActions(aRes.data);
      if (pRes.data && pRes.data.length > 0) setPriority(pRes.data[0]);
      if (eRes.data && eRes.data.length > 0) setAssessment(eRes.data[0]);
      if (oRes.data) setOverlaps(oRes.data);
      if (asRes.data) setAssignments(asRes.data);
    } catch {
      setComplaint(null);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]);
  useEffect(() => {
    bureausAPI.list().then((r) => setBureaus(r.data)).catch(() => setBureauLoadError(true));
  }, []);

  const addAction = async () => {
    if (!actionText.trim()) return;
    setAddingAction(true);
    try {
      await complaintsAPI.addAction(Number(id), { action_type: actionType, description: actionText });
      toast.success('Action recorded');
      setActionText('');
      load();
    } catch { toast.error('Failed to record action'); }
    finally { setAddingAction(false); }
  };

  const calcPriority = async () => {
    setCalculatingPriority(true);
    try {
      const res = await complaintsAPI.calculatePriority(Number(id));
      setPriority(res.data);
      toast.success('Priority recalculated');
      load();
    } catch { toast.error('Failed to calculate priority'); }
    finally { setCalculatingPriority(false); }
  };

  const detectOverlaps = async () => {
    setDetectingOverlap(true);
    try {
      const res = await complaintsAPI.detectOverlaps(Number(id));
      toast.success(res.data.message);
    } catch { toast.error('Overlap detection failed'); }
    finally { setDetectingOverlap(false); }
  };

  const runAssessment = async () => {
    try {
      await complaintsAPI.assess(Number(id));
      toast.success('Evidence assessment completed');
      load();
    } catch { toast.error('Assessment failed'); }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  if (loadError) return <PageErrorState message="Complaint details or related workflow records could not be loaded." onRetry={() => void load()} />;

  if (!complaint) return <div className="text-slate-500 text-center py-16">Complaint not found</div>;

  const overdue = isOverdue(complaint.target_disposal_date, complaint.status);
  const effectivePriority = complaint.assigned_priority_level ?? complaint.calculated_priority_level;
  const completenessScore = assessment?.completeness_score ?? complaint.completeness_score;
  const readinessScore = assessment?.evidence_readiness_score;

  return (
    <div className="max-w-5xl space-y-6">
      {/* Header */}
      <div>
        <Link to="/complaints" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 mb-3 transition-colors">
          <ArrowLeft size={13} /> Back to Complaints
        </Link>
        <div className="flex flex-wrap items-start gap-4 justify-between">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-bold text-slate-100">{complaint.title}</h1>
              <span className={statusBadge(complaint.status)}>{statusLabel(complaint.status)}</span>
              <span className={priorityBadge(effectivePriority)}>{priorityLabel(effectivePriority)}</span>
              {overdue && <span className="badge badge-critical flex items-center gap-1"><AlertTriangle size={10} /> Overdue</span>}
            </div>
            <p className="font-mono text-xs text-slate-500 mt-1">{complaint.complaint_id}</p>
          </div>
          {canWrite && (
            <div className="flex gap-2 flex-wrap">
              <button onClick={detectOverlaps} disabled={detectingOverlap} className="btn-secondary text-xs">
                <GitMerge size={13} /> {detectingOverlap ? 'Detecting…' : 'Detect Overlaps'}
              </button>
              <button onClick={runAssessment} disabled={assessingEvidence} className="btn-secondary text-xs">
                <Shield size={13} /> {assessingEvidence ? 'Assessing…' : 'Assess Evidence'}
              </button>
              <button onClick={calcPriority} disabled={calculatingPriority} className="btn-secondary text-xs">
                <RefreshCw size={13} /> {calculatingPriority ? 'Calculating…' : 'Recalculate Priority'}
              </button>
            </div>
          )}
        </div>
      </div>

      {bureauLoadError && <p className="text-sm text-status-warning" role="status">Bureau options could not be loaded; transfer options may be limited.</p>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main info */}
        <div className="lg:col-span-2 space-y-5">
          <div className="card">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Description</h3>
            <p className="text-sm text-slate-400 leading-relaxed whitespace-pre-wrap">{complaint.description}</p>
          </div>

          {/* Priority explanation */}
          {priority && (
            <div className="card border-l-4 border-l-indigo-500">
              <div className="flex items-start gap-3">
                <BarChart3 size={16} className="text-indigo-400 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-semibold text-slate-300">Priority Explanation</h3>
                    <span className={priorityBadge(priority.priority_level)}>
                      Score: {priority.score.toFixed(1)} / 100
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed mb-3">{priority.explanation}</p>
                  <div className="grid grid-cols-3 gap-2 text-[11px]">
                    {[
                      ['Urgency', priority.urgency_contribution],
                      ['Impact', priority.impact_contribution],
                      ['Deadline', priority.deadline_contribution],
                      ['Ageing', priority.ageing_contribution],
                      ['Escalation', priority.escalation_contribution],
                      ['Transfers', priority.transfer_contribution],
                    ].map(([label, val]) => (
                      <div key={String(label)} className="bg-slate-800/60 rounded-lg px-2 py-1.5">
                        <p className="text-slate-500">{label}</p>
                        <p className="text-slate-300 font-semibold">{val == null ? '—' : `${Number(val).toFixed(1)} pts`}</p>
                      </div>
                    ))}
                  </div>
                  {priority.missing_data_flags && priority.missing_data_flags.length > 0 && (
                    <div className="mt-3 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <p className="text-[11px] font-semibold text-amber-300 mb-1 flex items-center gap-1">
                        <AlertTriangle size={12} /> Data gaps surfaced during priority calculation:
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {priority.missing_data_flags.map((flag) => (
                          <span key={flag} className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-mono">
                            {flag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <p className="text-[10px] text-slate-600 mt-2">
                    Engine: Rule-Based Priority Engine · Algorithm: {priority.calculation_version} · {priority.is_override ? '⚠ Manual Override' : 'Automated'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Evidence Completeness & Quality */}
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <Shield size={15} className="text-indigo-400" /> Evidence Completeness & Readiness
              </h3>
              {assessment && (
                <span className={`badge ${
                  assessment.status.includes('Complete') ? 'badge-success' : 'badge-warning'
                }`}>
                  {assessment.status}
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-500">Completeness Score</span>
                  <span className="text-slate-300 font-mono font-medium">
                    {completenessScore == null ? 'Unavailable' : `${completenessScore.toFixed(0)}%`}
                  </span>
                </div>
                <div className="h-2 bg-slate-800 rounded-full">
                  <div
                    className="h-2 bg-indigo-500 rounded-full transition-all"
                    style={{ width: `${completenessScore ?? 0}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-500">Evidence Readiness</span>
                  <span className="text-slate-300 font-mono font-medium">
                    {readinessScore == null ? 'Unavailable' : `${readinessScore.toFixed(0)}%`}
                  </span>
                </div>
                <div className="h-2 bg-slate-800 rounded-full">
                  <div
                    className="h-2 bg-emerald-500 rounded-full transition-all"
                    style={{ width: `${readinessScore ?? 0}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Assessment Verification Indicators */}
            {assessment && (
              <div className="grid grid-cols-3 gap-2 text-xs mb-3">
                <div className="p-2 rounded bg-slate-800/40 border border-slate-700/50">
                  <p className="text-[10px] text-slate-500 uppercase">Institution Status</p>
                  <p className={`font-medium text-[11px] mt-0.5 ${assessment.institution_verified ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {assessment.institution_verified ? 'Verified in available records' : 'Snapshot or unverified'}
                  </p>
                </div>
                <div className="p-2 rounded bg-slate-800/40 border border-slate-700/50">
                  <p className="text-[10px] text-slate-500 uppercase">Date Consistency</p>
                  <p className={`font-medium text-[11px] mt-0.5 ${assessment.date_consistency_ok ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {assessment.date_consistency_ok ? '✓ Chronology OK' : '⚠ Inconsistency Detected'}
                  </p>
                </div>
                <div className="p-2 rounded bg-slate-800/40 border border-slate-700/50">
                  <p className="text-[10px] text-slate-500 uppercase">Documents</p>
                  <p className="font-medium text-slate-300 text-[11px] mt-0.5">
                    {assessment.document_count} uploaded
                  </p>
                </div>
              </div>
            )}

            {/* Missing Fields Warnings */}
            {assessment?.missing_fields && assessment.missing_fields.length > 0 && (
              <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 mb-2">
                <p className="text-[11px] font-semibold text-amber-300 mb-1 flex items-center gap-1">
                  <FileQuestion size={12} /> Missing required documentation fields:
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {assessment.missing_fields.map((field) => (
                    <span key={field} className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-200 text-[10px] font-mono">
                      {field.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {assessment?.consistency_issues && assessment.consistency_issues.length > 0 && (
              <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20">
                <p className="text-[11px] font-semibold text-rose-300 mb-1">Consistency Issues:</p>
                <ul className="list-disc list-inside text-[11px] text-rose-300/90 space-y-0.5">
                  {assessment.consistency_issues.map((issue, idx) => (
                    <li key={idx}>{issue}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Potential Duplicate Cases (Overlap Engine) */}
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                  <GitMerge size={15} className="text-indigo-400" /> Potential Duplicate Cases ({overlaps.length})
                </h3>
                <p className="text-[11px] text-slate-500">
                  Detector: RapidFuzz multi-factor baseline · Minimum threshold 25/100
                </p>
              </div>
              <Link to="/overlaps" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium">
                Review Module <ChevronRight size={12} />
              </Link>
            </div>

            {overlaps.length === 0 ? (
              <div className="p-4 rounded-lg bg-slate-800/30 border border-slate-700/40 text-center">
                <p className="text-xs text-slate-400">No overlapping complaints detected across AICTE bureaus.</p>
                <p className="text-[11px] text-slate-600 mt-1">Click "Detect Overlaps" to scan the repository for similar cases.</p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {overlaps.slice(0, 3).map((ov) => {
                  const candidate = ov.candidate_complaint;
                  const score = ov.similarity_score;
                  const scoreCls = score >= 70 ? 'text-rose-400' : score >= 45 ? 'text-amber-400' : 'text-slate-400';
                  return (
                    <div key={ov.id} className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/60 flex items-center justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-indigo-400 font-semibold">{candidate?.complaint_id || `Case #${ov.candidate_complaint_id}`}</span>
                          {candidate?.category && (
                            <span className="badge badge-indigo text-[10px]">{categoryLabel(candidate.category)}</span>
                          )}
                          <span className={`badge ${ov.review_status === 'reviewed' ? 'badge-success' : 'badge-warning'} text-[10px]`}>
                            {ov.review_status === 'reviewed' ? 'Reviewed' : 'Pending Review'}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 truncate mt-1">{candidate?.title || 'Complaint details'}</p>
                        {candidate?.institution_name_snapshot && (
                          <p className="text-[11px] text-slate-500 truncate mt-0.5">Institution: {candidate.institution_name_snapshot}</p>
                        )}
                      </div>
                      <div className="text-right shrink-0">
                        <p className={`text-base font-bold font-mono ${scoreCls}`}>{score.toFixed(0)} / 100</p>
                        <p className="text-[10px] text-slate-500">Similarity</p>
                        <Link to={`/complaints/${ov.candidate_complaint_id}`} className="text-[10px] text-indigo-400 hover:underline mt-1 block">
                          View Case →
                        </Link>
                      </div>
                    </div>
                  );
                })}
                {overlaps.length > 3 && (
                  <p className="text-center text-[11px] text-slate-500 pt-1">
                    + {overlaps.length - 3} more overlapping candidate(s). <Link to="/overlaps" className="text-indigo-400 hover:underline">View all in Overlaps Page</Link>
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Action timeline */}
          <div className="card">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Case Timeline</h3>
            <div className="space-y-3">
              {actions.length === 0 ? (
                <p className="text-xs text-slate-500">No actions recorded yet.</p>
              ) : (
                actions.map((a) => (
                  <div key={a.id} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 border-2 border-slate-900 shrink-0 mt-0.5" />
                      <div className="w-px flex-1 bg-slate-800 mt-1" />
                    </div>
                    <div className="pb-3 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-medium text-slate-200">{a.action_type.replace(/\./g, ' › ')}</span>
                        {a.new_status && (
                          <span className={statusBadge(a.new_status as any)}>{statusLabel(a.new_status)}</span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">{a.description}</p>
                      <p className="text-[11px] text-slate-600 mt-1">
                        {a.actor?.full_name ?? 'System'} · {formatDateTime(a.created_at)}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Add action */}
            {canWrite && (
              <div className="mt-4 pt-4 border-t border-slate-800 space-y-2">
                <div className="flex gap-2">
                  <select className="select w-48 text-xs" value={actionType} onChange={(e) => setActionType(e.target.value)}>
                    <option value="follow_up.sent">Follow-up Sent</option>
                    <option value="document.requested">Document Requested</option>
                    <option value="document.received">Document Received</option>
                    <option value="verification.performed">Verification Performed</option>
                    <option value="note.added">Note Added</option>
                    <option value="clarification.requested">Clarification Requested</option>
                  </select>
                </div>
                <div className="flex gap-2">
                  <input
                    className="input flex-1 text-xs"
                    placeholder="Describe the action taken…"
                    value={actionText}
                    onChange={(e) => setActionText(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && addAction()}
                  />
                  <button onClick={addAction} disabled={addingAction || !actionText} className="btn-primary text-xs px-3">
                    <Send size={13} />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar info */}
        <div className="space-y-4">
          <div className="card">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Case Details</h3>
            <dl className="space-y-2.5 text-xs">
              {[
                ['Category', categoryLabel(complaint.category)],
                ['Bureau', complaint.bureau?.name ?? '—'],
                ['Assigned To', complaint.assigned_officer?.full_name ?? 'Unassigned'],
                ['Registered', formatDate(complaint.registration_date)],
                ['Incident Date', formatDate(complaint.incident_date)],
                ['Target Disposal', formatDate(complaint.target_disposal_date)],
                ['Last Action', formatDate(complaint.last_action_date)],
                ['Institution', complaint.institution_name_snapshot ?? '—'],
                ['Anonymous', complaint.is_anonymous ? 'Yes' : 'No'],
                ['Data Source', complaint.data_source_label ?? '—'],
              ].map(([k, v]) => (
                <div key={String(k)} className="flex justify-between gap-2">
                  <dt className="text-slate-500 shrink-0">{k}</dt>
                  <dd className="text-slate-300 text-right">{String(v)}</dd>
                </div>
              ))}
            </dl>
          </div>

          {complaint.next_required_action && (
            <div className="card bg-indigo-500/10 border-indigo-500/30">
              <div className="flex gap-2">
                <Info size={14} className="text-indigo-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-medium text-indigo-300 mb-1">Next Required Action</p>
                  <p className="text-xs text-indigo-200">{complaint.next_required_action}</p>
                </div>
              </div>
            </div>
          )}

          {/* Deadline & Ageing Metrics */}
          <div className="card">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Deadline & Ageing</h3>
            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Target Disposal</span>
                <span className={`font-medium ${overdue ? 'text-rose-400 font-semibold' : 'text-slate-300'}`}>
                  {formatDate(complaint.target_disposal_date)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Timeline Status</span>
                {overdue ? (
                  <span className="badge badge-critical text-[10px]">Overdue</span>
                ) : (
                  <span className="badge badge-success text-[10px]">Within SLA Window</span>
                )}
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Last Bureau Action</span>
                <span className="text-slate-300">{formatDate(complaint.last_action_date)}</span>
              </div>
            </div>
          </div>

          {/* Assignment History */}
          {assignments.length > 0 && (
            <div className="card">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Assignment History</h3>
              <div className="space-y-2 text-xs">
                {assignments.map((a, idx) => (
                  <div key={a.id} className="p-2 rounded bg-slate-800/40 border border-slate-700/50">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-slate-200">
                        {a.officer?.full_name || 'Unassigned'}
                      </span>
                      <span className="text-[10px] text-slate-500">{formatDateTime(a.assigned_at)}</span>
                    </div>
                    <p className="text-[10px] text-slate-400">{a.assignment_type.replace(/_/g, ' ')}</p>
                    {a.reason && <p className="text-[10px] text-slate-500 mt-0.5 italic">{a.reason}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="card">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Quick Links</h3>
            <div className="space-y-1.5">
              <Link to="/overlaps" className="flex items-center gap-2 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
                <GitMerge size={12} /> View All Overlaps Module
              </Link>
              <Link to="/priority-queue" className="flex items-center gap-2 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
                <BarChart3 size={12} /> Priority Queue
              </Link>
              <Link to="/evidence" className="flex items-center gap-2 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
                <Shield size={12} /> Evidence Verification
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
