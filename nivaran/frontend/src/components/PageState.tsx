import { AlertTriangle, RefreshCw } from 'lucide-react';

export function PageErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="page-error-state" role="alert">
      <AlertTriangle size={19} aria-hidden="true" />
      <p>{message}</p>
      <button className="btn-secondary" onClick={onRetry}><RefreshCw size={14} aria-hidden="true" /> Retry</button>
    </div>
  );
}

export function PageLoadingState({ label = 'Loading data' }: { label?: string }) {
  return <div className="page-loading-state" role="status" aria-live="polite"><span className="loading-spinner" aria-hidden="true" />{label}</div>;
}

export function PageEmptyState({ title, detail }: { title: string; detail?: string }) {
  return <div className="page-empty-state"><h2>{title}</h2>{detail && <p>{detail}</p>}</div>;
}
