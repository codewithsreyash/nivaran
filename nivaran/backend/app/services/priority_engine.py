"""
Priority Engine — Rules-based implementation.
Status: Rules-based baseline active. No ML model trained.

Scoring (0–100):
  Urgency/severity:           30 pts
  Potential impact:           20 pts
  Deadline pressure:          20 pts
  Ageing & inaction:          15 pts
  Escalation / dependency:    10 pts
  Repeated transfers:          5 pts

Priority bands:
  80–100 → Critical
  60–79  → High
  30–59  → Medium
  0–29   → Low
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from ..models import Complaint, PriorityLevel, ComplaintStatus, ComplaintCategory


CALCULATION_VERSION = "rules-v1"

# Urgency weights per category
URGENCY_MAP: Dict[str, float] = {
    "student_safety_welfare": 30.0,
    "scholarship_financial": 24.0,
    "regulatory_compliance": 22.0,
    "academic_examination": 18.0,
    "faculty_related": 16.0,
    "approval_related": 14.0,
    "infrastructure_facilities": 12.0,
    "administrative": 10.0,
    "other": 8.0,
}

# Status-based impact multiplier
ESCALATION_STATUS = {ComplaintStatus.ESCALATED}


def _deadline_pressure(target_date: Optional[datetime], now: datetime) -> Tuple[float, str]:
    """Return deadline contribution (0–20) and a note."""
    if target_date is None:
        return 5.0, "No deadline set — moderate default applied."
    delta = (target_date - now).total_seconds() / 3600  # hours
    if delta < 0:
        return 20.0, f"Overdue by {abs(int(delta // 24))} day(s)."
    elif delta <= 24:
        return 18.0, "Due within 24 hours."
    elif delta <= 72:
        return 15.0, "Due within 3 days."
    elif delta <= 168:
        return 10.0, "Due within 7 days."
    elif delta <= 336:
        return 5.0, "Due within 2 weeks."
    else:
        return 2.0, "Deadline is more than 2 weeks away."


def _ageing_contribution(registration_date: datetime, last_action: Optional[datetime], now: datetime) -> Tuple[float, str]:
    """Return ageing contribution (0–15) and a note."""
    age_days = (now - registration_date).days
    inaction_days = (now - last_action).days if last_action else age_days

    if age_days >= 90 or inaction_days >= 60:
        return 15.0, f"Case is {age_days} days old with {inaction_days} days since last action."
    elif age_days >= 60 or inaction_days >= 30:
        return 12.0, f"Case is {age_days} days old; {inaction_days} days since last meaningful action."
    elif age_days >= 30 or inaction_days >= 14:
        return 8.0, f"Case has been open {age_days} days; {inaction_days} days since last action."
    elif age_days >= 14:
        return 5.0, f"Case has been open {age_days} days."
    else:
        return 2.0, f"Recently registered ({age_days} days ago)."


def calculate_priority(complaint: Complaint, transfer_count: int = 0) -> Dict[str, Any]:
    """
    Calculate priority score for a complaint.
    Returns a dict with score, level, contributions, explanation and metadata.
    """
    now = datetime.utcnow()
    missing: List[str] = []

    # 1. Urgency / severity (max 30)
    category_key = complaint.category.value if complaint.category else "other"
    urgency = URGENCY_MAP.get(category_key, 8.0)
    if complaint.category is None:
        missing.append("category")

    # 2. Potential impact (max 20) — proxy: safety/financial categories
    if category_key in ("student_safety_welfare", "scholarship_financial", "regulatory_compliance"):
        impact = 20.0
    elif category_key in ("academic_examination", "faculty_related"):
        impact = 14.0
    else:
        impact = 8.0

    # 3. Deadline pressure (max 20)
    deadline_pts, deadline_note = _deadline_pressure(complaint.target_disposal_date, now)

    # 4. Ageing and inaction (max 15)
    ageing_pts, ageing_note = _ageing_contribution(
        complaint.registration_date, complaint.last_action_date, now
    )

    # 5. Escalation / dependency (max 10)
    escalation_pts = 10.0 if complaint.status in ESCALATION_STATUS else 0.0
    if complaint.status == ComplaintStatus.AWAITING_INFORMATION:
        escalation_pts = max(escalation_pts, 3.0)

    # 6. Repeated transfers (max 5)
    transfer_pts = min(transfer_count * 2.5, 5.0)

    total = urgency + impact + deadline_pts + ageing_pts + escalation_pts + transfer_pts
    total = min(total, 100.0)

    # Priority band
    if total >= 80:
        level = PriorityLevel.CRITICAL
    elif total >= 60:
        level = PriorityLevel.HIGH
    elif total >= 30:
        level = PriorityLevel.MEDIUM
    else:
        level = PriorityLevel.LOW

    # Explanation
    parts = []
    if level == PriorityLevel.CRITICAL:
        parts.append("Critical priority")
    elif level == PriorityLevel.HIGH:
        parts.append("High priority")
    elif level == PriorityLevel.MEDIUM:
        parts.append("Medium priority")
    else:
        parts.append("Low priority")

    if deadline_pts >= 18:
        parts.append(deadline_note)
    if ageing_pts >= 12:
        parts.append(ageing_note)
    if escalation_pts > 0:
        parts.append(f"Case is {complaint.status.value.replace('_', ' ')}.")
    if urgency >= 24:
        parts.append(f"Category '{category_key.replace('_', ' ')}' carries high urgency weight.")
    if transfer_pts >= 2.5:
        parts.append(f"Case has been transferred {transfer_count} time(s).")
    if missing:
        parts.append(f"Missing data: {', '.join(missing)}.")

    explanation = " ".join(parts)

    return {
        "score": round(total, 2),
        "priority_level": level,
        "urgency_contribution": round(urgency, 2),
        "impact_contribution": round(impact, 2),
        "deadline_contribution": round(deadline_pts, 2),
        "ageing_contribution": round(ageing_pts, 2),
        "escalation_contribution": round(escalation_pts, 2),
        "transfer_contribution": round(transfer_pts, 2),
        "explanation": explanation,
        "missing_data_flags": missing,
        "calculation_version": CALCULATION_VERSION,
        "calculated_at": now,
        "deadline_note": deadline_note,
        "ageing_note": ageing_note,
    }
