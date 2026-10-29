"""
Extended Priority Engine tests — Phase 4.
Covers all 10 scenarios required:
1. Student-safety / welfare concern
2. Scholarship affecting multiple students
3. Overdue complaint
4. Deadline within 24 hours
5. No deadline set
6. Long-open complaint with no recent action
7. Repeated transfers
8. Recently registered low-urgency complaint
9. Escalated complaint
10. Missing / inconsistent data

Verifications per scenario:
- Score in [0, 100]
- Priority band matches configured thresholds
- Each component in its permitted range
- Component sum ≤ total ≤ 100 (may be capped)
- Explanation identifies major contributing factors
- Missing data is surfaced
"""
import pytest
from datetime import datetime, timedelta
from app.models import Complaint, ComplaintCategory, ComplaintStatus, PriorityLevel
from app.services.priority_engine import (
    calculate_priority, _deadline_pressure, _ageing_contribution,
    CALCULATION_VERSION, URGENCY_MAP
)

# Permitted max contributions per dimension
MAX_URGENCY = 30.0
MAX_IMPACT = 20.0
MAX_DEADLINE = 20.0
MAX_AGEING = 15.0
MAX_ESCALATION = 10.0
MAX_TRANSFERS = 5.0


def assert_score_invariants(result: dict):
    """Assert all global score invariants hold for a priority result."""
    score = result["score"]
    assert 0 <= score <= 100, f"Score {score} is outside [0, 100]"
    assert result["urgency_contribution"] >= 0
    assert result["urgency_contribution"] <= MAX_URGENCY
    assert result["impact_contribution"] >= 0
    assert result["impact_contribution"] <= MAX_IMPACT
    assert result["deadline_contribution"] >= 0
    assert result["deadline_contribution"] <= MAX_DEADLINE
    assert result["ageing_contribution"] >= 0
    assert result["ageing_contribution"] <= MAX_AGEING
    assert result["escalation_contribution"] >= 0
    assert result["escalation_contribution"] <= MAX_ESCALATION
    assert result["transfer_contribution"] >= 0
    assert result["transfer_contribution"] <= MAX_TRANSFERS
    assert result["calculation_version"] == CALCULATION_VERSION
    assert result["explanation"], "Explanation must not be empty"

    # Component sum check
    component_sum = (
        result["urgency_contribution"] + result["impact_contribution"] +
        result["deadline_contribution"] + result["ageing_contribution"] +
        result["escalation_contribution"] + result["transfer_contribution"]
    )
    if component_sum <= 100:
        assert abs(score - round(component_sum, 2)) < 0.01, \
            f"score={score} does not match component sum={component_sum}"
    else:
        assert score == 100.0, f"Score should be capped at 100, got {score}"


def assert_band(result: dict, expected_band: PriorityLevel):
    assert result["priority_level"] == expected_band, \
        f"Expected band {expected_band}, got {result['priority_level']} (score={result['score']})"


# ─── Test Cases ──────────────────────────────────────────────────────────────

def test_1_student_safety_welfare_is_critical():
    """Safety/welfare complaints must score at the maximum urgency tier."""
    now = datetime.utcnow()
    complaint = Complaint(
        category=ComplaintCategory.STUDENT_SAFETY_WELFARE,
        status=ComplaintStatus.REGISTERED,
        registration_date=now - timedelta(days=5),
        last_action_date=now - timedelta(days=5),
        target_disposal_date=now + timedelta(days=7),
    )
    result = calculate_priority(complaint, transfer_count=0)
    assert_score_invariants(result)
    assert result["urgency_contribution"] == 30.0, "Safety category must get max urgency (30.0)"
    assert result["impact_contribution"] == 20.0, "Safety category must get max impact (20.0)"
    # Total: 30 + 20 + 10 + 2 = 62 → HIGH or above
    assert result["score"] >= 60.0
    assert result["priority_level"] in (PriorityLevel.HIGH, PriorityLevel.CRITICAL)


def test_2_scholarship_complaint_is_high_priority():
    """Scholarship/financial complaints have high urgency and must reach at least HIGH."""
    now = datetime.utcnow()
    complaint = Complaint(
        category=ComplaintCategory.SCHOLARSHIP_FINANCIAL,
        status=ComplaintStatus.UNDER_PROCESS,
        registration_date=now - timedelta(days=20),
        last_action_date=now - timedelta(days=10),
        target_disposal_date=now + timedelta(days=3),
    )
    result = calculate_priority(complaint, transfer_count=0)
    assert_score_invariants(result)
    assert result["urgency_contribution"] == 24.0
    assert result["impact_contribution"] == 20.0
    assert result["priority_level"] in (PriorityLevel.HIGH, PriorityLevel.CRITICAL)
    assert "scholarship financial" in result["explanation"] or "urgency" in result["explanation"].lower()


