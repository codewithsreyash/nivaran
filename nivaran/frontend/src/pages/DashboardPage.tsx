import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle, ArrowRight, BarChart3, CheckCircle2, Clock3, FileText,
  ListOrdered, RefreshCw, ShieldAlert,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import { complaintsAPI, dashboardAPI } from '../lib/api';
import type { DashboardData } from '../types';
import { formatDate, priorityLabel, statusLabel } from '../lib/utils';

const STATUS_COLORS: Record<string, string> = {
  registered: '#1d4ed8',
  under_initial_review: '#2563a6',
  under_process: '#a65008',
  awaiting_information: '#9a3412',
  transferred: '#52667a',
  escalated: '#b42335',
  disposed: '#15803d',
  closed: '#475569',
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: '#b42335', high: '#c45b12', medium: '#a65008', low: '#52667a', unscored: '#718096',
};

const requiredCounts = [
  'total_complaints', 'pending_complaints', 'under_process', 'disposed_complaints',
  'overdue_complaints', 'critical_cases', 'high_priority_cases',
  'pending_overlap_reviews', 'pending_evidence_reviews',
] as const;

interface RecentComplaintRow {
  id: number;
  complaint_id: string;
  title: string;
  status: string;
  registration_date: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isCount(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0;
}

function isDashboardData(value: unknown): value is DashboardData {
  if (!isRecord(value)) return false;
  if (!requiredCounts.every((key) => isCount(value[key]))) return false;
  const isCountList = (items: unknown, key: string) => Array.isArray(items)
    && items.every((item) => isRecord(item) && typeof item[key] === 'string' && isCount(item.count));
  return isCountList(value.status_distribution, 'status')
    && isCountList(value.priority_distribution, 'priority')
    && isCountList(value.bureau_workload, 'bureau')
    && isCountList(value.monthly_trend, 'month');
}

function isComplaintList(value: unknown): value is { items: RecentComplaintRow[]; total: number } {
  return isRecord(value) && Array.isArray(value.items) && isCount(value.total)
    && value.items.every((item) => isRecord(item)
      && typeof item.id === 'number'
      && typeof item.complaint_id === 'string'
      && typeof item.title === 'string'
      && typeof item.status === 'string'
      && typeof item.registration_date === 'string');
}

function countLabel(value: number): string {
  return value.toLocaleString('en-IN');
}

function StatCard({
  label, value, icon: Icon, tone, to,
}: {
  label: string;
  value: number;
  icon: LucideIcon;
  tone: 'blue' | 'amber' | 'green' | 'red' | 'slate';
  to: string;
}) {
  const toneClass = {
    blue: 'dashboard-icon-blue', amber: 'dashboard-icon-amber',
    green: 'dashboard-icon-green', red: 'dashboard-icon-red', slate: 'dashboard-icon-slate',
  }[tone];
  return (
    <Link to={to} className="dashboard-stat-card">
      <span className={`dashboard-stat-icon ${toneClass}`}><Icon size={18} aria-hidden="true" /></span>
      <span className="dashboard-stat-label">{label}</span>
      <span className="dashboard-stat-value">{countLabel(value)}</span>
      <span className="dashboard-stat-link">View related records <ArrowRight size={14} aria-hidden="true" /></span>
    </Link>
  );
}

function ChartCard({ title, description, children }: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="dashboard-panel">
      <div className="dashboard-panel-heading">
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {children}
    </section>
  );
}

function ChartMessage({ children }: { children: React.ReactNode }) {
  return <div className="dashboard-chart-message">{children}</div>;
}

