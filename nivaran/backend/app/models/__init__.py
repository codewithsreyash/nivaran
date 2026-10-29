"""
AICTE OneView — Database Models
All complaint records in this file are SYNTHETIC DEMONSTRATION DATA.
No real AICTE complaint records or personal data are used.
"""
import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, Enum,
    ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
from ..database import Base


# ─────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    BUREAU_OFFICER = "bureau_officer"
    SUPERVISORY_REVIEWER = "supervisory_reviewer"
    READ_ONLY = "read_only"


class InstitutionVerificationStatus(str, enum.Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    PENDING = "pending"
    DISPUTED = "disputed"


class ComplaintStatus(str, enum.Enum):
    REGISTERED = "registered"
    UNDER_INITIAL_REVIEW = "under_initial_review"
    UNDER_PROCESS = "under_process"
    AWAITING_INFORMATION = "awaiting_information"
    TRANSFERRED = "transferred"
    ESCALATED = "escalated"
    DISPOSED = "disposed"
    CLOSED = "closed"


class ComplaintCategory(str, enum.Enum):
    SCHOLARSHIP_FINANCIAL = "scholarship_financial"
    ACADEMIC_EXAMINATION = "academic_examination"
    FACULTY_RELATED = "faculty_related"
    INFRASTRUCTURE_FACILITIES = "infrastructure_facilities"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    APPROVAL_RELATED = "approval_related"
    STUDENT_SAFETY_WELFARE = "student_safety_welfare"
    ADMINISTRATIVE = "administrative"
    OTHER = "other"


class PriorityLevel(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OverlapDecisionType(str, enum.Enum):
    CONFIRMED_DUPLICATE = "confirmed_duplicate"
    RELATED_INDEPENDENT = "related_independent"
    UNRELATED = "unrelated"
    DEFERRED = "deferred"
    ESCALATED_FOR_REVIEW = "escalated_for_review"


class DocumentVerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    REQUIRES_REVIEW = "requires_review"


class DataSourceType(str, enum.Enum):
    OFFICIAL_IMPORTED = "official_imported"
    PUBLIC_IMPORTED = "public_imported"
    USER_SUPPLIED = "user_supplied"
    SYNTHETIC_DEMONSTRATION = "synthetic_demonstration"


# ─────────────────────────────────────────────
# User and Authentication Models
# ─────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=False)
    full_name = Column(String(200), nullable=False)
    hashed_password = Column(String(200), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.READ_ONLY)
    bureau_id = Column(Integer, ForeignKey("bureaus.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bureau = relationship("Bureau", back_populates="officers")
    audit_logs = relationship("AuditLog", back_populates="user")
    assigned_complaints = relationship("Complaint", back_populates="assigned_officer",
                                       foreign_keys="Complaint.assigned_officer_id")
    actions = relationship("CaseAction", back_populates="actor")


# ─────────────────────────────────────────────
# Bureau / Cell Model
# ─────────────────────────────────────────────

class Bureau(Base):
    __tablename__ = "bureaus"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    officers = relationship("User", back_populates="bureau")
    complaints = relationship("Complaint", back_populates="bureau")


# ─────────────────────────────────────────────
# Institution Model
# ─────────────────────────────────────────────

class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(300), nullable=False, index=True)
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    institution_type = Column(String(100), nullable=True)
    verification_status = Column(
        Enum(InstitutionVerificationStatus),
        default=InstitutionVerificationStatus.UNVERIFIED
    )
    source_label = Column(String(100), nullable=True)  # e.g. "Synthetic Demonstration Record"
    source_reference = Column(String(300), nullable=True)
    last_verified_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    complaints = relationship("Complaint", back_populates="institution")

    __table_args__ = ()


# ─────────────────────────────────────────────
# Complaint Model
# ─────────────────────────────────────────────

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(String(50), unique=True, index=True, nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    institution_name_snapshot = Column(String(300), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Enum(ComplaintCategory), nullable=False)
    source_channel = Column(String(100), nullable=True)
    bureau_id = Column(Integer, ForeignKey("bureaus.id"), nullable=True)
    assigned_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(Enum(ComplaintStatus), default=ComplaintStatus.REGISTERED, index=True)
    registration_date = Column(DateTime, default=datetime.utcnow)
    incident_date = Column(DateTime, nullable=True)
    target_disposal_date = Column(DateTime, nullable=True)
    last_action_date = Column(DateTime, nullable=True)
    next_required_action = Column(String(300), nullable=True)

    # Evidence assessment
    evidence_assessment_status = Column(String(100), default="Information Incomplete")
    completeness_score = Column(Float, nullable=True)
    evidence_readiness_score = Column(Float, nullable=True)

    # Priority
    calculated_priority_score = Column(Float, nullable=True)
    calculated_priority_level = Column(Enum(PriorityLevel), nullable=True)
    assigned_priority_level = Column(Enum(PriorityLevel), nullable=True)
    priority_explanation = Column(Text, nullable=True)
    priority_calculated_at = Column(DateTime, nullable=True)

    # Provenance
    data_source_label = Column(String(100), default="Synthetic Demonstration Record")
    is_anonymous = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    institution = relationship("Institution", back_populates="complaints")
    bureau = relationship("Bureau", back_populates="complaints")
    assigned_officer = relationship("User", back_populates="assigned_complaints",
                                    foreign_keys=[assigned_officer_id])
    actions = relationship("CaseAction", back_populates="complaint",
                           order_by="CaseAction.created_at")
    documents = relationship("SupportingDocument", back_populates="complaint")
    overlap_results_as_primary = relationship("OverlapResult",
                                               back_populates="primary_complaint",
                                               foreign_keys="OverlapResult.primary_complaint_id")
    overlap_results_as_candidate = relationship("OverlapResult",
                                                 back_populates="candidate_complaint",
                                                 foreign_keys="OverlapResult.candidate_complaint_id")
    priority_assessments = relationship("PriorityAssessment", back_populates="complaint",
                                        order_by="PriorityAssessment.calculated_at")
    escalation_events = relationship("EscalationEvent", back_populates="complaint")
    notifications = relationship("Notification", back_populates="complaint")
    evidence_assessments = relationship("EvidenceAssessment", back_populates="complaint")
    clarification_requests = relationship("ClarificationRequest", back_populates="complaint")

    __table_args__ = ()


# ─────────────────────────────────────────────
# Case Actions (Timeline)
# ─────────────────────────────────────────────

class CaseAction(Base):
    __tablename__ = "case_actions"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    old_status = Column(String(100), nullable=True)
    new_status = Column(String(100), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="actions")
    actor = relationship("User", back_populates="actions")


# ─────────────────────────────────────────────
# Case Relationships
# ─────────────────────────────────────────────

class CaseRelationship(Base):
    __tablename__ = "case_relationships"

    id = Column(Integer, primary_key=True, index=True)
    complaint_a_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    complaint_b_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    relationship_type = Column(String(50), nullable=False)  # duplicate, related, independent
    decision_reason = Column(Text, nullable=True)
    decided_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────
# Overlap Detection
# ─────────────────────────────────────────────

class OverlapResult(Base):
    __tablename__ = "overlap_results"

    id = Column(Integer, primary_key=True, index=True)
    primary_complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    candidate_complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    similarity_score = Column(Float, nullable=False)
    institution_score = Column(Float, nullable=True)
    description_score = Column(Float, nullable=True)
    category_score = Column(Float, nullable=True)
    date_score = Column(Float, nullable=True)
    keyword_score = Column(Float, nullable=True)
    matching_keywords = Column(JSON, nullable=True)
    conflicting_info = Column(Text, nullable=True)
    missing_data_notes = Column(Text, nullable=True)
    algorithm_version = Column(String(50), default="rules-v1")
    review_status = Column(String(50), default="pending")  # pending, reviewed, rejected
    decision = Column(Enum(OverlapDecisionType), nullable=True)
    decision_reason = Column(Text, nullable=True)
    decided_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    primary_complaint = relationship("Complaint", back_populates="overlap_results_as_primary",
                                     foreign_keys=[primary_complaint_id])
    candidate_complaint = relationship("Complaint", back_populates="overlap_results_as_candidate",
                                       foreign_keys=[candidate_complaint_id])


# ─────────────────────────────────────────────
# Priority Assessment
# ─────────────────────────────────────────────

class PriorityAssessment(Base):
    __tablename__ = "priority_assessments"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    score = Column(Float, nullable=False)
    priority_level = Column(Enum(PriorityLevel), nullable=False)
    urgency_contribution = Column(Float, nullable=True)
    impact_contribution = Column(Float, nullable=True)
    deadline_contribution = Column(Float, nullable=True)
    ageing_contribution = Column(Float, nullable=True)
    escalation_contribution = Column(Float, nullable=True)
    transfer_contribution = Column(Float, nullable=True)
    explanation = Column(Text, nullable=False)
    missing_data_flags = Column(JSON, nullable=True)
    calculation_version = Column(String(50), default="rules-v1")
    calculated_at = Column(DateTime, default=datetime.utcnow)
    is_override = Column(Boolean, default=False)
    override_reason = Column(Text, nullable=True)
    override_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    complaint = relationship("Complaint", back_populates="priority_assessments")


# ─────────────────────────────────────────────
# Documents
# ─────────────────────────────────────────────

class SupportingDocument(Base):
    __tablename__ = "supporting_documents"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    filename = Column(String(300), nullable=False)
    original_filename = Column(String(300), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    content_type = Column(String(100), nullable=True)
    document_type = Column(String(100), nullable=True)
    verification_status = Column(
        Enum(DocumentVerificationStatus),
        default=DocumentVerificationStatus.PENDING
    )
    verification_notes = Column(Text, nullable=True)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    source_label = Column(String(100), default="User-Supplied Dataset")
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="documents")


# ─────────────────────────────────────────────
# Evidence Assessment
# ─────────────────────────────────────────────

class EvidenceAssessment(Base):
    __tablename__ = "evidence_assessments"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    completeness_score = Column(Float, nullable=True)
    evidence_readiness_score = Column(Float, nullable=True)
    institution_verified = Column(Boolean, default=False)
    date_consistency_ok = Column(Boolean, nullable=True)
    document_count = Column(Integer, default=0)
    missing_fields = Column(JSON, nullable=True)
    consistency_issues = Column(JSON, nullable=True)
    status = Column(String(100), default="Information Incomplete")
    notes = Column(Text, nullable=True)
    assessed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assessed_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="evidence_assessments")


# ─────────────────────────────────────────────
# Escalation
# ─────────────────────────────────────────────

class EscalationEvent(Base):
    __tablename__ = "escalation_events"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    trigger_reason = Column(Text, nullable=False)
    escalated_to = Column(String(200), nullable=True)
    initiated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="escalation_events")


# ─────────────────────────────────────────────
# Notifications
# ─────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(300), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(100), nullable=False)
    is_read = Column(Boolean, default=False)
    trigger_key = Column(String(200), nullable=True, unique=True)  # prevents duplicates
    created_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="notifications")


# ─────────────────────────────────────────────
# Clarification Requests
# ─────────────────────────────────────────────

class ClarificationRequest(Base):
    __tablename__ = "clarification_requests"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    question = Column(Text, nullable=False)
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    response = Column(Text, nullable=True)
    response_received_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="clarification_requests")


