import type { PriorityLevel, ComplaintStatus, ComplaintCategory } from '../types';

export function priorityBadge(level?: PriorityLevel | null): string {
  switch (level) {
    case 'critical': return 'badge-critical';
    case 'high':     return 'badge-high';
    case 'medium':   return 'badge-medium';
    case 'low':      return 'badge-low';
    default:         return 'badge-neutral';
  }
}

export function priorityLabel(level?: PriorityLevel | null): string {
  return level ? level.charAt(0).toUpperCase() + level.slice(1) : 'Unscored';
}

export function statusBadge(status?: ComplaintStatus | null): string {
  switch (status) {
    case 'registered':          return 'badge-info';
    case 'under_initial_review':return 'badge-info';
    case 'under_process':       return 'badge-warning';
    case 'awaiting_information':return 'badge-warning';
    case 'transferred':         return 'badge-neutral';
    case 'escalated':           return 'badge-critical';
    case 'disposed':            return 'badge-success';
    case 'closed':              return 'badge-neutral';
    default:                    return 'badge-neutral';
  }
}

export function statusLabel(status?: string | null): string {
  if (!status) return 'Unknown';
  return status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export function categoryLabel(cat?: ComplaintCategory | null): string {
  const map: Record<string, string> = {
    scholarship_financial:    'Scholarship / Financial',
    academic_examination:     'Academic / Examination',
    faculty_related:          'Faculty Related',
    infrastructure_facilities:'Infrastructure / Facilities',
    regulatory_compliance:    'Regulatory Compliance',
    approval_related:         'Approval Related',
    student_safety_welfare:   'Student Safety / Welfare',
    administrative:           'Administrative',
    other:                    'Other',
  };
  return cat ? (map[cat] ?? cat) : 'Unknown';
}

export function formatDate(iso?: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

export function isOverdue(targetDate?: string | null, status?: string): boolean {
  if (!targetDate || status === 'disposed' || status === 'closed') return false;
  return new Date(targetDate) < new Date();
}

export function daysSince(iso?: string | null): number | null {
  if (!iso) return null;
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
}

export function daysUntil(iso?: string | null): number | null {
  if (!iso) return null;
  return Math.floor((new Date(iso).getTime() - Date.now()) / 86400000);
}

export function verificationBadge(status?: string): string {
  switch (status) {
    case 'verified':   return 'badge-success';
    case 'pending':    return 'badge-warning';
    case 'disputed':   return 'badge-critical';
    default:           return 'badge-neutral';
  }
}
