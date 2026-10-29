"""Dashboard, reports, priority queue, overlap review, users, audit logs."""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import extract, func
from ..database import get_db
from ..dependencies import (
    get_bureau_scope, get_current_user, require_admin, require_not_readonly,
    require_roles, scope_query_to_bureau,
)
from ..models import (
    Complaint, ComplaintStatus, ComplaintCategory, PriorityLevel, OverlapResult,
    User, UserRole, AuditLog, Notification, Bureau, EvidenceAssessment,
    InactivityWarning, InactivityException
)
from ..schemas import (
    UserOut, UserCreate, UserUpdate,
    AuditLogOut, NotificationOut,
    OverlapResultOut, OverlapDecisionRequest,
    InactivityWarningOut, InactivityExceptionOut
)
from ..auth import hash_password
from ..services.audit_service import log_action


def _scope_overlap_query(query, bureau_scope: Optional[int]):
    if bureau_scope is None:
        return query
    return query.filter(
        OverlapResult.primary_complaint.has(Complaint.bureau_id == bureau_scope),
        OverlapResult.candidate_complaint.has(Complaint.bureau_id == bureau_scope),
    )


def _resolve_report_bureau(current_user: User, requested_bureau_id: Optional[int]) -> Optional[int]:
    scope = get_bureau_scope(current_user)
    if scope is not None:
        if requested_bureau_id is not None and requested_bureau_id != scope:
            if current_user.role == UserRole.BUREAU_OFFICER:
                detail = f"Access denied. Bureau officers can only export data for their assigned bureau ({scope})."
            else:
                detail = "Cannot access reports outside assigned bureau"
            raise HTTPException(status_code=403, detail=detail)
        return scope
    return requested_bureau_id

# ─── Dashboard ───────────────────────────────────────────────────────────────
dashboard_router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@dashboard_router.get("")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.utcnow()

    bureau_scope = get_bureau_scope(current_user)
    visible_ids_query = db.query(Complaint.id)
    if bureau_scope is not None:
        visible_ids_query = visible_ids_query.filter(Complaint.bureau_id == bureau_scope)
    visible_ids = visible_ids_query

    def complaints_query():
        return db.query(Complaint).filter(Complaint.id.in_(visible_ids))

    total = complaints_query().count()
    pending = complaints_query().filter(
        Complaint.status.in_([
            ComplaintStatus.REGISTERED,
            ComplaintStatus.UNDER_INITIAL_REVIEW,
            ComplaintStatus.AWAITING_INFORMATION,
            ComplaintStatus.TRANSFERRED,
        ])
    ).count()
    under_process = complaints_query().filter(
        Complaint.status.in_([
            ComplaintStatus.UNDER_PROCESS,
            ComplaintStatus.ESCALATED,
        ])
    ).count()
    disposed = complaints_query().filter(
        Complaint.status.in_([ComplaintStatus.DISPOSED, ComplaintStatus.CLOSED])
    ).count()
    overdue = complaints_query().filter(
        Complaint.target_disposal_date < now,
        Complaint.status.notin_([
            ComplaintStatus.DISPOSED.value, ComplaintStatus.CLOSED.value
        ])
    ).count()
    critical = complaints_query().filter(
        Complaint.calculated_priority_level == PriorityLevel.CRITICAL
    ).count()
    high = complaints_query().filter(
        Complaint.calculated_priority_level == PriorityLevel.HIGH
    ).count()
    escalated_count = complaints_query().filter(Complaint.status == ComplaintStatus.ESCALATED).count()
    transferred_count = complaints_query().filter(Complaint.status == ComplaintStatus.TRANSFERRED).count()
    pending_overlaps = _scope_overlap_query(db.query(OverlapResult), bureau_scope).filter(
        OverlapResult.review_status == "pending"
    ).count()
    pending_evidence = db.query(EvidenceAssessment).filter(
        EvidenceAssessment.complaint_id.in_(visible_ids),
        EvidenceAssessment.status.in_(["Information Incomplete", "Verification Required"])
    ).count()

    # Status distribution
    status_dist = complaints_query().with_entities(
        Complaint.status, func.count(Complaint.id)
    ).group_by(Complaint.status).all()

    # Bureau workload
    bureau_wl_query = db.query(
        Bureau.name, func.count(Complaint.id)
    ).join(Complaint, Complaint.bureau_id == Bureau.id, isouter=True
    )
    if bureau_scope is not None:
        bureau_wl_query = bureau_wl_query.filter(Complaint.id.in_(visible_ids))
    bureau_wl = bureau_wl_query.group_by(Bureau.id, Bureau.name).all()

    # Priority distribution
    prio_dist = complaints_query().with_entities(
        Complaint.calculated_priority_level, func.count(Complaint.id)
    ).group_by(Complaint.calculated_priority_level).all()

    # Monthly trend (last 6 months)
    month_year = extract("year", Complaint.registration_date)
    month_number = extract("month", Complaint.registration_date)
    monthly = complaints_query().with_entities(
        month_year.label("year"),
        month_number.label("month"),
        func.count(Complaint.id)
    ).group_by(month_year, month_number).order_by(month_year, month_number).limit(6).all()

    return {
        "total_complaints": total,
        "pending_complaints": pending,
        "under_process": under_process,
        "disposed_complaints": disposed,
        "overdue_complaints": overdue,
        "critical_cases": critical,
        "high_priority_cases": high,
        "escalated_cases": escalated_count,
        "transferred_cases": transferred_count,
        "pending_overlap_reviews": pending_overlaps,
        "pending_evidence_reviews": pending_evidence,
        "status_distribution": [
            {"status": s.value if s else "unknown", "count": c}
            for s, c in status_dist
        ],
        "bureau_workload": [
            {"bureau": b or "Unassigned", "count": c}
            for b, c in bureau_wl
        ],
        "priority_distribution": [
            {"priority": p.value if p else "unscored", "count": c}
            for p, c in prio_dist
        ],
        "monthly_trend": [
            {
                "month": f"{int(year)}-{int(month):02d}" if year is not None and month is not None else None,
                "count": count,
            }
            for year, month, count in monthly
        ],
        "region_distribution": [],
    }


