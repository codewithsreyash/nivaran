from datetime import datetime, timedelta
from app.models import Complaint, ComplaintCategory, Institution, InstitutionVerificationStatus
from app.services.evidence_service import assess_complaint


def test_assess_complaint_complete(db_session):
    now = datetime.utcnow()
    inst = db_session.query(Institution).filter_by(id=1).first()
    complaint = Complaint(
        complaint_id="AICTE-TEST-COMP-01",
        title="Complete Complaint Title",
        description="Detailed description of the issue that meets the threshold.",
        category=ComplaintCategory.ACADEMIC_EXAMINATION,
        institution_id=inst.id,
        institution_name_snapshot=inst.name,
        incident_date=now - timedelta(days=5),
        registration_date=now,
        target_disposal_date=now + timedelta(days=10)
    )
    db_session.add(complaint)
    db_session.flush()

    assessment = assess_complaint(db_session, complaint)
    assert assessment.completeness_score == 100.0
    assert assessment.date_consistency_ok is True
    assert len(assessment.missing_fields) == 0


def test_assess_complaint_missing_fields(db_session):
    complaint = Complaint(
        complaint_id="AICTE-TEST-COMP-02",
        title="Incomplete Case",
        description="",  # missing description
        category=ComplaintCategory.OTHER,
        institution_id=None,
        institution_name_snapshot=None,
        incident_date=None,
        registration_date=datetime.utcnow(),
        target_disposal_date=None
    )
    db_session.add(complaint)
    db_session.flush()

    assessment = assess_complaint(db_session, complaint)
    assert assessment.completeness_score < 50.0
    assert "description" in assessment.missing_fields
    assert "incident_date" in assessment.missing_fields


def test_assess_complaint_date_inconsistency(db_session):
    now = datetime.utcnow()
    complaint = Complaint(
        complaint_id="AICTE-TEST-COMP-03",
        title="Date issue complaint",
        description="Description here.",
        category=ComplaintCategory.OTHER,
        institution_name_snapshot="Apex College",
        incident_date=now + timedelta(days=5),  # incident in future relative to registration
        registration_date=now,
        target_disposal_date=now + timedelta(days=10)
    )
    db_session.add(complaint)
    db_session.flush()

    assessment = assess_complaint(db_session, complaint)
    assert assessment.date_consistency_ok is False
    assert len(assessment.consistency_issues) > 0
