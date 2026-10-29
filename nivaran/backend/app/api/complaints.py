"""Complaint management API — the largest router in the application."""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from ..database import get_db
from ..dependencies import (
    ensure_bureau_access, get_bureau_scope, get_current_user,
    require_not_readonly, require_roles, scope_query_to_bureau,
)
from ..models import (
    Complaint, ComplaintStatus, ComplaintCategory, PriorityLevel, Bureau,
    CaseAction, OverlapResult, PriorityAssessment, User, UserRole,
    Notification, EvidenceAssessment, ClarificationRequest, SupportingDocument,
    AssignmentRecord, InactivityWarning, InactivityException
)
from ..schemas import (
    ComplaintCreate, ComplaintUpdate, ComplaintOut, ComplaintListItem,
    CaseActionCreate, CaseActionOut, TransferRequest,
    OverlapResultOut, OverlapDecisionRequest,
    PriorityAssessmentOut, PriorityOverrideRequest,
    EvidenceAssessmentOut, ClarificationCreate, ClarificationOut,
    AssignmentRecordOut, ManualReassignRequest,
    InactivityWarningOut, InactivityExceptionCreate, InactivityExceptionOut
)
from ..services.priority_engine import calculate_priority
from ..services.overlap_engine import detect_overlaps_for_complaint
from ..services.evidence_service import assess_complaint as run_evidence_assessment
from ..services.audit_service import log_action
from ..services.assignment_engine import assign_complaint

router = APIRouter(prefix="/api/complaints", tags=["complaints"])

VALID_TRANSITIONS = {
    ComplaintStatus.REGISTERED: [
        ComplaintStatus.UNDER_INITIAL_REVIEW, ComplaintStatus.AWAITING_INFORMATION,
        ComplaintStatus.TRANSFERRED, ComplaintStatus.CLOSED
    ],
    ComplaintStatus.UNDER_INITIAL_REVIEW: [
        ComplaintStatus.UNDER_PROCESS, ComplaintStatus.AWAITING_INFORMATION,
        ComplaintStatus.TRANSFERRED, ComplaintStatus.ESCALATED
    ],
    ComplaintStatus.UNDER_PROCESS: [
        ComplaintStatus.AWAITING_INFORMATION, ComplaintStatus.TRANSFERRED,
        ComplaintStatus.ESCALATED, ComplaintStatus.DISPOSED
    ],
    ComplaintStatus.AWAITING_INFORMATION: [
        ComplaintStatus.UNDER_PROCESS, ComplaintStatus.TRANSFERRED,
        ComplaintStatus.ESCALATED, ComplaintStatus.CLOSED
    ],
    ComplaintStatus.TRANSFERRED: [
        ComplaintStatus.UNDER_INITIAL_REVIEW, ComplaintStatus.UNDER_PROCESS, ComplaintStatus.ESCALATED
    ],
    ComplaintStatus.ESCALATED: [
        ComplaintStatus.UNDER_PROCESS, ComplaintStatus.DISPOSED, ComplaintStatus.CLOSED
    ],
    ComplaintStatus.DISPOSED: [ComplaintStatus.CLOSED],
    ComplaintStatus.CLOSED: [],
}


def _generate_complaint_id() -> str:
    now = datetime.utcnow()
    return f"AICTE-{now.year}-{now.strftime('%m')}-{str(uuid.uuid4().int)[:6].upper()}"


def check_complaint_write_access(complaint: Complaint, user: User) -> None:
    """Enforce role-based access control and cross-bureau write boundaries."""
    if user.role == UserRole.READ_ONLY:
        raise HTTPException(
            status_code=403,
            detail="Read-only users cannot modify complaints"
        )
    ensure_bureau_access(user, complaint.bureau_id)


def check_complaint_read_access(complaint: Complaint, user: User) -> None:
    ensure_bureau_access(user, complaint.bureau_id)



# ─── List & Search ───────────────────────────────────────────────────────────

