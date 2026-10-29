from datetime import datetime, timedelta
from app.models import Complaint, ComplaintCategory, ComplaintStatus, PriorityLevel
from app.services.priority_engine import (
    calculate_priority, _deadline_pressure, _ageing_contribution,
    CALCULATION_VERSION, URGENCY_MAP
)


def test_urgency_score_weights():
    score_safety = URGENCY_MAP[ComplaintCategory.STUDENT_SAFETY_WELFARE.value]
    score_admin = URGENCY_MAP[ComplaintCategory.ADMINISTRATIVE.value]
    assert score_safety == 30.0
    assert score_admin == 10.0
    assert score_safety > score_admin


def test_deadline_pressure_overdue():
    now = datetime.utcnow()
    past_date = now - timedelta(days=3)
    score, note = _deadline_pressure(past_date, now)
    assert score == 20.0
    assert "Overdue" in note


def test_deadline_pressure_near_future():
    now = datetime.utcnow()
    near_date = now + timedelta(hours=12)
    score, note = _deadline_pressure(near_date, now)
    assert score == 18.0
    assert "24 hours" in note


def test_deadline_pressure_far_future():
    now = datetime.utcnow()
    far_date = now + timedelta(days=20)
    score, note = _deadline_pressure(far_date, now)
    assert score == 2.0


def test_ageing_contribution():
    now = datetime.utcnow()
    reg_date = now - timedelta(days=100)
    last_act = now - timedelta(days=65)
    score, note = _ageing_contribution(reg_date, last_act, now)
    assert score == 15.0
    assert "100 days old" in note


def test_calculate_priority_critical_case():
    now = datetime.utcnow()
    complaint = Complaint(
        category=ComplaintCategory.STUDENT_SAFETY_WELFARE,
        status=ComplaintStatus.ESCALATED,
        target_disposal_date=now - timedelta(days=2),
        registration_date=now - timedelta(days=60),
        last_action_date=now - timedelta(days=25)
    )
    result = calculate_priority(complaint, transfer_count=2)
    assert result["score"] >= 80.0
    assert result["priority_level"] == PriorityLevel.CRITICAL
    assert result["calculation_version"] == CALCULATION_VERSION
    assert result["urgency_contribution"] == 30.0
    assert result["impact_contribution"] == 20.0
    assert result["transfer_contribution"] == 5.0


def test_calculate_priority_low_case():
    now = datetime.utcnow()
    complaint = Complaint(
        category=ComplaintCategory.OTHER,
        status=ComplaintStatus.REGISTERED,
        target_disposal_date=now + timedelta(days=30),
        registration_date=now - timedelta(days=1),
        last_action_date=now
    )
    result = calculate_priority(complaint, transfer_count=0)
    assert result["score"] < 30.0
    assert result["priority_level"] == PriorityLevel.LOW