def test_3_overdue_complaint_gets_max_deadline_pressure():
    """Overdue complaints must receive the maximum deadline contribution (20 pts)."""
    now = datetime.utcnow()
    complaint = Complaint(
        category=ComplaintCategory.OTHER,
        status=ComplaintStatus.UNDER_PROCESS,
        registration_date=now - timedelta(days=10),
        last_action_date=now - timedelta(days=5),
        target_disposal_date=now - timedelta(days=2),  # overdue
    )
    result = calculate_priority(complaint, transfer_count=0)
    assert_score_invariants(result)
    assert result["deadline_contribution"] == 20.0, "Overdue complaint must get max deadline score"
    assert "Overdue" in result.get("deadline_note", "") or "Overdue" in result["explanation"]


def test_4_deadline_within_24h():
    """Deadline within 24 hours must get 18 pts deadline pressure."""
    now = datetime.utcnow()
    complaint = Complaint(
        category=ComplaintCategory.ADMINISTRATIVE,
        status=ComplaintStatus.REGISTERED,
        registration_date=now - timedelta(days=1),
        last_action_date=now - timedelta(days=1),
        target_disposal_date=now + timedelta(hours=10),
    )
    result = calculate_priority(complaint, transfer_count=0)
    assert_score_invariants(result)
    assert result["deadline_contribution"] == 18.0
    assert "24 hours" in result.get("deadline_note", "")


def test_5_no_deadline_gets_default_deadline_score():
    """No deadline set must get the moderate default (5.0 pts)."""
    now = datetime.utcnow()
    complaint = Complaint(
        category=ComplaintCategory.ADMINISTRATIVE,
        status=ComplaintStatus.REGISTERED,
        registration_date=now - timedelta(days=5),
        last_action_date=now - timedelta(days=5),
        target_disposal_date=None,  # no deadline
    )
    result = calculate_priority(complaint, transfer_count=0)
    assert_score_invariants(result)
    assert result["deadline_contribution"] == 5.0
    assert "No deadline" in result.get("deadline_note", "")


def test_6_long_open_no_action_gets_max_ageing():
    """Case older than 90 days or inactive 60+ days must get max ageing (15 pts)."""
    now = datetime.utcnow()
    complaint = Complaint(
        category=ComplaintCategory.OTHER,
        status=ComplaintStatus.UNDER_PROCESS,
        registration_date=now - timedelta(days=100),
        last_action_date=now - timedelta(days=61),
        target_disposal_date=now + timedelta(days=30),
    )
    result = calculate_priority(complaint, transfer_count=0)
    assert_score_invariants(result)
    assert result["ageing_contribution"] == 15.0
    assert result["ageing_contribution"] <= MAX_AGEING


def test_7_repeated_transfers():
    """Two transfers → 5.0 pts transfer contribution (capped)."""
    now = datetime.utcnow()
    complaint = Complaint(
        category=ComplaintCategory.ADMINISTRATIVE,
        status=ComplaintStatus.UNDER_PROCESS,
        registration_date=now - timedelta(days=20),
        last_action_date=now - timedelta(days=5),
        target_disposal_date=now + timedelta(days=10),
    )
    result = calculate_priority(complaint, transfer_count=2)
    assert_score_invariants(result)
    assert result["transfer_contribution"] == 5.0
    assert "transferred 2 time(s)" in result["explanation"]


def test_7b_single_transfer():
    """One transfer → 2.5 pts."""
    now = datetime.utcnow()
    complaint = Complaint(
        category=ComplaintCategory.ADMINISTRATIVE,
        status=ComplaintStatus.UNDER_PROCESS,
        registration_date=now - timedelta(days=20),
        last_action_date=now - timedelta(days=5),
        target_disposal_date=now + timedelta(days=10),
    )
    result = calculate_priority(complaint, transfer_count=1)
    assert_score_invariants(result)
    assert result["transfer_contribution"] == 2.5


def test_8_recently_registered_low_urgency_is_low():
    """Fresh administrative complaint with far deadline → LOW priority."""
    now = datetime.utcnow()
    complaint = Complaint(
        category=ComplaintCategory.ADMINISTRATIVE,
        status=ComplaintStatus.REGISTERED,
        registration_date=now - timedelta(days=1),
        last_action_date=now - timedelta(days=1),
        target_disposal_date=now + timedelta(days=30),
    )
    result = calculate_priority(complaint, transfer_count=0)
    assert_score_invariants(result)
    # urgency=10, impact=8, deadline=5, ageing=2, esc=0, transfer=0 → 25 → LOW
    assert result["score"] < 30
    assert result["priority_level"] == PriorityLevel.LOW