@router.get("", response_model=dict)
def list_complaints(
    search: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    bureau_id: Optional[int] = None,
    officer_id: Optional[int] = None,
    priority: Optional[str] = None,
    institution_id: Optional[int] = None,
    overdue_only: bool = False,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = "registration_date",
    sort_desc: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Complaint).options(
        joinedload(Complaint.bureau),
        joinedload(Complaint.assigned_officer),
    )
    q = scope_query_to_bureau(q, Complaint.bureau_id, current_user)
    if search:
        q = q.filter(or_(
            Complaint.title.ilike(f"%{search}%"),
            Complaint.complaint_id.ilike(f"%{search}%"),
            Complaint.institution_name_snapshot.ilike(f"%{search}%"),
        ))
    if status:
        q = q.filter(Complaint.status == status)
    if category:
        q = q.filter(Complaint.category == category)
    if bureau_id:
        q = q.filter(Complaint.bureau_id == bureau_id)
    if officer_id:
        q = q.filter(Complaint.assigned_officer_id == officer_id)
    if priority:
        q = q.filter(
            or_(Complaint.assigned_priority_level == priority,
                Complaint.calculated_priority_level == priority)
        )
    if institution_id:
        q = q.filter(Complaint.institution_id == institution_id)
    if overdue_only:
        q = q.filter(
            Complaint.target_disposal_date < datetime.utcnow(),
            Complaint.status.notin_(["disposed", "closed"])
        )

    col = getattr(Complaint, sort_by, Complaint.registration_date)
    q = q.order_by(col.desc() if sort_desc else col.asc())

    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [ComplaintListItem.model_validate(c) for c in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


# ─── Create ──────────────────────────────────────────────────────────────────

@router.post("", response_model=ComplaintOut, status_code=201)
def create_complaint(
    payload: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_readonly),
):
    # Rapid duplicate submission guard (identical title, institution, category within 30s)
    cutoff = datetime.utcnow() - timedelta(seconds=30)
    existing_dup = db.query(Complaint).filter(
        Complaint.title == payload.title.strip(),
        Complaint.category == payload.category,
        Complaint.registration_date >= cutoff,
        Complaint.institution_name_snapshot == payload.institution_name_snapshot,
    ).first()
    if existing_dup:
        raise HTTPException(
            status_code=409,
            detail=f"Identical complaint was recently registered as {existing_dup.complaint_id}. Duplicate submission prevented."
        )

    # Date sanity checks
    if payload.incident_date and payload.target_disposal_date:
        if payload.target_disposal_date < payload.incident_date:
            raise HTTPException(
                status_code=422,
                detail="Target disposal date cannot precede the incident date."
            )

    scope = get_bureau_scope(current_user)
    if scope is not None:
        if payload.bureau_id is not None and payload.bureau_id != scope:
            raise HTTPException(status_code=403, detail="Cannot register a complaint outside your assigned bureau")
        payload.bureau_id = scope

    complaint = Complaint(
        complaint_id=_generate_complaint_id(),
        **payload.model_dump(),
    )
    db.add(complaint)
    db.flush()

    # Initial priority calculation
    result = calculate_priority(complaint)
    complaint.calculated_priority_score = result["score"]
    complaint.calculated_priority_level = result["priority_level"]
    complaint.priority_explanation = result["explanation"]
    complaint.priority_calculated_at = result["calculated_at"]

    pa = PriorityAssessment(
        complaint_id=complaint.id,
        **{k: v for k, v in result.items()
           if k in ["score", "priority_level", "urgency_contribution", "impact_contribution",
                    "deadline_contribution", "ageing_contribution", "escalation_contribution",
                    "transfer_contribution", "explanation", "missing_data_flags",
                    "calculation_version", "calculated_at"]},
    )
    db.add(pa)

    action = CaseAction(
        complaint_id=complaint.id,
        actor_id=current_user.id,
        action_type="complaint.registered",
        description=f"Complaint registered by {current_user.full_name}.",
        new_status=ComplaintStatus.REGISTERED.value,
    )
    db.add(action)

    # Automatic officer assignment
    assignment_result = assign_complaint(
        db=db,
        complaint=complaint,
        acting_user_id=current_user.id,
        assignment_type="auto"
    )

    db.commit()
    db.refresh(complaint)

    log_action(db, "complaint.created", user_id=current_user.id,
               resource_type="complaint", resource_id=complaint.id,
               details={"complaint_id": complaint.complaint_id, "assignment": assignment_result})
    return ComplaintOut.model_validate(complaint)


