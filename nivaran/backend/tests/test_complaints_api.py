from datetime import datetime, timedelta
from app.models import ComplaintStatus, ComplaintCategory


def test_list_complaints(client, admin_token):
    res = client.get("/api/complaints", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    item = data["items"][0]
    assert "complaint_id" in item
    assert "title" in item


def test_get_complaint_detail(client, admin_token):
    res = client.get("/api/complaints/1", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == 1
    assert data["institution_name_snapshot"] == "Apex Engineering College"
    assert data["status"] == "under_process"


def test_get_complaint_not_found(client, admin_token):
    res = client.get("/api/complaints/99999", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 404


def test_create_complaint_as_officer(client, officer_token):
    payload = {
        "title": "Severe Water Logging in Academic Block",
        "description": "Continuous water logging blocking laboratory access for final year students.",
        "category": "infrastructure_facilities",
        "institution_id": 1,
        "institution_name_snapshot": "Apex Engineering College",
        "bureau_id": 1,
        "is_anonymous": False
    }
    res = client.post(
        "/api/complaints",
        json=payload,
        headers={"Authorization": f"Bearer {officer_token}"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == payload["title"]
    assert "AICTE-" in data["complaint_id"]
    assert data["calculated_priority_score"] is not None
    assert data["calculated_priority_level"] is not None


def test_create_complaint_as_readonly_forbidden(client, readonly_token):
    payload = {
        "title": "Unauthorized Fee Hike",
        "description": "Fees hiked without approval.",
        "category": "regulatory_compliance"
    }
    res = client.post(
        "/api/complaints",
        json=payload,
        headers={"Authorization": f"Bearer {readonly_token}"}
    )
    assert res.status_code == 403
    assert "Read-only" in res.json()["detail"]


def test_add_case_action(client, admin_token):
    payload = {
        "action_type": "official_note",
        "description": "Reviewed documents submitted by applicant.",
        "metadata_json": {"doc_count": 2}
    }
    res = client.post(
        "/api/complaints/1/actions",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["action_type"] == "official_note"
    assert "Reviewed documents" in data["description"]


def test_update_status_valid_and_invalid_transitions(client, admin_token):
    # Valid transition: UNDER_PROCESS -> ESCALATED
    res = client.patch(
        "/api/complaints/1",
        json={"status": "escalated"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "escalated"

    # Invalid transition: ESCALATED cannot go back to REGISTERED
    bad_res = client.patch(
        "/api/complaints/1",
        json={"status": "registered"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert bad_res.status_code == 400
    assert "Invalid transition" in bad_res.json()["detail"]