# ─── Priority Queue ────────────────────────────────────────────────────────────
priority_router = APIRouter(prefix="/api/priority-queue", tags=["priority"])


@priority_router.get("")
def get_priority_queue(
    min_level: Optional[str] = None,
    bureau_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Complaint).filter(
        Complaint.status.notin_([ComplaintStatus.DISPOSED.value, ComplaintStatus.CLOSED.value])
    ).options(joinedload(Complaint.bureau), joinedload(Complaint.assigned_officer))
    q = scope_query_to_bureau(q, Complaint.bureau_id, current_user)

    if bureau_id:
        q = q.filter(Complaint.bureau_id == bureau_id)
    if min_level == "critical":
        q = q.filter(Complaint.calculated_priority_level == PriorityLevel.CRITICAL)
    elif min_level == "high":
        q = q.filter(Complaint.calculated_priority_level.in_([
            PriorityLevel.CRITICAL, PriorityLevel.HIGH
        ]))

    q = q.order_by(Complaint.calculated_priority_score.desc().nullslast(),
                   Complaint.target_disposal_date.asc().nullslast())
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    now = datetime.utcnow()
    result = []
    for c in items:
        overdue = c.target_disposal_date and c.target_disposal_date < now
        days_since_action = None
        if c.last_action_date:
            days_since_action = (now - c.last_action_date).days

        result.append({
            "id": c.id,
            "complaint_id": c.complaint_id,
            "title": c.title,
            "category": c.category.value,
            "status": c.status.value,
            "institution_name": c.institution_name_snapshot,
            "bureau": c.bureau.name if c.bureau else None,
            "officer": c.assigned_officer.full_name if c.assigned_officer else None,
            "target_disposal_date": c.target_disposal_date.isoformat() if c.target_disposal_date else None,
            "is_overdue": overdue,
            "days_since_last_action": days_since_action,
            "calculated_priority_score": c.calculated_priority_score,
            "calculated_priority_level": c.calculated_priority_level.value if c.calculated_priority_level else None,
            "assigned_priority_level": c.assigned_priority_level.value if c.assigned_priority_level else None,
            "priority_explanation": c.priority_explanation,
            "next_required_action": c.next_required_action,
        })

    return {"items": result, "total": total, "page": page, "per_page": per_page,
            "pages": (total + per_page - 1) // per_page}


# ─── Overlap Router ────────────────────────────────────────────────────────────
overlap_router = APIRouter(prefix="/api/overlaps", tags=["overlaps"])


@overlap_router.get("")
def get_all_overlaps(
    review_status: Optional[str] = "pending",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = _scope_overlap_query(db.query(OverlapResult), get_bureau_scope(current_user)).options(
        joinedload(OverlapResult.primary_complaint),
        joinedload(OverlapResult.candidate_complaint),
    )
    if review_status:
        q = q.filter(OverlapResult.review_status == review_status)
    q = q.order_by(OverlapResult.similarity_score.desc())
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [OverlapResultOut.model_validate(r) for r in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@overlap_router.post("/{overlap_id}/decision", response_model=OverlapResultOut)
def record_overlap_decision(
    overlap_id: int,
    payload: OverlapDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.SUPERVISORY_REVIEWER)
    ),
):
    result = db.query(OverlapResult).filter(OverlapResult.id == overlap_id).first()
    if not result:
        raise HTTPException(404, "Overlap result not found")
    result.decision = payload.decision
    result.decision_reason = payload.reason
    result.decided_by_id = current_user.id
    result.decided_at = datetime.utcnow()
    result.review_status = "reviewed"
    db.commit()
    db.refresh(result)
    log_action(db, "overlap.decision", user_id=current_user.id,
               resource_type="overlap", resource_id=overlap_id,
               details={"decision": payload.decision.value})
    return OverlapResultOut.model_validate(result)


# ─── Deadlines ────────────────────────────────────────────────────────────────
deadlines_router = APIRouter(prefix="/api/deadlines", tags=["deadlines"])


@deadlines_router.get("")
def get_deadlines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.utcnow()
    from datetime import timedelta
    in_7 = now + timedelta(days=7)

    overdue = scope_query_to_bureau(db.query(Complaint), Complaint.bureau_id, current_user).filter(
        Complaint.target_disposal_date < now,
        Complaint.status.notin_(["disposed", "closed"])
    ).order_by(Complaint.target_disposal_date.asc()).limit(20).all()

    upcoming = scope_query_to_bureau(db.query(Complaint), Complaint.bureau_id, current_user).filter(
        Complaint.target_disposal_date >= now,
        Complaint.target_disposal_date <= in_7,
        Complaint.status.notin_(["disposed", "closed"])
    ).order_by(Complaint.target_disposal_date.asc()).limit(20).all()

    def fmt(c):
        return {
            "id": c.id,
            "complaint_id": c.complaint_id,
            "title": c.title,
            "status": c.status.value,
            "target_disposal_date": c.target_disposal_date.isoformat() if c.target_disposal_date else None,
            "priority": c.calculated_priority_level.value if c.calculated_priority_level else None,
            "bureau_id": c.bureau_id,
            "institution": c.institution_name_snapshot,
        }

    return {
        "overdue": [fmt(c) for c in overdue],
        "due_within_7_days": [fmt(c) for c in upcoming],
    }


# ─── Notifications ────────────────────────────────────────────────────────────
notifications_router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@notifications_router.get("", response_model=List[NotificationOut])
def get_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Notification).filter(
        (Notification.recipient_id == current_user.id) |
        (Notification.recipient_id == None)
    )
    scope = get_bureau_scope(current_user)
    if scope is not None:
        q = q.filter(
            Notification.complaint_id.is_(None)
            | Notification.complaint.has(Complaint.bureau_id == scope)
        )
    if unread_only:
        q = q.filter(Notification.is_read == False)
    return [NotificationOut.model_validate(n) for n in q.order_by(Notification.created_at.desc()).limit(50).all()]


