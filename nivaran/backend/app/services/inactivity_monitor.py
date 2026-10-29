"""
Inactivity Monitoring Service — 10/20/30 day escalation workflow.

This service monitors complaints for inactivity and triggers warnings/reassignment:
- Day 10: First warning to officer
- Day 20: Second warning + supervisor escalation
- Day 30: Reassignment to new eligible officer

Configurable thresholds via INACTIVITY_THRESHOLDS dict.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from ..models import (
    Complaint, User, UserRole, ComplaintStatus,
    InactivityWarning, InactivityException, AssignmentRecord
)
from ..services.assignment_engine import assign_complaint
from ..services.audit_service import log_action


# Configurable thresholds (in days)
INACTIVITY_THRESHOLDS = {
    "day_10": 10,
    "day_20": 20,
    "day_30": 30,
}


# Meaningful action types that reset inactivity baseline
MEANINGFUL_ACTION_TYPES = [
    "complaint.registered",
    "status.changed",
    "complaint.transferred",
    "assignment.assigned",
    "assignment.reassigned",
    "complaint.action_added",
    "evidence.assessed",
    "overlap.decision_recorded",
]


def _get_last_meaningful_action(
    db: Session,
    complaint: Complaint
) -> Optional[datetime]:
    """
    Get the timestamp of the last meaningful action on a complaint.
    If no meaningful action exists, return the assignment timestamp or registration date.
    """
    last_action = db.query(func.max(Complaint.actions.created_at)).filter(
        Complaint.id == complaint.id,
        Complaint.actions.action_type.in_(MEANINGFUL_ACTION_TYPES)
    ).scalar()

    if last_action:
        return last_action

    # Fallback to assignment or registration
    if complaint.assigned_officer_id:
        last_assignment = db.query(func.max(AssignmentRecord.assigned_at)).filter(
            AssignmentRecord.complaint_id == complaint.id
        ).scalar()
        if last_assignment:
            return last_assignment

    return complaint.registration_date


def _has_active_exception(db: Session, complaint_id: int) -> bool:
    """Check if complaint has an active inactivity exception."""
    now = datetime.utcnow()
    exception = db.query(InactivityException).filter(
        InactivityException.complaint_id == complaint_id,
        InactivityException.is_active == True,
        or_(
            InactivityException.expires_at.is_(None),
            InactivityException.expires_at > now
        )
    ).first()
    return exception is not None


def _create_warning(
    db: Session,
    complaint: Complaint,
    officer_id: Optional[int],
    stage: str,
    days_inactive: int,
    last_action_at: Optional[datetime],
    new_officer_id: Optional[int] = None,
) -> InactivityWarning:
    """Create an inactivity warning record."""
    dedup_key = f"{stage}:{complaint.id}:{datetime.utcnow().date()}"
    existing = db.query(InactivityWarning).filter(
        InactivityWarning.dedup_key == dedup_key
    ).first()
    if existing:
        return existing

    warning = InactivityWarning(
        complaint_id=complaint.id,
        officer_id=officer_id,
        warning_stage=stage,
        days_inactive=days_inactive,
        last_meaningful_action_at=last_action_at,
        new_officer_id=new_officer_id,
        notification_sent=False,
        supervisor_notified=False,
        dedup_key=dedup_key,
    )
    db.add(warning)
    db.flush()
    return warning


def process_complaint_inactivity(db: Session, complaint: Complaint) -> Dict[str, Any]:
    """
    Process a single complaint for inactivity monitoring.

    Returns a dict with processing results.
    """
    result = {
        "complaint_id": complaint.complaint_id,
        "processed": False,
        "warnings_created": [],
        "reassigned": False,
        "skip_reason": None,
    }

    # Skip closed/disposed complaints
    if complaint.status in (ComplaintStatus.CLOSED, ComplaintStatus.DISPOSED):
        result["skip_reason"] = "Complaint closed or disposed"
        return result

    # Skip if no officer assigned
    if not complaint.assigned_officer_id:
        result["skip_reason"] = "No officer assigned"
        return result

    # Skip if active exception exists
    if _has_active_exception(db, complaint.id):
        result["skip_reason"] = "Active inactivity exception"
        return result

    # Get last meaningful action
    last_action = _get_last_meaningful_action(db, complaint)
    if not last_action:
        last_action = complaint.registration_date

    days_inactive = (datetime.utcnow() - last_action).days

    # Day 10: First warning
    if days_inactive >= INACTIVITY_THRESHOLDS["day_10"]:
        # Check if day_10 warning already exists
        existing_day10 = db.query(InactivityWarning).filter(
            InactivityWarning.complaint_id == complaint.id,
            InactivityWarning.warning_stage == "day_10"
        ).first()

        if not existing_day10:
            warning = _create_warning(
                db, complaint, complaint.assigned_officer_id,
                "day_10", days_inactive, last_action
            )
            warning.notification_sent = True
            result["warnings_created"].append("day_10")

    # Day 20: Second warning + supervisor escalation
    if days_inactive >= INACTIVITY_THRESHOLDS["day_20"]:
        existing_day20 = db.query(InactivityWarning).filter(
            InactivityWarning.complaint_id == complaint.id,
            InactivityWarning.warning_stage == "day_20"
        ).first()

        if not existing_day20:
            warning = _create_warning(
                db, complaint, complaint.assigned_officer_id,
                "day_20", days_inactive, last_action
            )
            warning.notification_sent = True
            warning.supervisor_notified = True
            result["warnings_created"].append("day_20")

    # Day 30: Reassignment
    if days_inactive >= INACTIVITY_THRESHOLDS["day_30"]:
        existing_day30 = db.query(InactivityWarning).filter(
            InactivityWarning.complaint_id == complaint.id,
            InactivityWarning.warning_stage.in_(["day_30_reassigned", "day_30_no_replacement"])
        ).first()

        if not existing_day30:
            # Attempt reassignment
            try:
                assignment_result = assign_complaint(
                    db=db,
                    complaint=complaint,
                    acting_user_id=None,  # System/scheduler
                    assignment_type="inactivity_reassign"
                )

                if assignment_result["assigned"]:
                    warning = _create_warning(
                        db, complaint, complaint.assigned_officer_id,
                        "day_30_reassigned", days_inactive, last_action,
                        new_officer_id=assignment_result["officer_id"]
                    )
                    warning.notification_sent = True
                    warning.supervisor_notified = True
                    result["warnings_created"].append("day_30_reassigned")
                    result["reassigned"] = True
                else:
                    # No eligible replacement
                    warning = _create_warning(
                        db, complaint, complaint.assigned_officer_id,
                        "day_30_no_replacement", days_inactive, last_action
                    )
                    warning.supervisor_notified = True
                    result["warnings_created"].append("day_30_no_replacement")
            except Exception as e:
                # Log error but continue processing other complaints
                result["error"] = str(e)

    result["processed"] = True
    return result


def run_inactivity_monitor(db: Session) -> Dict[str, Any]:
    """
    Run the inactivity monitoring service on all open complaints.

    This function is idempotent — it can be called multiple times without
    creating duplicate warnings or reassignments.

    Returns summary statistics.
    """
    summary = {
        "processed_at": datetime.utcnow().isoformat(),
        "total_complaints_checked": 0,
        "day_10_warnings": 0,
        "day_20_warnings": 0,
        "day_30_reassignments": 0,
        "day_30_no_replacement": 0,
        "complaints_processed": [],
    }

    # Get all open complaints with assigned officers
    open_statuses = [
        ComplaintStatus.REGISTERED,
        ComplaintStatus.UNDER_INITIAL_REVIEW,
        ComplaintStatus.UNDER_PROCESS,
        ComplaintStatus.AWAITING_INFORMATION,
        ComplaintStatus.TRANSFERRED,
        ComplaintStatus.ESCALATED,
    ]

    complaints = db.query(Complaint).filter(
        Complaint.status.in_(open_statuses),
        Complaint.assigned_officer_id.isnot(None)
    ).all()

    summary["total_complaints_checked"] = len(complaints)

    for complaint in complaints:
        try:
            result = process_complaint_inactivity(db, complaint)
            summary["complaints_processed"].append(result)

            if "day_10" in result.get("warnings_created", []):
                summary["day_10_warnings"] += 1
            if "day_20" in result.get("warnings_created", []):
                summary["day_20_warnings"] += 1
            if "day_30_reassigned" in result.get("warnings_created", []):
                summary["day_30_reassignments"] += 1
            if "day_30_no_replacement" in result.get("warnings_created", []):
                summary["day_30_no_replacement"] += 1

        except Exception as e:
            # Log and continue with next complaint
            summary["complaints_processed"].append({
                "complaint_id": complaint.complaint_id,
                "error": str(e),
            })

    db.commit()
    return summary