# ─── Get One ─────────────────────────────────────────────────────────────────

@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = db.query(Complaint).options(
        joinedload(Complaint.bureau),
        joinedload(Complaint.assigned_officer),
        joinedload(Complaint.institution),
    ).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    check_complaint_read_access(complaint, current_user)
    return ComplaintOut.model_validate(complaint)


# ─── Update ──────────────────────────────────────────────────────────────────

@router.patch("/{complaint_id}", response_model=ComplaintOut)
def update_complaint(
    complaint_id: int,
    payload: ComplaintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_readonly),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")

    check_complaint_write_access(complaint, current_user)

    updates = payload.model_dump(exclude_none=True)
    ownership_fields = {"bureau_id", "assigned_officer_id"} & payload.model_fields_set
    if get_bureau_scope(current_user) is not None and ownership_fields:
        raise HTTPException(status_code=403, detail="Use transfer or reassignment workflows to change complaint ownership")

    old_bureau_id = complaint.bureau_id
    old_officer_id = complaint.assigned_officer_id
    target_bureau_id = payload.bureau_id if "bureau_id" in ownership_fields else old_bureau_id
    target_officer_id = payload.assigned_officer_id if "assigned_officer_id" in ownership_fields else old_officer_id

    if ownership_fields:
        if target_bureau_id is not None:
            target_bureau = db.query(Bureau).filter(
                Bureau.id == target_bureau_id,
                Bureau.is_active == True,
            ).first()
            if not target_bureau:
                raise HTTPException(status_code=422, detail="Target bureau does not exist or is inactive")
        if target_officer_id is not None:
            target_officer = db.query(User).filter(User.id == target_officer_id).first()
            if (
                not target_officer or not target_officer.is_active
                or target_officer.role != UserRole.BUREAU_OFFICER
                or target_bureau_id is None
                or target_officer.bureau_id != target_bureau_id
            ):
                raise HTTPException(status_code=422, detail="Target officer must be active and belong to the target bureau")
        for field in ownership_fields:
            updates[field] = getattr(payload, field)

    # Validate status transition
    if "status" in updates:
        new_status = updates["status"]
        allowed = VALID_TRANSITIONS.get(complaint.status, [])
        if new_status not in allowed:
            raise HTTPException(
                400,
                f"Invalid transition from {complaint.status.value} to {new_status.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )
        old_status = complaint.status
        action = CaseAction(
            complaint_id=complaint.id,
            actor_id=current_user.id,
            action_type="status.changed",
            description=f"Status changed from {old_status.value} to {new_status.value}.",
            old_status=old_status.value,
            new_status=new_status.value,
        )
        db.add(action)

    for k, v in updates.items():
        setattr(complaint, k, v)

    if ownership_fields and (
        target_bureau_id != old_bureau_id or target_officer_id != old_officer_id
    ):
        db.add(AssignmentRecord(
            complaint_id=complaint.id,
            officer_id=target_officer_id,
            previous_officer_id=old_officer_id,
            assigned_by_id=current_user.id,
            bureau_id=target_bureau_id,
            assignment_type="manual",
            reason="Ownership updated through privileged complaint patch",
        ))

    complaint.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(complaint)
    log_action(db, "complaint.updated", user_id=current_user.id,
               resource_type="complaint", resource_id=complaint.id, details=updates)
    return ComplaintOut.model_validate(complaint)


# ─── Actions ─────────────────────────────────────────────────────────────────

@router.post("/{complaint_id}/actions", response_model=CaseActionOut, status_code=201)
def add_action(
    complaint_id: int,
    payload: CaseActionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_readonly),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")

    check_complaint_write_access(complaint, current_user)

    action = CaseAction(
        complaint_id=complaint.id,
        actor_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(action)
    complaint.last_action_date = datetime.utcnow()
    complaint.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(action)

    log_action(db, "complaint.action_added", user_id=current_user.id,
               resource_type="complaint", resource_id=complaint.id,
               details={"action_type": action.action_type})
    return CaseActionOut.model_validate(action)


@router.get("/{complaint_id}/actions", response_model=List[CaseActionOut])
def get_actions(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    check_complaint_read_access(complaint, current_user)
    return [
        CaseActionOut.model_validate(a)
        for a in db.query(CaseAction)
            .filter(CaseAction.complaint_id == complaint_id)
            .options(joinedload(CaseAction.actor))
            .order_by(CaseAction.created_at.desc())
            .all()
    ]


# ─── Transfer ────────────────────────────────────────────────────────────────

@router.post("/{complaint_id}/transfer", response_model=ComplaintOut)
def transfer_complaint(
    complaint_id: int,
    payload: TransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_readonly),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")

    check_complaint_write_access(complaint, current_user)

    if complaint.status in (ComplaintStatus.CLOSED, ComplaintStatus.DISPOSED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transfer a complaint in {complaint.status.value} status."
        )

    old_bureau = complaint.bureau_id
    old_officer = complaint.assigned_officer_id

    allowed = VALID_TRANSITIONS.get(complaint.status, [])
    if ComplaintStatus.TRANSFERRED not in allowed and complaint.status != ComplaintStatus.TRANSFERRED:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition from {complaint.status.value} to transferred. Allowed: {[s.value for s in allowed]}"
        )

    target_bureau_id = payload.target_bureau_id if payload.target_bureau_id is not None else old_bureau
    target_bureau = None
    if target_bureau_id is not None:
        target_bureau = db.query(Bureau).filter(
            Bureau.id == target_bureau_id,
            Bureau.is_active == True,
        ).first()
        if not target_bureau:
            raise HTTPException(status_code=422, detail="Target bureau does not exist or is inactive")

    if payload.target_officer_id is not None:
        target_officer = db.query(User).filter(User.id == payload.target_officer_id).first()
        if (
            not target_officer or not target_officer.is_active
            or target_officer.role != UserRole.BUREAU_OFFICER
            or target_bureau is None
            or target_officer.bureau_id != target_bureau_id
        ):
            raise HTTPException(status_code=422, detail="Target officer must be active and belong to the target bureau")
        resulting_officer_id = target_officer.id
    elif target_bureau_id != old_bureau:
        # A transfer to a different bureau must not carry the previous bureau's assignee.
        resulting_officer_id = None
    elif old_officer is not None:
        old_assignee = db.query(User).filter(User.id == old_officer).first()
        resulting_officer_id = (
            old_officer
            if old_assignee and old_assignee.is_active
            and old_assignee.role == UserRole.BUREAU_OFFICER
            and old_assignee.bureau_id == target_bureau_id
            else None
        )
    else:
        resulting_officer_id = None

    old_status = complaint.status
    complaint.bureau_id = target_bureau_id
    complaint.assigned_officer_id = resulting_officer_id
    complaint.status = ComplaintStatus.TRANSFERRED

    db.add(AssignmentRecord(
        complaint_id=complaint.id,
        officer_id=resulting_officer_id,
        previous_officer_id=old_officer,
        assigned_by_id=current_user.id,
        bureau_id=target_bureau_id,
        assignment_type="transfer",
        reason=payload.reason,
    ))

    action = CaseAction(
        complaint_id=complaint.id,
        actor_id=current_user.id,
        action_type="complaint.transferred",
        description=f"Transferred to Bureau {target_bureau_id}. Reason: {payload.reason}",
        old_status=old_status.value,
        new_status=ComplaintStatus.TRANSFERRED.value,
        metadata_json={
            "from_bureau": old_bureau,
            "to_bureau": target_bureau_id,
            "from_officer": old_officer,
            "to_officer": resulting_officer_id,
            "reason": payload.reason,
        },
    )
    db.add(action)
    db.flush()

    # Recalculate priority to account for transfer penalty
    transfer_count = db.query(CaseAction).filter(
        CaseAction.complaint_id == complaint.id,
        CaseAction.action_type == "complaint.transferred"
    ).count()

    p_res = calculate_priority(complaint, transfer_count)
    complaint.calculated_priority_score = p_res["score"]
    complaint.calculated_priority_level = p_res["priority_level"]
    complaint.priority_explanation = p_res["explanation"]
    complaint.priority_calculated_at = p_res["calculated_at"]

    pa = PriorityAssessment(
        complaint_id=complaint.id,
        **{k: v for k, v in p_res.items()
           if k in ["score", "priority_level", "urgency_contribution", "impact_contribution",
                    "deadline_contribution", "ageing_contribution", "escalation_contribution",
                    "transfer_contribution", "explanation", "missing_data_flags",
                    "calculation_version", "calculated_at"]},
    )
    db.add(pa)

    complaint.last_action_date = datetime.utcnow()
    complaint.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(complaint)

    log_action(db, "complaint.transferred", user_id=current_user.id,
               resource_type="complaint", resource_id=complaint.id,
               details={"from_bureau": old_bureau, "to_bureau": target_bureau_id,
                        "from_officer": old_officer, "to_officer": resulting_officer_id,
                        "reason": payload.reason})
    return ComplaintOut.model_validate(complaint)



# ─── Overlap Detection ───────────────────────────────────────────────────────

@router.post("/{complaint_id}/detect-overlaps")
def detect_overlaps(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_readonly),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    check_complaint_write_access(complaint, current_user)
    results = detect_overlaps_for_complaint(db, complaint)
    log_action(db, "overlap.detected", user_id=current_user.id,
               resource_type="complaint", resource_id=complaint.id,
               details={"found": len(results)})
    return {"detected": len(results), "message": f"Found {len(results)} potential overlap(s)."}


@router.get("/{complaint_id}/overlaps", response_model=List[OverlapResultOut])
def get_overlaps(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    check_complaint_read_access(complaint, current_user)
    query = db.query(OverlapResult).filter(
        OverlapResult.primary_complaint_id == complaint_id
    ).options(
        joinedload(OverlapResult.candidate_complaint),
    )
    scope = get_bureau_scope(current_user)
    if scope is not None:
        query = query.filter(OverlapResult.candidate_complaint.has(Complaint.bureau_id == scope))
    results = query.all()
    return [OverlapResultOut.model_validate(r) for r in results]


# ─── Priority ─────────────────────────────────────────────────────────────────

@router.post("/{complaint_id}/calculate-priority", response_model=PriorityAssessmentOut)
def calculate_priority_route(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_readonly),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    check_complaint_write_access(complaint, current_user)

    transfer_count = db.query(CaseAction).filter(
        CaseAction.complaint_id == complaint.id,
        CaseAction.action_type == "complaint.transferred"
    ).count()

    result = calculate_priority(complaint, transfer_count)

    complaint.calculated_priority_score = result["score"]
    complaint.calculated_priority_level = result["priority_level"]
    complaint.priority_explanation = result["explanation"]
    complaint.priority_calculated_at = result["calculated_at"]

    pa = PriorityAssessment(
        complaint_id=complaint.id,
        **{k: v for k, v in result.items()
           if k in ["score", "priority_level", "urgency_contribution", "impact_contribution",
                    "deadline_contribution", "ageing_contribution", "escalation_contribution",
                    "transfer_contribution", "explanation", "missing_data_flags",
                    "calculation_version", "calculated_at"]},
    )
    db.add(pa)
    db.commit()
    db.refresh(pa)
    return PriorityAssessmentOut.model_validate(pa)


@router.get("/{complaint_id}/priority-history", response_model=List[PriorityAssessmentOut])
def priority_history(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    check_complaint_read_access(complaint, current_user)
    assessments = db.query(PriorityAssessment).filter(
        PriorityAssessment.complaint_id == complaint_id
    ).order_by(PriorityAssessment.calculated_at.desc()).all()
    return [PriorityAssessmentOut.model_validate(a) for a in assessments]


@router.post("/{complaint_id}/priority-override", response_model=PriorityAssessmentOut)
def priority_override(
    complaint_id: int,
    payload: PriorityOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISORY_REVIEWER)),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")

    complaint.assigned_priority_level = payload.priority_level
    pa = PriorityAssessment(
        complaint_id=complaint.id,
        score=complaint.calculated_priority_score or 0,
        priority_level=payload.priority_level,
        explanation=f"Manual override by {current_user.full_name}. Reason: {payload.reason}",
        missing_data_flags=[],
        calculation_version="manual-override",
        calculated_at=datetime.utcnow(),
        is_override=True,
        override_reason=payload.reason,
        override_by_id=current_user.id,
    )
    db.add(pa)
    db.commit()
    db.refresh(pa)
    log_action(db, "priority.overridden", user_id=current_user.id,
               resource_type="complaint", resource_id=complaint_id,
               details={"new_priority": payload.priority_level.value, "reason": payload.reason})
    return PriorityAssessmentOut.model_validate(pa)


# ─── Evidence Assessment ─────────────────────────────────────────────────────

@router.post("/{complaint_id}/assess", response_model=EvidenceAssessmentOut)
def assess_evidence(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_readonly),
):
    complaint = db.query(Complaint).options(
        joinedload(Complaint.institution)
    ).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    check_complaint_write_access(complaint, current_user)
    assessment = run_evidence_assessment(db, complaint, assessor_id=current_user.id)
    log_action(db, "evidence.assessed", user_id=current_user.id,
               resource_type="complaint", resource_id=complaint.id,
               details={"status": assessment.status, "completeness_score": assessment.completeness_score})
    return EvidenceAssessmentOut.model_validate(assessment)


@router.get("/{complaint_id}/assessment", response_model=List[EvidenceAssessmentOut])
def get_assessments(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    check_complaint_read_access(complaint, current_user)
    assessments = db.query(EvidenceAssessment).filter(
        EvidenceAssessment.complaint_id == complaint_id
    ).order_by(EvidenceAssessment.assessed_at.desc()).all()
    return [EvidenceAssessmentOut.model_validate(a) for a in assessments]


# ─── Clarifications ──────────────────────────────────────────────────────────

@router.post("/{complaint_id}/clarifications", response_model=ClarificationOut, status_code=201)
def request_clarification(
    complaint_id: int,
    payload: ClarificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_readonly),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    check_complaint_write_access(complaint, current_user)
    cr = ClarificationRequest(
        complaint_id=complaint.id,
        question=payload.question,
        requested_by_id=current_user.id,
    )
    db.add(cr)
    complaint.status = ComplaintStatus.AWAITING_INFORMATION
    complaint.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cr)
    return ClarificationOut.model_validate(cr)


@router.get("/{complaint_id}/clarifications", response_model=List[ClarificationOut])
def get_clarifications(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    check_complaint_read_access(complaint, current_user)
    clarifications = db.query(ClarificationRequest).filter(
        ClarificationRequest.complaint_id == complaint_id
    ).order_by(ClarificationRequest.created_at.desc()).all()
    return [ClarificationOut.model_validate(c) for c in clarifications]


# ─── Assignment History ───────────────────────────────────────────────────────

@router.get("/{complaint_id}/assignments", response_model=List[AssignmentRecordOut])
def get_assignment_history(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    check_complaint_read_access(complaint, current_user)

    records = db.query(AssignmentRecord).filter(
        AssignmentRecord.complaint_id == complaint_id
    ).options(
        joinedload(AssignmentRecord.officer),
        joinedload(AssignmentRecord.previous_officer),
        joinedload(AssignmentRecord.assigned_by),
    ).order_by(AssignmentRecord.assigned_at.desc()).all()
    return [AssignmentRecordOut.model_validate(r) for r in records]


@router.post("/{complaint_id}/reassign", response_model=ComplaintOut)
def manual_reassign(
    complaint_id: int,
    payload: ManualReassignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISORY_REVIEWER)),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")

    if complaint.status in (ComplaintStatus.CLOSED, ComplaintStatus.DISPOSED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reassign a complaint in {complaint.status.value} status."
        )

    target_officer = db.query(User).filter(User.id == payload.target_officer_id).first()
    if (
        not target_officer or not target_officer.is_active
        or target_officer.role != UserRole.BUREAU_OFFICER
        or target_officer.bureau_id is None
        or (complaint.bureau_id is not None and target_officer.bureau_id != complaint.bureau_id)
    ):
        raise HTTPException(status_code=422, detail="Target officer must be active and belong to the complaint bureau")
    target_bureau = db.query(Bureau).filter(
        Bureau.id == target_officer.bureau_id,
        Bureau.is_active == True,
    ).first()
    if not target_bureau:
        raise HTTPException(status_code=422, detail="Target officer's bureau does not exist or is inactive")
    if complaint.bureau_id is None:
        complaint.bureau_id = target_officer.bureau_id

    assignment_result = assign_complaint(
        db=db,
        complaint=complaint,
        acting_user_id=current_user.id,
        force_officer_id=payload.target_officer_id,
        reason=payload.reason,
        assignment_type="manual"
    )

    db.commit()
    db.refresh(complaint)

    log_action(db, "complaint.reassigned", user_id=current_user.id,
               resource_type="complaint", resource_id=complaint.id,
               details={"to_officer_id": payload.target_officer_id, "reason": payload.reason})
    return ComplaintOut.model_validate(complaint)


# ─── Inactivity Management ────────────────────────────────────────────────────

@router.get("/{complaint_id}/inactivity-warnings", response_model=List[InactivityWarningOut])
def get_inactivity_warnings(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    check_complaint_read_access(complaint, current_user)

    warnings = db.query(InactivityWarning).filter(
        InactivityWarning.complaint_id == complaint_id
    ).options(
        joinedload(InactivityWarning.officer),
        joinedload(InactivityWarning.new_officer),
    ).order_by(InactivityWarning.created_at.desc()).all()
    return [InactivityWarningOut.model_validate(w) for w in warnings]


@router.post("/{complaint_id}/inactivity-exceptions", response_model=InactivityExceptionOut, status_code=201)
def create_inactivity_exception(
    complaint_id: int,
    payload: InactivityExceptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISORY_REVIEWER)),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")

    exception = InactivityException(
        complaint_id=complaint.id,
        authorized_by_id=current_user.id,
        reason=payload.reason,
        expires_at=payload.expires_at,
    )
    db.add(exception)
    db.commit()
    db.refresh(exception)

    log_action(db, "inactivity.exception_created", user_id=current_user.id,
               resource_type="complaint", resource_id=complaint.id,
               details={"reason": payload.reason, "expires_at": payload.expires_at})
    return InactivityExceptionOut.model_validate(exception)


@router.delete("/{complaint_id}/inactivity-exceptions/{exception_id}")
def revoke_inactivity_exception(
    complaint_id: int,
    exception_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISORY_REVIEWER)),
):
    exception = db.query(InactivityException).filter(
        InactivityException.id == exception_id,
        InactivityException.complaint_id == complaint_id
    ).first()
    if not exception:
        raise HTTPException(404, "Exception not found")

    exception.is_active = False
    exception.revoked_at = datetime.utcnow()
    exception.revoked_by_id = current_user.id
    db.commit()

    log_action(db, "inactivity.exception_revoked", user_id=current_user.id,
               resource_type="complaint", resource_id=complaint_id,
               details={"exception_id": exception_id})
    return {"message": "Exception revoked"}
