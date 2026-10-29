from datetime import datetime, timedelta
from app.models import Complaint, ComplaintCategory
from app.services.overlap_engine import (
    compute_overlap, _institution_score, _category_score,
    _description_score, _date_score, _keyword_overlap, ALGORITHM_VERSION
)


def test_institution_score_same_id():
    c1 = Complaint(institution_id=5, institution_name_snapshot="National Tech Institute")
    c2 = Complaint(institution_id=5, institution_name_snapshot="National Tech Institute")
    score, note = _institution_score(c1, c2)
    assert score == 30.0
    assert "Same verified" in note


def test_institution_score_different_id():
    c1 = Complaint(institution_id=5, institution_name_snapshot="National Tech Institute")
    c2 = Complaint(institution_id=8, institution_name_snapshot="Regional Engineering College")
    score, note = _institution_score(c1, c2)
    assert score == 0.0
    assert "Different" in note


def test_category_score():
    c1 = Complaint(category=ComplaintCategory.SCHOLARSHIP_FINANCIAL)
    c2 = Complaint(category=ComplaintCategory.SCHOLARSHIP_FINANCIAL)
    c3 = Complaint(category=ComplaintCategory.INFRASTRUCTURE_FACILITIES)
    score_match, _ = _category_score(c1, c2)
    score_mismatch, _ = _category_score(c1, c3)
    assert score_match == 15.0
    assert score_mismatch == 0.0


def test_description_score_similar():
    c1 = Complaint(description="Hostel drinking water contaminated causing illness among students.")
    c2 = Complaint(description="Drinking water contaminated in hostel mess; students fallen ill.")
    score, note = _description_score(c1, c2)
    assert score > 20.0
    assert "Description similarity" in note


def test_compute_overlap_full():
    now = datetime.utcnow()
    c1 = Complaint(
        complaint_id="C1",
        title="Scholarship delay for BTech batches",
        description="Scholarship disbursal pending for 6 months despite submission of all documents.",
        category=ComplaintCategory.SCHOLARSHIP_FINANCIAL,
        institution_id=1,
        registration_date=now
    )
    c2 = Complaint(
        complaint_id="C2",
        title="Pending scholarship funds disbursal",
        description="Scholarship disbursal pending for 6 months for engineering students.",
        category=ComplaintCategory.SCHOLARSHIP_FINANCIAL,
        institution_id=1,
        registration_date=now - timedelta(days=2)
    )

    result = compute_overlap(c1, c2)
    assert result["similarity_score"] >= 65.0
    assert result["institution_score"] == 30.0
    assert result["category_score"] == 15.0
    assert result["algorithm_version"] == ALGORITHM_VERSION
    assert "scholarship" in [kw.lower() for kw in result["matching_keywords"]]


def test_date_score_missing_dates_does_not_crash():
    """Verify that complaints missing dates return 0.0 without throwing NoneType exceptions."""
    c1 = Complaint(incident_date=None, registration_date=None)
    c2 = Complaint(incident_date=None, registration_date=None)
    score, note = _date_score(c1, c2)
    assert score == 0.0
    assert "missing dates" in note

    # Partial date
    c3 = Complaint(incident_date=datetime.utcnow(), registration_date=None)
    score_p, note_p = _date_score(c1, c3)
    assert score_p == 0.0


def test_date_score_ranges():
    now = datetime.utcnow()
    c1 = Complaint(incident_date=now)
    c2 = Complaint(incident_date=now - timedelta(days=3))
    c3 = Complaint(incident_date=now - timedelta(days=20))
    c4 = Complaint(incident_date=now - timedelta(days=60))
    c5 = Complaint(incident_date=now - timedelta(days=120))

    assert _date_score(c1, c2)[0] == 10.0  # <= 7 days
    assert _date_score(c1, c3)[0] == 6.0   # <= 30 days
    assert _date_score(c1, c4)[0] == 3.0   # <= 90 days
    assert _date_score(c1, c5)[0] == 0.0   # > 90 days
