import { useCallback, useEffect, useState } from 'react';
import { bureausAPI, reportsAPI } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import type { Bureau } from '../types';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import { Download } from 'lucide-react';
import { PageErrorState } from '../components/PageState';
import toast from 'react-hot-toast';

const STATUS_COLORS: Record<string, string> = {
  registered: '#1d4ed8', under_initial_review: '#2563a6',
  under_process: '#a65008', awaiting_information: '#9a3412',
  transferred: '#52667a', escalated: '#b42335',
  disposed: '#15803d', closed: '#475569',
};
const PRIORITY_COLORS: Record<string, string> = {
  critical: '#b42335', high: '#c45b12', medium: '#a65008', low: '#52667a', unscored: '#718096',
};
const BUREAU_COLORS = ['#0d2740', '#1d4ed8', '#405d7c', '#15803d', '#a65008', '#52667a'];

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-slate-300 mb-4">{title}</h3>
      {children}
    </div>
  );
}

const tooltipStyle = { background: '#ffffff', color: '#172b40', border: '1px solid #dce3eb', borderRadius: 8, fontSize: 12 };

export default function ReportsPage() {
  const { isAdmin, isReviewer } = useAuth();
  const canSelectBureau = isAdmin || isReviewer;
  const [complaints, setComplaints] = useState<any>(null);
  const [priority, setPriority] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(false);
  const [bureaus, setBureaus] = useState<Bureau[]>([]);
  const [bureausError, setBureausError] = useState(false);
  const [bureauId, setBureauId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const params = {
    bureau_id: canSelectBureau && bureauId ? Number(bureauId) : undefined,
    start_date: startDate ? `${startDate}T00:00:00` : undefined,
    end_date: endDate ? `${endDate}T23:59:59` : undefined,
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [c, p] = await Promise.all([reportsAPI.complaints(params), reportsAPI.priority(params)]);
      setComplaints(c.data);
      setPriority(p.data);
    } catch {
      setComplaints(null);
      setPriority(null);
      setError(true);
    } finally { setLoading(false); }
  }, [bureauId, canSelectBureau, endDate, startDate]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    if (canSelectBureau) bureausAPI.list().then((response) => setBureaus(response.data)).catch(() => { setBureaus([]); setBureausError(true); });
  }, [canSelectBureau]);

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      setExporting(true);
      const res = await reportsAPI.export(format, params);
      const blob = format === 'csv'
        ? new Blob([res.data], { type: 'text/csv;charset=utf-8;' })
        : new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `aicte_oneview_complaints_report.${format}`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success('Report downloaded');
    } catch (err) {
      console.error('Export error:', err);
      toast.error(`Could not export ${format.toUpperCase()} report`);
    } finally {
      setExporting(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  const statusData = (complaints?.by_status ?? []).map((d: any) => ({
    name: d.status.replace(/_/g, ' '), value: d.count,
    fill: STATUS_COLORS[d.status] ?? '#334155',
  }));

  const categoryData = (complaints?.by_category ?? []).map((d: any) => ({
    name: d.category.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
    Complaints: d.count,
  }));

  const bureauData = (complaints?.by_bureau ?? []).map((d: any, i: number) => ({
    name: d.bureau, Cases: d.count, fill: BUREAU_COLORS[i % BUREAU_COLORS.length],
  }));

  const priorityData = (priority?.by_priority ?? []).map((d: any) => ({
    name: d.priority.charAt(0).toUpperCase() + d.priority.slice(1),
    value: d.count,
    fill: PRIORITY_COLORS[d.priority] ?? '#334155',
  }));

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-title">Reports & Analytics</h1>
          <p className="page-subtitle">Aggregated summaries from the report APIs for records available to your account.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport('csv')}
            disabled={exporting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 border border-slate-700 transition"
            title="Download complaints report as CSV"
          >
            <Download size={13} />
            {exporting ? 'Exporting...' : 'Export CSV'}
          </button>
          <button
            onClick={() => handleExport('json')}
            disabled={exporting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 border border-slate-700 transition"
            title="Download complaints report as JSON"
          >
            <Download size={13} />
            JSON
          </button>
        </div>
      </div>

      <section className="card flex flex-wrap items-end gap-3" aria-label="Report filters">
        {canSelectBureau && <div className="min-w-48 flex-1">
          <label className="label" htmlFor="report-bureau">Bureau scope</label>
          <select id="report-bureau" className="select" value={bureauId} onChange={(event) => setBureauId(event.target.value)}>
            <option value="">All authorized bureaus</option>
            {bureaus.map((bureau) => <option key={bureau.id} value={bureau.id}>{bureau.name}</option>)}
          </select>
        </div>}
        <div className="min-w-40 flex-1">
          <label className="label" htmlFor="report-start-date">From registration date</label>
          <input id="report-start-date" className="input" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
        </div>
        <div className="min-w-40 flex-1">
          <label className="label" htmlFor="report-end-date">Through registration date</label>
          <input id="report-end-date" className="input" type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
        </div>
        <button className="btn-secondary" onClick={() => { setBureauId(''); setStartDate(''); setEndDate(''); }}>Clear filters</button>
      </section>
      {bureausError && canSelectBureau && <p className="text-sm text-status-warning" role="status">Bureau options could not be loaded; reports remain limited to the API’s default authorized scope.</p>}

      {error && <PageErrorState message="Report data could not be loaded. Summary values and charts are hidden until both report requests succeed." onRetry={() => void load()} />}

      {/* Overdue KPI */}
      {!error && <div className="card bg-rose-500/10 border-rose-500/20">
        <div className="flex items-center gap-4">
          <div>
            <p className="text-3xl font-bold text-rose-700">{typeof priority?.total_overdue === 'number' ? priority.total_overdue.toLocaleString('en-IN') : 'Unavailable'}</p>
            <p className="text-xs text-slate-500 mt-1">Total Overdue Cases</p>
          </div>
          <div className="flex-1 pl-6 border-l border-rose-500/20">
            <p className="text-xs text-slate-400">These cases have passed their target disposal date without being disposed or closed. They require immediate attention from the assigned bureau officer.</p>
          </div>
        </div>
      </div>}

      {!error && <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status pie */}
        <ChartCard title="Cases by Status">
          {statusData.length === 0 ? <p className="page-empty-state text-sm">Status breakdown is unavailable.</p> : <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label={({ name, value }) => `${value}`}>
                {statusData.map((d: any, i: number) => <Cell key={i} fill={d.fill} />)}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>}
        </ChartCard>

        {/* Priority pie */}
        <ChartCard title="Cases by Priority">
          {priorityData.length === 0 ? <p className="page-empty-state text-sm">Priority breakdown is unavailable.</p> : <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={priorityData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100}>
                {priorityData.map((d: any, i: number) => <Cell key={i} fill={d.fill} />)}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>}
        </ChartCard>

        {/* Category bar */}
        <ChartCard title="Cases by Category">
          {categoryData.length === 0 ? <p className="page-empty-state text-sm">Category breakdown is unavailable.</p> : <ResponsiveContainer width="100%" height={300}>
            <BarChart data={categoryData} layout="vertical" margin={{ left: 100 }}>
              <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} width={100} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="Complaints" fill="#1d4ed8" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>}
        </ChartCard>

        {/* Bureau bar */}
        <ChartCard title="Cases by Bureau / Cell">
          {bureauData.length === 0 ? <p className="page-empty-state text-sm">Bureau breakdown is unavailable.</p> : <ResponsiveContainer width="100%" height={300}>
            <BarChart data={bureauData}>
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="Cases" radius={[4, 4, 0, 0]}>
                {bureauData.map((d: any, i: number) => <Cell key={i} fill={d.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>}
        </ChartCard>
      </div>}
    </div>
  );
}
