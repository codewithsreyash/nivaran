import { Database, AlertCircle } from 'lucide-react';

export default function DataSourcesPage() {
  return (
    <div className="space-y-5">
      <div className="page-header">
        <div>
          <h1 className="page-title">Data Sources</h1>
          <p className="page-subtitle">Source metadata, provenance, and licensing</p>
        </div>
      </div>

      {/* Warning */}
      <div className="card bg-amber-500/10 border-amber-500/20">
        <div className="flex items-start gap-3">
          <AlertCircle size={16} className="text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-900 mb-1">Data source metadata is not connected</p>
            <p className="text-sm text-amber-900">
              The current backend does not provide a data-source registry endpoint. Record counts, approvals,
              licensing, and source provenance are therefore unavailable on this page.
            </p>
          </div>
        </div>
      </div>

      <div className="card flex items-start gap-3">
        <Database size={19} className="text-slate-500 shrink-0" aria-hidden="true" />
        <div>
          <h2 className="text-sm font-semibold text-slate-800">Registry not connected</h2>
          <p className="text-sm text-slate-600 mt-1">Connect a verified source registry before presenting source counts, approval status, or licensing details.</p>
        </div>
      </div>
    </div>
  );
}