function ErrorPanel({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <section className="dashboard-error" role="alert">
      <div className="dashboard-error-icon"><AlertTriangle size={20} aria-hidden="true" /></div>
      <div className="dashboard-error-copy">
        <h2>Dashboard unavailable</h2>
        <p>{message}</p>
      </div>
      <button className="btn-secondary" onClick={onRetry}><RefreshCw size={15} aria-hidden="true" /> Retry</button>
    </section>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [recentComplaints, setRecentComplaints] = useState<RecentComplaintRow[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recentError, setRecentError] = useState(false);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    setRecentError(false);
    setData(null);
    setRecentComplaints(null);

    const [dashboardResult, complaintsResult] = await Promise.allSettled([
      dashboardAPI.get(signal),
      complaintsAPI.list({ page: 1, per_page: 5, sort_by: 'registration_date', sort_desc: true }, signal),
    ]);

    if (signal?.aborted) return;

    if (dashboardResult.status === 'rejected') {
      setError('We could not retrieve dashboard data. Check your connection and try again.');
      setRecentError(complaintsResult.status === 'rejected');
      setLoading(false);
      return;
    }

    if (!isDashboardData(dashboardResult.value.data)) {
      setError('The dashboard response is incomplete. Retry to request the latest data.');
      setRecentError(complaintsResult.status === 'rejected');
      setLoading(false);
      return;
    }

    setData(dashboardResult.value.data);
    if (complaintsResult.status === 'fulfilled' && isComplaintList(complaintsResult.value.data)) {
      setRecentComplaints(complaintsResult.value.data.items);
    } else {
      setRecentError(true);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const retry = () => { void load(); };

  if (loading) {
    return (
      <div className="dashboard-page" aria-busy="true" aria-live="polite">
        <div className="page-header">
          <div><div className="skeleton h-7 w-52 mb-2" /><div className="skeleton h-4 w-80" /></div>
          <div className="skeleton h-10 w-28 rounded-lg" />
        </div>
        <div className="dashboard-kpi-grid">{Array.from({ length: 6 }, (_, index) => (
          <div className="dashboard-stat-skeleton" key={index}><div className="skeleton h-9 w-9 rounded-lg" /><div className="skeleton h-4 w-24" /><div className="skeleton h-8 w-16" /></div>
        ))}</div>
        <div className="dashboard-chart-grid">{Array.from({ length: 2 }, (_, index) => <div className="dashboard-chart-skeleton" key={index}><div className="skeleton h-5 w-40 mb-5" /><div className="skeleton h-52 w-full" /></div>)}</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="dashboard-page">
        <PageHeading onRetry={retry} loading={loading} />
        <ErrorPanel message={error ?? 'Dashboard data is not available.'} onRetry={retry} />
      </div>
    );
  }

  const statusData = data.status_distribution.map((item) => ({
    name: statusLabel(item.status), value: item.count, color: STATUS_COLORS[item.status] ?? '#52667a',
  }));
  const priorityData = data.priority_distribution.map((item) => ({
    name: priorityLabel(item.priority as Parameters<typeof priorityLabel>[0]),
    value: item.count,
    color: PRIORITY_COLORS[item.priority] ?? '#52667a',
  }));

  return (
    <div className="dashboard-page">
      <PageHeading onRetry={retry} loading={loading} />

      <section className="dashboard-kpi-grid" aria-label="Complaint summary">
        <StatCard label="Total complaints" value={data.total_complaints} icon={FileText} tone="blue" to="/complaints" />
        <StatCard label="Awaiting action" value={data.pending_complaints} icon={Clock3} tone="amber" to="/complaints" />
        <StatCard label="In progress" value={data.under_process} icon={BarChart3} tone="blue" to="/complaints" />
        <StatCard label="Disposed or closed" value={data.disposed_complaints} icon={CheckCircle2} tone="green" to="/complaints" />
        <StatCard label="Overdue" value={data.overdue_complaints} icon={AlertTriangle} tone="red" to="/deadlines" />
        <StatCard label="Critical priority" value={data.critical_cases} icon={ShieldAlert} tone="red" to="/priority-queue?min_level=critical" />
      </section>

      {data.total_complaints === 0 && (
        <section className="dashboard-empty" aria-live="polite">
          <div className="dashboard-empty-icon"><FileText size={22} aria-hidden="true" /></div>
          <div><h2>No complaints found</h2><p>The dashboard API returned zero complaints for the records available to your account.</p></div>
          <Link className="btn-secondary" to="/complaints">Open complaint management <ArrowRight size={15} aria-hidden="true" /></Link>
        </section>
      )}

      <section className="dashboard-followups" aria-label="Items requiring review">
        <div><span className="dashboard-followup-label">High priority</span><strong>{countLabel(data.high_priority_cases)}</strong><Link to="/priority-queue?min_level=high">Review queue <ArrowRight size={14} aria-hidden="true" /></Link></div>
        <div><span className="dashboard-followup-label">Overlap reviews pending</span><strong>{countLabel(data.pending_overlap_reviews)}</strong><Link to="/overlaps">Review overlaps <ArrowRight size={14} aria-hidden="true" /></Link></div>
        <div><span className="dashboard-followup-label">Evidence reviews pending</span><strong>{countLabel(data.pending_evidence_reviews)}</strong><Link to="/evidence">Review evidence <ArrowRight size={14} aria-hidden="true" /></Link></div>
      </section>

      <section className="dashboard-chart-grid" aria-label="Complaint analysis">
        <ChartCard title="Complaints by status" description="Current status counts returned by the dashboard API.">
          {data.total_complaints === 0 ? <ChartMessage>No status distribution for an empty complaint set.</ChartMessage>
            : statusData.length === 0 ? <ChartMessage>Status distribution is unavailable in the response.</ChartMessage>
              : <div className="dashboard-chart-wrap" style={{ height: Math.max(230, statusData.length * 38) }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={statusData} layout="vertical" margin={{ top: 4, right: 18, left: 8, bottom: 4 }}>
                    <CartesianGrid stroke="#e7edf3" horizontal={false} />
                    <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: '#596c80' }} axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="name" width={148} tick={{ fontSize: 11, fill: '#34495e' }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ border: '1px solid #dce3eb', borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="value" name="Complaints" radius={[0, 4, 4, 0]} maxBarSize={22}>
                      {statusData.map((item) => <Cell key={item.name} fill={item.color} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>}
        </ChartCard>

        <ChartCard title="Complaints by priority" description="Priority levels in the visible complaint set.">
          {data.total_complaints === 0 ? <ChartMessage>No priority distribution for an empty complaint set.</ChartMessage>
            : priorityData.length === 0 ? <ChartMessage>Priority distribution is unavailable in the response.</ChartMessage>
              : <div className="dashboard-chart-wrap" style={{ height: 250 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={priorityData} layout="vertical" margin={{ top: 4, right: 18, left: 8, bottom: 4 }}>
                    <CartesianGrid stroke="#e7edf3" horizontal={false} />
                    <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: '#596c80' }} axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11, fill: '#34495e' }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ border: '1px solid #dce3eb', borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="value" name="Complaints" radius={[0, 4, 4, 0]} maxBarSize={26}>
                      {priorityData.map((item) => <Cell key={item.name} fill={item.color} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>}
        </ChartCard>

        <ChartCard title="Monthly registrations" description="Monthly counts from the dashboard response.">
          {data.monthly_trend.length === 0 ? <ChartMessage>Monthly registration data is unavailable.</ChartMessage>
            : <div className="dashboard-chart-wrap" style={{ height: 250 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.monthly_trend} margin={{ top: 8, right: 12, left: -16, bottom: 4 }}>
                  <CartesianGrid stroke="#e7edf3" strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#596c80' }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: '#596c80' }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ border: '1px solid #dce3eb', borderRadius: 8, fontSize: 12 }} />
                  <Line type="monotone" dataKey="count" name="Complaints" stroke="#1d4ed8" strokeWidth={2} dot={{ r: 3, fill: '#1d4ed8' }} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>}
        </ChartCard>
      </section>

      <section className="dashboard-recent dashboard-panel">
        <div className="dashboard-panel-heading dashboard-recent-heading">
          <div><h2>Recently registered complaints</h2><p>Latest records from complaint management.</p></div>
          <Link className="dashboard-text-link" to="/complaints">View all complaints <ArrowRight size={14} aria-hidden="true" /></Link>
        </div>
        {recentError ? <ChartMessage>Recent complaint records could not be loaded. Use complaint management to retry.</ChartMessage>
          : recentComplaints?.length === 0 ? <ChartMessage>No complaint records were returned.</ChartMessage>
            : recentComplaints && <div className="dashboard-recent-list">
              {recentComplaints.map((complaint) => (
                <Link className="dashboard-recent-row" to={`/complaints/${complaint.id}`} key={complaint.id}>
                  <span className="dashboard-recent-id">{complaint.complaint_id}</span>
                  <span className="dashboard-recent-title">{complaint.title}</span>
                  <span className={`dashboard-status-badge status-${complaint.status}`}>{statusLabel(complaint.status)}</span>
                  <span className="dashboard-recent-date">{formatDate(complaint.registration_date)}</span>
                  <ArrowRight size={15} className="dashboard-recent-arrow" aria-hidden="true" />
                </Link>
              ))}
            </div>}
      </section>

      <nav className="dashboard-shortcuts" aria-label="Dashboard shortcuts">
        <Link to="/complaints"><FileText size={16} aria-hidden="true" /> Complaint management</Link>
        <Link to="/priority-queue"><ListOrdered size={16} aria-hidden="true" /> Priority queue</Link>
        <Link to="/deadlines"><Clock3 size={16} aria-hidden="true" /> Deadlines</Link>
        <Link to="/reports"><BarChart3 size={16} aria-hidden="true" /> Reports</Link>
      </nav>
    </div>
  );
}

function PageHeading({ onRetry, loading }: { onRetry: () => void; loading: boolean }) {
  return (
    <div className="page-header dashboard-heading">
      <div>
        <h1 className="page-title">Complaint overview</h1>
        <p className="page-subtitle">Current complaint status, priority, and deadlines for records available to your account.</p>
      </div>
      <button onClick={onRetry} disabled={loading} className="btn-secondary" aria-label="Refresh dashboard data">
        <RefreshCw size={15} aria-hidden="true" /> Refresh
      </button>
    </div>
  );
}
