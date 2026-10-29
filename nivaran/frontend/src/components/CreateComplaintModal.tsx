import { useState } from 'react';
import { complaintsAPI } from '../lib/api';
import type { Bureau } from '../types';
import { X, Plus, Info } from 'lucide-react';
import toast from 'react-hot-toast';

const CATEGORIES = [
  ['scholarship_financial','Scholarship / Financial'],
  ['academic_examination','Academic / Examination'],
  ['faculty_related','Faculty Related'],
  ['infrastructure_facilities','Infrastructure / Facilities'],
  ['regulatory_compliance','Regulatory Compliance'],
  ['approval_related','Approval Related'],
  ['student_safety_welfare','Student Safety / Welfare'],
  ['administrative','Administrative'],
  ['other','Other'],
];

interface Props {
  bureaus: Bureau[];
  onClose: () => void;
  onCreated: () => void;
}

export default function CreateComplaintModal({ bureaus, onClose, onCreated }: Props) {
  const [form, setForm] = useState({
    title: '', description: '', category: '',
    bureau_id: '', source_channel: '',
    institution_name_snapshot: '', is_anonymous: false,
  });
  const [saving, setSaving] = useState(false);

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title || !form.description || !form.category) {
      toast.error('Title, description and category are required'); return;
    }
    setSaving(true);
    try {
      await complaintsAPI.create({
        ...form,
        bureau_id: form.bureau_id ? Number(form.bureau_id) : undefined,
      });
      toast.success('Complaint registered successfully');
      onCreated();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Failed to create complaint');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div>
            <h2 className="text-base font-semibold text-slate-100">Register New Complaint</h2>
            <p className="text-xs text-slate-500 mt-0.5">Enter the complaint details available to you; optional fields can be left blank.</p>
          </div>
          <button onClick={onClose} className="btn-ghost p-2" aria-label="Close complaint registration"><X size={16} /></button>
        </div>

        <form onSubmit={submit} className="p-6 space-y-4">
          <div>
            <label className="label">Complaint Title *</label>
            <input className="input" aria-label="Complaint title" placeholder="Brief summary of the complaint" value={form.title} onChange={(e) => set('title', e.target.value)} />
          </div>

          <div>
            <label className="label">Description *</label>
            <textarea
              className="input h-28 resize-none"
              aria-label="Complaint description"
              placeholder="Describe the complaint in detail…"
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label">Category *</label>
              <select className="select" aria-label="Complaint category" value={form.category} onChange={(e) => set('category', e.target.value)}>
                <option value="">Select category…</option>
                {CATEGORIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Bureau / Cell</label>
              <select className="select" aria-label="Bureau or cell" value={form.bureau_id} onChange={(e) => set('bureau_id', e.target.value)}>
                <option value="">Select bureau…</option>
                {bureaus.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label">Institution Name</label>
              <input className="input" aria-label="Institution name" placeholder="Institution name (if known)" value={form.institution_name_snapshot} onChange={(e) => set('institution_name_snapshot', e.target.value)} />
            </div>
            <div>
              <label className="label">Source / Channel</label>
              <input className="input" aria-label="Source or channel" placeholder="e.g., Email, Portal, Walk-in" value={form.source_channel} onChange={(e) => set('source_channel', e.target.value)} />
            </div>
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.is_anonymous} onChange={(e) => set('is_anonymous', e.target.checked)} className="rounded border-slate-600 bg-slate-800 text-indigo-500" />
            <span className="text-sm text-slate-300">Anonymous complaint</span>
          </label>

          <div className="flex items-start gap-2 p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
            <Info size={14} className="text-indigo-400 shrink-0 mt-0.5" />
            <p className="text-xs text-indigo-300">
              Priority will be calculated automatically. Evidence assessment will begin after registration.
            </p>
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary flex-1 justify-center">
              {saving ? 'Registering…' : <><Plus size={14} /> Register Complaint</>}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
