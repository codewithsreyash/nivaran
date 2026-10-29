"""Evidence and completeness assessment service."""
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from ..models import Complaint, EvidenceAssessment, SupportingDocument


REQUIRED_FIELDS = ["title", "description", "category", "institution_name_snapshot"]


def assess_complaint(db: Session, complaint: Complaint, assessor_id: Optional[int] = None) -> EvidenceAssessment:
    """Run completeness and consistency checks on a complaint."""
    now = datetime.utcnow()
    missing_fields: List[str] = []

    for field in REQUIRED_FIELDS:
        val = getattr(complaint, field, None)
        if not val:
            missing_fields.append(field)

    if not complaint.incident_date:
        missing_fields.append("incident_date")
    if not complaint.target_disposal_date:
        missing_fields.append("target_disposal_date")

    # Completeness score
    total_fields = len(REQUIRED_FIELDS) + 2
    completeness = ((total_fields - len(missing_fields)) / total_fields) * 100

    # Document count
    doc_count = db.query(SupportingDocument).filter(
        SupportingDocument.complaint_id == complaint.id
    ).count()

    # Evidence readiness: completeness + documents
    evidence_readiness = completeness * 0.6 + min(doc_count * 20, 40)
    evidence_readiness = min(evidence_readiness, 100)

    # Institution verified?
    institution_verified = (
        complaint.institution is not None and
        complaint.institution.verification_status.value == "verified"
    ) if complaint.institution else False

    # Date consistency
    date_ok: Optional[bool] = None
    consistency_issues: List[str] = []
    if complaint.incident_date and complaint.registration_date:
        if complaint.incident_date > complaint.registration_date:
            consistency_issues.append(
                "Incident date is after registration date — review needed."
            )
            date_ok = False
        else:
            date_ok = True

    # Status label
    if completeness >= 90 and evidence_readiness >= 70 and institution_verified:
        status = "No Material Concern Identified in Available Checks"
    elif consistency_issues:
        status = "Contradiction Requires Review"
    elif completeness < 50:
        status = "Information Incomplete"
    elif not institution_verified:
        status = "Verification Required"
    else:
        status = "Evidence Under Review"

    assessment = EvidenceAssessment(
        complaint_id=complaint.id,
        completeness_score=round(completeness, 1),
        evidence_readiness_score=round(evidence_readiness, 1),
        institution_verified=institution_verified,
        date_consistency_ok=date_ok,
        document_count=doc_count,
        missing_fields=missing_fields,
        consistency_issues=consistency_issues if consistency_issues else None,
        status=status,
        assessed_by_id=assessor_id,
        assessed_at=now,
    )
    db.add(assessment)

    # Update complaint summary fields
    complaint.completeness_score = round(completeness, 1)
    complaint.evidence_readiness_score = round(evidence_readiness, 1)
    complaint.evidence_assessment_status = status

    db.commit()
    db.refresh(assessment)
    return assessment