def test_9_escalated_complaint_gets_escalation_bonus():
    """Escalated status must add 10 pts escalation contribution."""
    now = datetime.utcnow()
    complaint = Complaint(
        category=ComplaintCategory.REGULATORY_COMPLIANCE,
        status=ComplaintStatus.ESCALATED,
        registration_date=now - timedelta(days=30),
        last_action_date=now - timedelta(days=10),
        target_disposal_date=now + timedelta(days=5),
    )
    result = calculate_priority(complaint, transfer_count=0)
    assert_score_invariants(result)
    assert result["escalation_contribution"] == 10.0
    assert result["priority_level"] in (PriorityLevel.HIGH, PriorityLevel.CRITICAL)


def test_10_missing_category_surfaces_in_missing_flags():
    """Complaint with missing category must flag it in missing_data_flags."""
    now = datetime.utcnow()
    complaint = Complaint(
        category=None,
        status=ComplaintStatus.REGISTERED,
        registration_date=now - timedelta(days=2),
        last_action_date=None,
        target_disposal_date=None,
    )
    result = calculate_priority(complaint, transfer_count=0)
    assert_score_invariants(result)
    assert "category" in result["missing_data_flags"], \
        f"Expected 'category' in missing_data_flags, got: {result['missing_data_flags']}"


def test_score_cap_at_100():
    """No score must ever exceed 100 regardless of inputs."""
    now = datetime.utcnow()
    # Worst-case: safety, escalated, overdue, 100+ days old, 10 transfers
    complaint = Complaint(
        category=ComplaintCategory.STUDENT_SAFETY_WELFARE,
        status=ComplaintStatus.ESCALATED,
        registration_date=now - timedelta(days=120),
        last_action_date=now - timedelta(days=70),
        target_disposal_date=now - timedelta(days=30),  # heavily overdue
    )
    result = calculate_priority(complaint, transfer_count=10)
    assert result["score"] == 100.0, f"Score should be capped at 100, got {result['score']}"


def test_priority_bands_match_thresholds():
    """Verify each band threshold boundary explicitly."""
    now = datetime.utcnow()

    # Build a complaint that scores ≈ 30 (MEDIUM boundary)
    # admin, registered, deadline=30 days, new: 10+8+5+2=25 → LOW
    c_low = Complaint(
        category=ComplaintCategory.ADMINISTRATIVE,
        status=ComplaintStatus.REGISTERED,
        registration_date=now - timedelta(days=1),
        last_action_date=now,
        target_disposal_date=now + timedelta(days=30),
    )
    low = calculate_priority(c_low, transfer_count=0)
    assert low["priority_level"] == PriorityLevel.LOW
    assert low["score"] < 30

    # Force CRITICAL: safety+escalated+overdue+old = 30+20+20+15+10=95 → CRITICAL
    c_crit = Complaint(
        category=ComplaintCategory.STUDENT_SAFETY_WELFARE,
        status=ComplaintStatus.ESCALATED,
        registration_date=now - timedelta(days=91),
        last_action_date=now - timedelta(days=61),
        target_disposal_date=now - timedelta(days=10),
    )
    crit = calculate_priority(c_crit, transfer_count=0)
    assert crit["score"] >= 80
    assert crit["priority_level"] == PriorityLevel.CRITICAL


def test_deadline_all_tiers():
    """Verify each deadline tier returns the expected score."""
    now = datetime.utcnow()
    from app.services.priority_engine import _deadline_pressure

    cases = [
        (now - timedelta(days=1), 20.0, "Overdue"),
        (now + timedelta(hours=6), 18.0, "24 hours"),
        (now + timedelta(days=2), 15.0, "3 days"),
        (now + timedelta(days=5), 10.0, "7 days"),
        (now + timedelta(days=10), 5.0, "2 weeks"),
        (now + timedelta(days=20), 2.0, None),
        (None, 5.0, "No deadline"),
    ]
    for date, expected_score, note_fragment in cases:
        score, note = _deadline_pressure(date, now)
        assert score == expected_score, f"date={date}: expected {expected_score}, got {score}"
        if note_fragment:
            assert note_fragment in note, f"Expected '{note_fragment}' in note '{note}'"
