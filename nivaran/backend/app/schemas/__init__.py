"""Pydantic schemas for all API request/response models."""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, field_validator, Field
from ..models import (
    UserRole, ComplaintStatus, ComplaintCategory, PriorityLevel,
    OverlapDecisionType, InstitutionVerificationStatus,
    DocumentVerificationStatus, DataSourceType
)



# ─── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    bureau_id: Optional[int]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.READ_ONLY
    bureau_id: Optional[int] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    bureau_id: Optional[int] = None
    is_active: Optional[bool] = None


# ─── Bureau ──────────────────────────────────────────────────────────────────

class BureauOut(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


# ─── Institution ─────────────────────────────────────────────────────────────

class InstitutionCreate(BaseModel):
    institution_id: str
    name: str
    state: Optional[str] = None
    district: Optional[str] = None
    region: Optional[str] = None
    address: Optional[str] = None
    institution_type: Optional[str] = None
    source_label: Optional[str] = "Synthetic Demonstration Record"
    source_reference: Optional[str] = None


class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    region: Optional[str] = None
    address: Optional[str] = None
    institution_type: Optional[str] = None
    verification_status: Optional[InstitutionVerificationStatus] = None
    source_label: Optional[str] = None


class InstitutionOut(BaseModel):
    id: int
    institution_id: str
    name: str
    state: Optional[str]
    district: Optional[str]
    region: Optional[str]
    address: Optional[str]
    institution_type: Optional[str]
    verification_status: InstitutionVerificationStatus
    source_label: Optional[str]
    source_reference: Optional[str]
    last_verified_date: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Complaint ───────────────────────────────────────────────────────────────

class ComplaintCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    description: str = Field(..., min_length=10)
    category: ComplaintCategory
    institution_id: Optional[int] = None
    institution_name_snapshot: Optional[str] = None
    source_channel: Optional[str] = None
    bureau_id: Optional[int] = None
    incident_date: Optional[datetime] = None
    target_disposal_date: Optional[datetime] = None
    is_anonymous: bool = False

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 3:
            raise ValueError("Title must contain at least 3 non-whitespace characters")
        return s

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 10:
            raise ValueError("Description must contain at least 10 non-whitespace characters")
        return s



class ComplaintUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ComplaintCategory] = None
    status: Optional[ComplaintStatus] = None
    bureau_id: Optional[int] = None
    assigned_officer_id: Optional[int] = None
    target_disposal_date: Optional[datetime] = None
    next_required_action: Optional[str] = None
    assigned_priority_level: Optional[PriorityLevel] = None


class ComplaintOut(BaseModel):
    id: int
    complaint_id: str
    institution_id: Optional[int]
    institution_name_snapshot: Optional[str]
    title: str
    description: str
    category: ComplaintCategory
    source_channel: Optional[str]
    bureau_id: Optional[int]
    assigned_officer_id: Optional[int]
    status: ComplaintStatus
    registration_date: datetime
    incident_date: Optional[datetime]
    target_disposal_date: Optional[datetime]
    last_action_date: Optional[datetime]
    next_required_action: Optional[str]
    evidence_assessment_status: Optional[str]
    completeness_score: Optional[float]
    calculated_priority_score: Optional[float]
    calculated_priority_level: Optional[PriorityLevel]
    assigned_priority_level: Optional[PriorityLevel]
    priority_explanation: Optional[str]
    data_source_label: Optional[str]
    is_anonymous: bool
    created_at: datetime
    updated_at: datetime
    bureau: Optional[BureauOut] = None
    assigned_officer: Optional[UserOut] = None

    class Config:
        from_attributes = True


class ComplaintListItem(BaseModel):
    id: int
    complaint_id: str
    title: str
    category: ComplaintCategory
    status: ComplaintStatus
    institution_name_snapshot: Optional[str]
    bureau_id: Optional[int]
    assigned_officer_id: Optional[int]
    registration_date: datetime
    target_disposal_date: Optional[datetime]
    calculated_priority_level: Optional[PriorityLevel]
    assigned_priority_level: Optional[PriorityLevel]
    data_source_label: Optional[str]

    class Config:
        from_attributes = True


# ─── Case Actions ────────────────────────────────────────────────────────────

class CaseActionCreate(BaseModel):
    action_type: str
    description: str
    metadata_json: Optional[Dict[str, Any]] = None


class CaseActionOut(BaseModel):
    id: int
    complaint_id: int
    actor_id: Optional[int]
    action_type: str
    description: str
    old_status: Optional[str]
    new_status: Optional[str]
    metadata_json: Optional[Dict[str, Any]]
    created_at: datetime
    actor: Optional[UserOut] = None

    class Config:
        from_attributes = True


# ─── Transfer ────────────────────────────────────────────────────────────────

class TransferRequest(BaseModel):
    target_bureau_id: Optional[int] = None
    target_officer_id: Optional[int] = None
    reason: str


# ─── Overlap Detection ───────────────────────────────────────────────────────

