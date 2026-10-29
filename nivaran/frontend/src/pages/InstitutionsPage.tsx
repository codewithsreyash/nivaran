import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { institutionsAPI } from '../lib/api';
import type { Institution } from '../types';
import { verificationBadge, formatDate } from '../lib/utils';
import { Building2, Search, Plus, MapPin, CheckCircle2, AlertCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { PageEmptyState, PageErrorState } from '../components/PageState';

export default function InstitutionsPage() {
  const { canWrite } = useAuth();
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ institution_id: '', name: '', state: '', district: '', region: '', institution_type: '' });
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const res = await institutionsAPI.list({ search: search || undefined, page, per_page: 20 });
      setInstitutions(res.data.items);
      setTotal(res.data.total);
      setPages(res.data.pages);
    } catch {
      setInstitutions([]);
      setTotal(0);
      setPages(1);
      setLoadError(true);
    } finally { setLoading(false); }
  }, [search, page]);

  useEffect(() => { load(); }, [load]);

  const createInstitution = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.institution_id || !form.name) { toast.error('ID and name required'); return; }
    setSaving(true);
    try {
      await institutionsAPI.create({ ...form, source_label: 'Synthetic Demonstration Record' });
      toast.success('Institution added');
      setShowAdd(false);
      setForm({ institution_id: '', name: '', state: '', district: '', region: '', institution_type: '' });
      load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Failed to add institution');
    } finally { setSaving(false); }
  };

  const vStatusClass: Record<string, string> = {
    verified: 'text-emerald-400', unverified: 'text-slate-500',
    pending: 'text-amber-400', disputed: 'text-rose-400',
  };
  const vStatusIcon: Record<string, any> = {
    verified: CheckCircle2, unverified: AlertCircle,
    pending: AlertCircle, disputed: AlertCircle,
  };

  return (
    <div className="space-y-5">
      <div className="page-header">
        <div>
          <h1 className="page-title">Institution Registry</h1>
          <p className="page-subtitle">{loadError ? 'Institution data unavailable' : loading ? 'Loading institution records…' : `${total} institutions`}</p>
        </div>
        {canWrite && (
          <button onClick={() => setShowAdd(!showAdd)} className="btn-primary">
            <Plus size={16} /> Add Institution
          </button>
        )}
      </div>

      {/* Add form */}
      {showAdd && (
        <div className="card border-indigo-500/30">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Add Institution (Synthetic)</h3>
          <form onSubmit={createInstitution} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="label">Institution ID *</label>
              <input className="input text-xs" placeholder="e.g. INST-MH-013" value={form.institution_id} onChange={(e) => setForm({ ...form, institution_id: e.target.value })} />
            </div>
            <div>
              <label className="label">Name *</label>
              <input className="input text-xs" placeholder="Full institution name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div>
              <label className="label">State</label>
              <input className="input text-xs" value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} />
            </div>
            <div>
              <label className="label">District</label>
              <input className="input text-xs" value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} />
            </div>
            <div>
              <label className="label">Region</label>
              <input className="input text-xs" placeholder="Northern / Southern / Western…" value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} />
            </div>
            <div>
              <label className="label">Type</label>
              <input className="input text-xs" placeholder="Engineering College / University…" value={form.institution_type} onChange={(e) => setForm({ ...form, institution_type: e.target.value })} />
            </div>
            <div className="col-span-2 flex gap-3">
              <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary flex-1 justify-center text-xs">Cancel</button>
              <button type="submit" disabled={saving} className="btn-primary flex-1 justify-center text-xs">
                {saving ? 'Adding…' : 'Add Institution'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Search */}
      <div className="card">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input className="input pl-9" aria-label="Search institutions" placeholder="Search institutions by name…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        </div>
      </div>

      {/* Grid */}
      {loadError ? <PageErrorState message="Institution records could not be loaded." onRetry={() => void load()} /> : loading ? (
        <div className="text-center py-12 text-slate-500 text-sm">Loading…</div>
      ) : institutions.length === 0 ? (
        <PageEmptyState title="No institutions found" detail={search ? 'Try a different search term.' : 'No institution records were returned.'} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {institutions.map((inst) => {
            const VIcon = vStatusIcon[inst.verification_status] ?? AlertCircle;
            return (
              <div key={inst.id} className="card hover:border-slate-700 transition-colors group">
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="w-9 h-9 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                    <Building2 size={16} className="text-slate-500" />
                  </div>
                  <div className={`flex items-center gap-1 text-xs ${vStatusClass[inst.verification_status]}`}>
                    <VIcon size={12} />
                    <span className="capitalize">{inst.verification_status}</span>
                  </div>
                </div>
                <h3 className="text-sm font-semibold text-slate-200 leading-tight mb-1">{inst.name}</h3>
                <p className="text-[11px] text-slate-500 font-mono mb-2">{inst.institution_id}</p>
                {(inst.district || inst.state) && (
                  <div className="flex items-center gap-1 text-[11px] text-slate-500 mb-2">
                    <MapPin size={10} /> {[inst.district, inst.state].filter(Boolean).join(', ')}
                  </div>
                )}
                {inst.institution_type && (
                  <span className="badge badge-neutral text-[10px]">{inst.institution_type}</span>
                )}
                <div className="mt-3 pt-2 border-t border-slate-800 flex justify-between items-center">
                  <span className="text-[10px] text-slate-600">{inst.source_label}</span>
                  {inst.region && <span className="text-[10px] text-slate-600">{inst.region}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex justify-center gap-2">
          <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="btn-secondary text-xs">← Prev</button>
          <span className="text-xs text-slate-500 self-center">{page} / {pages}</span>
          <button disabled={page >= pages} onClick={() => setPage(page + 1)} className="btn-secondary text-xs">Next →</button>
        </div>
      )}
    </div>
  );
}