# ─────────────────────────────────────────────
# Audit Log
# ─────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(200), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = ()


# ─────────────────────────────────────────────
# Data Sources and Import Jobs
# ─────────────────────────────────────────────

class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    source_type = Column(Enum(DataSourceType), nullable=False)
    url_or_path = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    licence = Column(String(200), nullable=True)
    has_sensitive_data = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    import_jobs = relationship("ImportJob", back_populates="data_source")


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True, index=True)
    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    filename = Column(String(300), nullable=True)
    status = Column(String(50), default="pending")
    total_rows = Column(Integer, nullable=True)
    imported_rows = Column(Integer, nullable=True)
    rejected_rows = Column(Integer, nullable=True)
    error_summary = Column(JSON, nullable=True)
    initiated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    data_source = relationship("DataSource", back_populates="import_jobs")


# ─────────────────────────────────────────────
# Model Registry (for future ML integration)
# ─────────────────────────────────────────────

class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    task = Column(String(100), nullable=False)
    training_dataset = Column(String(200), nullable=True)
    training_date = Column(DateTime, nullable=True)
    feature_definitions = Column(JSON, nullable=True)
    label_definitions = Column(JSON, nullable=True)
    evaluation_metrics = Column(JSON, nullable=True)
    known_limitations = Column(Text, nullable=True)
    approval_status = Column(String(50), default="not_approved")
    artifact_path = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────