class OverlapResultOut(BaseModel):
    id: int
    primary_complaint_id: int
    candidate_complaint_id: int
    similarity_score: float
    institution_score: Optional[float]
    description_score: Optional[float]
    category_score: Optional[float]
    date_score: Optional[float]
    keyword_score: Optional[float]
    matching_keywords: Optional[List[str]]
    conflicting_info: Optional[str]
    missing_data_notes: Optional[str]
    algorithm_version: str
    review_status: str
    decision: Optional[OverlapDecisionType]
    decision_reason: Optional[str]
    decided_at: Optional[datetime]
    created_at: datetime
    primary_complaint: Optional[ComplaintListItem] = None
    candidate_complaint: Optional[ComplaintListItem] = None

    class Config:
        from_attributes = True


class OverlapDecisionRequest(BaseModel):
    decision: OverlapDecisionType
    reason: str


# ─── Priority ────────────────────────────────────────────────────────────────

class PriorityAssessmentOut(BaseModel):
    id: int
    complaint_id: int
    score: float
    priority_level: PriorityLevel
    urgency_contribution: Optional[float]
    impact_contribution: Optional[float]
    deadline_contribution: Optional[float]
    ageing_contribution: Optional[float]
    escalation_contribution: Optional[float]
    transfer_contribution: Optional[float]
    explanation: str
    missing_data_flags: Optional[List[str]]
    calculation_version: str
    calculated_at: datetime
    is_override: bool
    override_reason: Optional[str]

    class Config:
        from_attributes = True


class PriorityOverrideRequest(BaseModel):
    priority_level: PriorityLevel
    reason: str


# ─── Evidence Assessment ─────────────────────────────────────────────────────

class EvidenceAssessmentOut(BaseModel):
    id: int
    complaint_id: int
    completeness_score: Optional[float]
    evidence_readiness_score: Optional[float]
    institution_verified: bool
    date_consistency_ok: Optional[bool]
    document_count: int
    missing_fields: Optional[List[str]]
    consistency_issues: Optional[List[str]]
    status: str
    notes: Optional[str]
    assessed_at: datetime

    class Config:
        from_attributes = True


# ─── Documents ───────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: int
    complaint_id: int
    original_filename: str
    file_size_bytes: Optional[int]
    content_type: Optional[str]
    document_type: Optional[str]
    verification_status: DocumentVerificationStatus
    verification_notes: Optional[str]
    source_label: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentVerifyRequest(BaseModel):
    status: DocumentVerificationStatus
    notes: Optional[str] = None


# ─── Clarification ───────────────────────────────────────────────────────────

class ClarificationCreate(BaseModel):
    question: str


class ClarificationOut(BaseModel):
    id: int
    complaint_id: int
    question: str
    response: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Notifications ───────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: int
    complaint_id: Optional[int]
    title: str
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Audit Log ───────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime
    user: Optional[UserOut] = None

    class Config:
        from_attributes = True


# ─── Dashboard ───────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_complaints: int
    pending_complaints: int
    under_process: int
    disposed_complaints: int
    overdue_complaints: int
    critical_cases: int
    high_priority_cases: int
    pending_overlap_reviews: int
    pending_evidence_reviews: int
    status_distribution: List[Dict[str, Any]]
    bureau_workload: List[Dict[str, Any]]
    region_distribution: List[Dict[str, Any]]
    priority_distribution: List[Dict[str, Any]]
    monthly_trend: List[Dict[str, Any]]


# ─── Pagination ──────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    per_page: int
    pages: int


# ─── Assignment Records ───────────────────────────────────────────────────────

class AssignmentRecordOut(BaseModel):
    id: int
    complaint_id: int
    officer_id: Optional[int]
    previous_officer_id: Optional[int]
    assigned_by_id: Optional[int]
    bureau_id: Optional[int]
    assignment_type: str
    reason: Optional[str]
    officer_workload_at_assignment: Optional[int]
    assigned_at: datetime
    officer: Optional[UserOut] = None
    previous_officer: Optional[UserOut] = None
    assigned_by: Optional[UserOut] = None

    class Config:
        from_attributes = True


class ManualReassignRequest(BaseModel):
    target_officer_id: int
    reason: str


# ─── Inactivity Warnings ───────────────────────────────────────────────────────

class InactivityWarningOut(BaseModel):
    id: int
    complaint_id: int
    officer_id: Optional[int]
    warning_stage: str
    days_inactive: int
    last_meaningful_action_at: Optional[datetime]
    new_officer_id: Optional[int]
    notification_sent: bool
    supervisor_notified: bool
    created_at: datetime
    officer: Optional[UserOut] = None
    new_officer: Optional[UserOut] = None

    class Config:
        from_attributes = True


class InactivityExceptionCreate(BaseModel):
    reason: str
    expires_at: Optional[datetime] = None


class InactivityExceptionOut(BaseModel):
    id: int
    complaint_id: int
    authorized_by_id: int
    reason: str
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    revoked_at: Optional[datetime]
    revoked_by_id: Optional[int]
    authorized_by: Optional[UserOut] = None

    class Config:
        from_attributes = True


# Forward references
Token.model_rebuild()
