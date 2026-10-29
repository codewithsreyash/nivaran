// Shared type definitions for the frontend
export type PriorityLevel = 'critical' | 'high' | 'medium' | 'low';
export type ComplaintStatus =
  | 'registered' | 'under_initial_review' | 'under_process'
  | 'awaiting_information' | 'transferred' | 'escalated' | 'disposed' | 'closed';
export type ComplaintCategory =
  | 'scholarship_financial' | 'academic_examination' | 'faculty_related'
  | 'infrastructure_facilities' | 'regulatory_compliance' | 'approval_related'
  | 'student_safety_welfare' | 'administrative' | 'other';

export interface Complaint {
  id: number;
  complaint_id: string;
  title: string;
  description: string;
  category: ComplaintCategory;
  status: ComplaintStatus;
  institution_id?: number;
  institution_name_snapshot?: string;
  bureau_id?: number;
  assigned_officer_id?: number;
  registration_date: string;
  incident_date?: string;
  target_disposal_date?: string;
  last_action_date?: string;
  next_required_action?: string;
  evidence_assessment_status?: string;
  completeness_score?: number;
  calculated_priority_score?: number;
  calculated_priority_level?: PriorityLevel;
  assigned_priority_level?: PriorityLevel;
  priority_explanation?: string;
  data_source_label?: string;
  is_anonymous: boolean;
  created_at: string;
  updated_at: string;
  bureau?: Bureau;
  assigned_officer?: User;
}

/** Fields returned by the paginated complaint list endpoint. */
export interface ComplaintListItem {
  id: number;
  complaint_id: string;
  title: string;
  category: ComplaintCategory;
  status: ComplaintStatus;
  institution_name_snapshot?: string | null;
  bureau_id?: number | null;
  assigned_officer_id?: number | null;
  registration_date: string;
  target_disposal_date?: string | null;
  calculated_priority_level?: PriorityLevel | null;
  assigned_priority_level?: PriorityLevel | null;
  data_source_label?: string | null;
}

export interface Institution {
  id: number;
  institution_id: string;
  name: string;
  state?: string;
  district?: string;
  region?: string;
  address?: string;
  institution_type?: string;
  verification_status: string;
  source_label?: string;
  last_verified_date?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Bureau {
  id: number;
  name: string;
  code: string;
  description?: string;
  is_active: boolean;
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: string;
  bureau_id?: number;
  is_active: boolean;
  created_at: string;
}

export interface OverlapResult {
  id: number;
  primary_complaint_id: number;
  candidate_complaint_id: number;
  similarity_score: number;
  institution_score?: number;
  description_score?: number;
  category_score?: number;
  date_score?: number;
  keyword_score?: number;
  matching_keywords?: string[];
  conflicting_info?: string;
  missing_data_notes?: string;
  algorithm_version: string;
  review_status: string;
  decision?: string;
  decision_reason?: string;
  decided_at?: string;
  created_at: string;
  primary_complaint?: Complaint;
  candidate_complaint?: Complaint;
}

export interface PriorityAssessment {
  id: number;
  complaint_id: number;
  score: number;
  priority_level: PriorityLevel;
  urgency_contribution?: number;
  impact_contribution?: number;
  deadline_contribution?: number;
  ageing_contribution?: number;
  escalation_contribution?: number;
  transfer_contribution?: number;
  explanation: string;
  missing_data_flags?: string[];
  calculation_version: string;
  calculated_at: string;
  is_override: boolean;
  override_reason?: string;
}

export interface CaseAction {
  id: number;
  complaint_id: number;
  actor_id?: number;
  action_type: string;
  description: string;
  old_status?: string;
  new_status?: string;
  metadata_json?: Record<string, any>;
  created_at: string;
  actor?: User;
}

export interface DashboardData {
  total_complaints: number;
  pending_complaints: number;
  under_process: number;
  disposed_complaints: number;
  overdue_complaints: number;
  critical_cases: number;
  high_priority_cases: number;
  pending_overlap_reviews: number;
  pending_evidence_reviews: number;
  status_distribution: { status: string; count: number }[];
  bureau_workload: { bureau: string; count: number }[];
  priority_distribution: { priority: string; count: number }[];
  monthly_trend: { month: string; count: number }[];
}

export interface Notification {
  id: number;
  complaint_id?: number;
  title: string;
  message: string;
  notification_type: string;
  is_read: boolean;
  created_at: string;
}

export interface AuditLog {
  id: number;
  user_id?: number;
  action: string;
  resource_type?: string;
  resource_id?: string;
  details?: Record<string, any>;
  ip_address?: string;
  created_at: string;
  user?: User;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface EvidenceAssessment {
  id: number;
  complaint_id: number;
  completeness_score?: number;
  evidence_readiness_score?: number;
  institution_verified: boolean;
  date_consistency_ok?: boolean;
  document_count: number;
  missing_fields?: string[];
  consistency_issues?: string[];
  status: string;
  notes?: string;
  assessed_at: string;
}