@notifications_router.patch("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_readonly),
):
    q = db.query(Notification).filter(
        Notification.id == notification_id,
        (Notification.recipient_id == current_user.id) | (Notification.recipient_id == None),
    )
    scope = get_bureau_scope(current_user)
    if scope is not None:
        q = q.filter(
            Notification.complaint_id.is_(None)
            | Notification.complaint.has(Complaint.bureau_id == scope)
        )
    n = q.first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"detail": "Marked as read"}


# ─── Users ─────────────────────────────────────────────────────────────────────
users_router = APIRouter(prefix="/api/users", tags=["users"])


@users_router.get("", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return [UserOut.model_validate(u) for u in db.query(User).all()]


@users_router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(400, "Username already taken")
    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        bureau_id=payload.bureau_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_action(db, "user.created", user_id=current_user.id,
               resource_type="user", resource_id=user.id)
    return UserOut.model_validate(user)


@users_router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    updates = payload.model_dump(exclude_none=True)
    for k, v in updates.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    log_action(db, "user.updated", user_id=current_user.id,
               resource_type="user", resource_id=user.id,
               details={"updated_fields": list(updates.keys())})
    return UserOut.model_validate(user)


# ─── Audit Logs ───────────────────────────────────────────────────────────────
audit_router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@audit_router.get("")
def get_audit_logs(
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    user_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    q = db.query(AuditLog).options(joinedload(AuditLog.user))
    if resource_type:
        q = q.filter(AuditLog.resource_type == resource_type)
    if resource_id:
        q = q.filter(AuditLog.resource_id == resource_id)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    q = q.order_by(AuditLog.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [AuditLogOut.model_validate(a) for a in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


# ─── Reports ─────────────────────────────────────────────────────────────────
reports_router = APIRouter(prefix="/api/reports", tags=["reports"])


@reports_router.get("/complaints")
def report_complaints(
    bureau_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(422, "End date cannot be earlier than start date.")
    bureau_filter = _resolve_report_bureau(current_user, bureau_id)
    base_q = db.query(Complaint)
    if bureau_filter is not None:
        base_q = base_q.filter(Complaint.bureau_id == bureau_filter)
    if start_date:
        base_q = base_q.filter(Complaint.registration_date >= start_date)
    if end_date:
        base_q = base_q.filter(Complaint.registration_date <= end_date)

    by_status = base_q.with_entities(Complaint.status, func.count(Complaint.id)).group_by(Complaint.status).all()
    by_category = base_q.with_entities(Complaint.category, func.count(Complaint.id)).group_by(Complaint.category).all()
    by_bureau = db.query(Bureau.name, func.count(Complaint.id)).join(
        Complaint, Complaint.bureau_id == Bureau.id, isouter=True
    )
    if start_date:
        by_bureau = by_bureau.filter(Complaint.registration_date >= start_date)
    if end_date:
        by_bureau = by_bureau.filter(Complaint.registration_date <= end_date)
    if bureau_filter is not None:
        by_bureau = by_bureau.filter(Complaint.bureau_id == bureau_filter)
    by_bureau = by_bureau.group_by(Bureau.id, Bureau.name).all()

    return {
        "by_status": [{"status": s.value if s else "unknown", "count": c} for s, c in by_status],
        "by_category": [{"category": cat.value if cat else "unknown", "count": c} for cat, c in by_category],
        "by_bureau": [{"bureau": b or "Unassigned", "count": c} for b, c in by_bureau],
    }


@reports_router.get("/priority")
def report_priority(
    bureau_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(422, "End date cannot be earlier than start date.")
    bureau_filter = _resolve_report_bureau(current_user, bureau_id)
    now = datetime.utcnow()
    q = db.query(Complaint)
    if bureau_filter is not None:
        q = q.filter(Complaint.bureau_id == bureau_filter)
    if start_date:
        q = q.filter(Complaint.registration_date >= start_date)
    if end_date:
        q = q.filter(Complaint.registration_date <= end_date)

    by_priority = q.with_entities(Complaint.calculated_priority_level, func.count(Complaint.id)).group_by(
        Complaint.calculated_priority_level
    ).all()
    overdue = q.filter(
        Complaint.target_disposal_date < now,
        Complaint.status.notin_(["disposed", "closed"])
    ).count()
    return {
        "by_priority": [{"priority": p.value if p else "unscored", "count": c} for p, c in by_priority],
        "total_overdue": overdue,
    }


@reports_router.get("/export")
def export_complaints_report(
    format: str = Query("json", pattern="^(json|csv)$"),
    bureau_id: Optional[int] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(422, "End date cannot be earlier than start date.")
    if category and category not in [c.value for c in ComplaintCategory]:
        raise HTTPException(400, f"Invalid category filter: '{category}'.")
    if status and status not in [s.value for s in ComplaintStatus]:
        raise HTTPException(400, f"Invalid status filter: '{status}'.")

    bureau_filter = _resolve_report_bureau(current_user, bureau_id)

    q = db.query(Complaint).options(
        joinedload(Complaint.bureau),
        joinedload(Complaint.assigned_officer),
    )

    if bureau_filter is not None:
        q = q.filter(Complaint.bureau_id == bureau_filter)

    if category:
        q = q.filter(Complaint.category == category)
    if status:
        q = q.filter(Complaint.status == status)
    if start_date:
        q = q.filter(Complaint.registration_date >= start_date)
    if end_date:
        q = q.filter(Complaint.registration_date <= end_date)

    complaints = q.order_by(Complaint.registration_date.desc()).all()
    rows = []
    for c in complaints:
        rows.append({
            "complaint_id": c.complaint_id,
            "title": c.title,
            "category": c.category.value if c.category else "",
            "status": c.status.value if c.status else "",
            "institution": c.institution_name_snapshot or "",
            "bureau": c.bureau.name if c.bureau else "Unassigned",
            "priority_score": c.calculated_priority_score or 0.0,
            "priority_level": (c.assigned_priority_level or c.calculated_priority_level or PriorityLevel.MEDIUM).value,
            "registration_date": c.registration_date.isoformat() if c.registration_date else "",
            "target_disposal_date": c.target_disposal_date.isoformat() if c.target_disposal_date else "",
        })

    if format == "csv":
        import io
        import csv
        from fastapi.responses import Response
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "complaint_id", "title", "category", "status", "institution",
            "bureau", "priority_score", "priority_level", "registration_date", "target_disposal_date"
        ])
        writer.writeheader()
        writer.writerows(rows)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=aicte_complaints_report.csv"}
        )

    return {"total": len(rows), "data": rows}


# ─── Inactivity Queue (Supervisor View) ───────────────────────────────────────
inactivity_router = APIRouter(prefix="/api/inactivity", tags=["inactivity"])


@inactivity_router.get("/warnings", response_model=List[InactivityWarningOut])
def get_all_inactivity_warnings(
    warning_stage: Optional[str] = None,
    supervisor_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISORY_REVIEWER)),
):
    """Get all inactivity warnings, optionally filtered by stage."""
    q = db.query(InactivityWarning).options(
        joinedload(InactivityWarning.officer),
        joinedload(InactivityWarning.new_officer),
    )

    if warning_stage:
        q = q.filter(InactivityWarning.warning_stage == warning_stage)

    if supervisor_only:
        q = q.filter(InactivityWarning.supervisor_notified == True)

    warnings = q.order_by(InactivityWarning.created_at.desc()).all()
    return [InactivityWarningOut.model_validate(w) for w in warnings]


@inactivity_router.get("/exceptions", response_model=List[InactivityExceptionOut])
def get_all_inactivity_exceptions(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISORY_REVIEWER)),
):
    """Get all inactivity exceptions, optionally filtered by active status."""
    q = db.query(InactivityException).options(
        joinedload(InactivityException.authorized_by),
    )

    if active_only:
        q = q.filter(InactivityException.is_active == True)

    exceptions = q.order_by(InactivityException.created_at.desc()).all()
    return [InactivityExceptionOut.model_validate(e) for e in exceptions]


@inactivity_router.post("/trigger-monitor")
def trigger_manual_monitor(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISORY_REVIEWER)),
):
    """Manually trigger the inactivity monitoring service (for testing/immediate action)."""
    from ..services.inactivity_monitor import run_inactivity_monitor
    summary = run_inactivity_monitor(db)
    log_action(db, "inactivity.monitor_triggered", user_id=current_user.id,
               resource_type="system", resource_id="inactivity_monitor",
               details=summary)
    return summary


# ─── Bureaus ──────────────────────────────────────────────────────────────────
bureaus_router = APIRouter(prefix="/api/bureaus", tags=["bureaus"])


@bureaus_router.get("")
def list_bureaus(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from ..schemas import BureauOut
    bureaus = db.query(Bureau).filter(Bureau.is_active == True).all()
    return [BureauOut.model_validate(b) for b in bureaus]
