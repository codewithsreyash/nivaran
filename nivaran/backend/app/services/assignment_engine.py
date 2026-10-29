"""
Assignment Engine — deterministic, explainable officer assignment.

Policy (rules-v1):
  1. Select officers who are active and belong to the complaint's bureau.
  2. Score each officer: lower open-case workload → higher preference.
     Tie-break: fewer critical-priority open cases first.
  3. Assign the top-scoring officer.
  4. Record the assignment in AssignmentRecord and CaseAction.
  5. Notify the assigned officer via the Notification table.
  6. If no eligible officer found, mark complaint unassigned and notify supervisors.

This module is stateless — it receives a db session and complaint, runs the
selection, persists results, and returns a result dict.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import (
    Complaint, User, UserRole, Bureau, AssignmentRecord,
    CaseAction, Notification, ComplaintStatus, PriorityLevel
)
from ..services.audit_service import log_action


# Categories → preferred bureau codes (deterministic routing)
CATEGORY_BUREAU_MAP: Dict[str, List[str]] = {
    "scholarship_financial":     ["FIN"],
    "academic_examination":      ["ACAD"],
    "faculty_related":           ["ACAD"],
    "infrastructure_facilities": ["COMP"],
    "regulatory_compliance":     ["COMP"],
    "approval_related":          ["COMP"],
    "student_safety_welfare":    ["ACAD", "COMP"],
    "administrative":            ["COMP"],
    "other":                     [],          # any active bureau
}


def _notify(
    db: Session,
    complaint: Complaint,
    recipient_id: int,
    title: str,
    message: str,
    notification_type: str,
    dedup_key: Optional[str] = None,
) -> None:
    """Create a notification, silently skipping duplicates via trigger_key."""
    if dedup_key:
        existing = db.query(Notification).filter(
            Notification.trigger_key == dedup_key
        ).first()
        if existing:
            return
    n = Notification(
        complaint_id=complaint.id,
        recipient_id=recipient_id,
        title=title,
        message=message,
        notification_type=notification_type,
        trigger_key=dedup_key,
    )
    db.add(n)


def _get_officer_workload(db: Session, officer_id: int) -> Dict[str, int]:
    """Return open-case counts for an officer."""
    terminal = [ComplaintStatus.DISPOSED.value, ComplaintStatus.CLOSED.value]
    total = db.query(func.count(Complaint.id)).filter(
        Complaint.assigned_officer_id == officer_id,
        Complaint.status.notin_(terminal),
    ).scalar() or 0
    critical = db.query(func.count(Complaint.id)).filter(
        Complaint.assigned_officer_id == officer_id,
        Complaint.status.notin_(terminal),
        Complaint.calculated_priority_level == PriorityLevel.CRITICAL,
    ).scalar() or 0
    return {"open_cases": total, "critical_cases": critical}


def assign_complaint(
    db: Session,
    complaint: Complaint,
    acting_user_id: Optional[int] = None,
    force_officer_id: Optional[int] = None,
    reason: Optional[str] = None,
    assignment_type: str = "auto",
) -> Dict[str, Any]:
    """
    Assign `complaint` to the best eligible officer.

    Parameters
    ----------
    db               : active SQLAlchemy session
    complaint        : the Complaint ORM instance (must already have an id)
    acting_user_id   : user who triggered the assignment (None = system/scheduler)
    force_officer_id : bypass workload selection and assign this specific officer
    reason           : human-readable reason (required for manual reassignment)
    assignment_type  : 'auto' | 'manual' | 'inactivity_reassign' | 'transfer'

    Returns
    -------
    dict with keys:
        assigned         : bool
        officer_id       : int | None
        officer_name     : str | None
        workload         : dict | None
        reason           : str
        assignment_record_id : int | None
    """
    now = datetime.utcnow()

    # ── Resolve target bureau ──────────────────────────────────────────────
    bureau_id = complaint.bureau_id
    bureau: Optional[Bureau] = None
    if bureau_id:
        bureau = db.query(Bureau).filter(Bureau.id == bureau_id).first()

    # ── Find eligible officers ─────────────────────────────────────────────
    if force_officer_id:
        candidates = db.query(User).filter(
            User.id == force_officer_id,
            User.is_active == True,
            User.role == UserRole.BUREAU_OFFICER,
        ).all()
        selection_reason = f"Manual override: officer {force_officer_id} specified."
    elif bureau_id:
        # Officers in the same bureau
        candidates = db.query(User).filter(
            User.bureau_id == bureau_id,
            User.is_active == True,
            User.role == UserRole.BUREAU_OFFICER,
        ).all()
        selection_reason = (
            f"Auto-selected from {len(candidates)} active officer(s) in bureau '{bureau.name if bureau else bureau_id}'."
        )
    else:
        # No bureau assigned — check category routing
        category_key = complaint.category.value if complaint.category else "other"
        preferred_codes = CATEGORY_BUREAU_MAP.get(category_key, [])

        if preferred_codes:
            preferred_bureaus = db.query(Bureau).filter(
                Bureau.code.in_(preferred_codes),
                Bureau.is_active == True,
            ).all()
            bureau_ids = [b.id for b in preferred_bureaus]
            candidates = db.query(User).filter(
                User.bureau_id.in_(bureau_ids),
                User.is_active == True,
                User.role == UserRole.BUREAU_OFFICER,
            ).all()
            selection_reason = (
                f"Category '{category_key}' routed to bureau(s) {preferred_codes}."
            )
            # Set the bureau on the complaint if exactly one match
            if preferred_bureaus and not complaint.bureau_id:
                complaint.bureau_id = preferred_bureaus[0].id
        else:
            candidates = []
            selection_reason = "No bureau or routing rule resolved; complaint marked unassigned."

    # ── Score and select best candidate ───────────────────────────────────
    # Exclude the officer being replaced (for inactivity_reassign)
    current_officer_id = complaint.assigned_officer_id
    if assignment_type == "inactivity_reassign" and current_officer_id:
        candidates = [c for c in candidates if c.id != current_officer_id]

    if not candidates:
        # ── UNASSIGNED path ───────────────────────────────────────────────
        selected_officer = None
        workload = None
        assignment_reason = reason or selection_reason + " No eligible officer found."

        # Notify supervisors
        supervisors = db.query(User).filter(
            User.role.in_([UserRole.ADMIN, UserRole.SUPERVISORY_REVIEWER]),
            User.is_active == True,
        ).all()
        for sup in supervisors:
            _notify(
                db, complaint, sup.id,
                title=f"Unassigned Complaint: {complaint.complaint_id}",
                message=(
                    f"Complaint '{complaint.complaint_id}' could not be automatically assigned "
                    f"to an officer in the responsible bureau. Manual intervention required."
                ),
                notification_type="assignment.unassigned",
                dedup_key=f"unassigned:{complaint.id}:{sup.id}:{now.date()}",
            )

        ar = AssignmentRecord(
            complaint_id=complaint.id,
            officer_id=None,
            previous_officer_id=current_officer_id,
            assigned_by_id=acting_user_id,
            bureau_id=bureau_id,
            assignment_type=assignment_type,
            reason=assignment_reason,
            assigned_at=now,
        )
        db.add(ar)

        action = CaseAction(
            complaint_id=complaint.id,
            actor_id=acting_user_id,
            action_type="assignment.unassigned",
            description=f"No eligible officer found. {assignment_reason}",
            metadata_json={"bureau_id": bureau_id, "assignment_type": assignment_type},
        )
        db.add(action)
        complaint.assigned_officer_id = None

        try:
            db.flush()
        except Exception:
            db.rollback()
            raise

        log_action(
            db, "complaint.unassigned",
            user_id=acting_user_id,
            resource_type="complaint",
            resource_id=complaint.id,
            details={"complaint_id": complaint.complaint_id, "reason": assignment_reason},
        )
        return {
            "assigned": False,
            "officer_id": None,
            "officer": None,
            "workload": None,
            "reason": assignment_reason,
            "assignment_record_id": ar.id if ar.id else None,
        }

    # Score candidates: sort by (open_cases ASC, critical_cases ASC)
    scored = []
    for officer in candidates:
        wl = _get_officer_workload(db, officer.id)
        scored.append((officer, wl))
    scored.sort(key=lambda x: (x[1]["open_cases"], x[1]["critical_cases"]))
    selected_officer, workload = scored[0]

    assignment_reason = (
        reason or
        f"{selection_reason} Assigned '{selected_officer.full_name}' "
        f"(open cases: {workload['open_cases']}, critical: {workload['critical_cases']})."
    )

    # ── Persist assignment ─────────────────────────────────────────────────
    ar = AssignmentRecord(
        complaint_id=complaint.id,
        officer_id=selected_officer.id,
        previous_officer_id=current_officer_id,
        assigned_by_id=acting_user_id,
        bureau_id=complaint.bureau_id,
        assignment_type=assignment_type,
        reason=assignment_reason,
        officer_workload_at_assignment=workload["open_cases"],
        assigned_at=now,
    )
    db.add(ar)

    action_desc = (
        f"Assigned to {selected_officer.full_name} "
        f"({assignment_type.replace('_', ' ')}). {assignment_reason}"
    )
    action = CaseAction(
        complaint_id=complaint.id,
        actor_id=acting_user_id,
        action_type="assignment.assigned",
        description=action_desc,
        metadata_json={
            "officer_id": selected_officer.id,
            "previous_officer_id": current_officer_id,
            "assignment_type": assignment_type,
            "workload": workload,
        },
    )
    db.add(action)

    # Update the complaint
    complaint.assigned_officer_id = selected_officer.id

    # Notify assigned officer
    _notify(
        db, complaint, selected_officer.id,
        title=f"New Case Assigned: {complaint.complaint_id}",
        message=(
            f"You have been assigned complaint '{complaint.complaint_id}' — "
            f"'{complaint.title}'. Priority: "
            f"{complaint.calculated_priority_level.value if complaint.calculated_priority_level else 'unscored'}."
        ),
        notification_type="assignment.new",
        dedup_key=f"assign:{complaint.id}:{selected_officer.id}:{now.date()}",
    )

    # Notify previous officer if this is a reassignment
    if current_officer_id and current_officer_id != selected_officer.id:
        _notify(
            db, complaint, current_officer_id,
            title=f"Case Reassigned: {complaint.complaint_id}",
            message=(
                f"Complaint '{complaint.complaint_id}' has been reassigned to "
                f"'{selected_officer.full_name}'. Reason: {reason or 'Automatic reassignment'}."
            ),
            notification_type="assignment.reassigned",
            dedup_key=f"reassign_from:{complaint.id}:{current_officer_id}:{now.date()}",
        )

    try:
        db.flush()
    except Exception:
        db.rollback()
        raise

    log_action(
        db, "complaint.assigned",
        user_id=acting_user_id,
        resource_type="complaint",
        resource_id=complaint.id,
        details={
            "complaint_id": complaint.complaint_id,
            "officer_id": selected_officer.id,
            "officer_name": selected_officer.full_name,
            "assignment_type": assignment_type,
            "workload": workload,
        },
    )
    return {
        "assigned": True,
        "officer_id": selected_officer.id,
        "officer": {
            "id": selected_officer.id,
            "username": selected_officer.username,
            "full_name": selected_officer.full_name,
            "email": selected_officer.email,
            "role": selected_officer.role.value,
            "bureau_id": selected_officer.bureau_id,
        },
        "workload": workload,
        "reason": assignment_reason,
        "assignment_record_id": ar.id,
    }