# Assignment Record (Feature 1 — Assignment History)
# ─────────────────────────────────────────────

class AssignmentRecord(Base):
    """Immutable record of every assignment event for a complaint."""
    __tablename__ = "assignment_records"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    # The officer being assigned (null = unassigned state)
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # The officer who was previously assigned (null = first assignment)
    previous_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Who performed the assignment (system or user)
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    bureau_id = Column(Integer, ForeignKey("bureaus.id"), nullable=True)
    # 'auto', 'manual', 'inactivity_reassign', 'transfer'
    assignment_type = Column(String(50), nullable=False, default="auto")
    reason = Column(Text, nullable=True)
    # Workload snapshot at time of assignment
    officer_workload_at_assignment = Column(Integer, nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", foreign_keys=[complaint_id])
    officer = relationship("User", foreign_keys=[officer_id])
    previous_officer = relationship("User", foreign_keys=[previous_officer_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])


# ─────────────────────────────────────────────
# Inactivity Warning (Feature 2 — 10/20/30-day workflow)
# ─────────────────────────────────────────────

class InactivityWarning(Base):
    """Persistent record of each inactivity threshold breach."""
    __tablename__ = "inactivity_warnings"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # 'day_10', 'day_20', 'day_30_reassigned', 'day_30_no_replacement'
    warning_stage = Column(String(50), nullable=False)
    days_inactive = Column(Integer, nullable=False)
    last_meaningful_action_at = Column(DateTime, nullable=True)
    # For reassignment events
    new_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notification_sent = Column(Boolean, default=False)
    supervisor_notified = Column(Boolean, default=False)
    # Unique key to prevent duplicate warnings per stage
    dedup_key = Column(String(200), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", foreign_keys=[complaint_id])
    officer = relationship("User", foreign_keys=[officer_id])
    new_officer = relationship("User", foreign_keys=[new_officer_id])


# ─────────────────────────────────────────────
# Inactivity Exception (supervisor pause/hold)
# ─────────────────────────────────────────────

class InactivityException(Base):
    """Supervisor-approved pause of inactivity monitoring for a complaint."""
    __tablename__ = "inactivity_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    authorized_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    # If null, exception is open-ended; if set, monitoring resumes after this date
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    complaint = relationship("Complaint", foreign_keys=[complaint_id])
    authorized_by = relationship("User", foreign_keys=[authorized_by_id])
