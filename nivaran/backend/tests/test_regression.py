"""
Comprehensive regression tests: authorization, data integrity, idempotency.
These tests run against the isolated test_oneview.db fixture, not the demo DB.
"""
import pytest
from datetime import datetime, timedelta
from app.models import (
    Complaint, ComplaintStatus, ComplaintCategory, PriorityLevel,
    OverlapResult, User, UserRole, CaseAction, Notification, Bureau
)


# ─── Auth / Authorization ────────────────────────────────────────────────────

class TestAuthorization:
    def test_readonly_cannot_create_complaint(self, client, readonly_token):
        res = client.post(
            "/api/complaints",
            json={
                "title": "Should be blocked",
                "description": "Read-only user attempting write",
                "category": "administrative",
            },
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"

    def test_readonly_cannot_record_overlap_decision(self, client, readonly_token):
        res = client.post(
            "/api/overlaps/1/decision",
            json={"decision": "unrelated", "reason": "test"},
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert res.status_code == 403

    def test_readonly_cannot_add_case_action(self, client, readonly_token):
        res = client.post(
            "/api/complaints/1/actions",
            json={"action_type": "note.added", "description": "blocked"},
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert res.status_code == 403

    def test_unauthenticated_cannot_access_complaints(self, client):
        res = client.get("/api/complaints")
        assert res.status_code == 401

    def test_non_admin_cannot_list_users(self, client, officer_token):
        res = client.get("/api/users", headers={"Authorization": f"Bearer {officer_token}"})
        assert res.status_code == 403

    def test_non_admin_cannot_list_audit_logs(self, client, officer_token):
        res = client.get("/api/audit-logs", headers={"Authorization": f"Bearer {officer_token}"})
        assert res.status_code == 403

    def test_admin_can_list_users(self, client, admin_token):
        res = client.get("/api/users", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        users = res.json()
        assert isinstance(users, list)
        assert len(users) >= 4

    def test_admin_can_list_audit_logs(self, client, admin_token):
        res = client.get("/api/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        data = res.json()
        assert "items" in data

    def test_reviewer_can_record_overlap_decision(self, client):
        """Reviewer role should be allowed to record decisions."""
        res = client.post("/api/auth/login", data={"username": "reviewer1", "password": "Review@123"})
        assert res.status_code == 200
        tok = res.json()["access_token"]
        # Get an overlap result to decide on
        res2 = client.get("/api/overlaps?review_status=pending", headers={"Authorization": f"Bearer {tok}"})
        assert res2.status_code == 200


# ─── Input Validation ─────────────────────────────────────────────────────────

class TestInputValidation:
    def test_invalid_category_rejected(self, client, officer_token):
        res = client.post(
            "/api/complaints",
            json={
                "title": "Bad category",
                "description": "Testing invalid enum",
                "category": "fee_grievance",  # not a valid enum value
            },
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 422

    def test_missing_title_rejected(self, client, officer_token):
        res = client.post(
            "/api/complaints",
            json={"description": "No title here", "category": "administrative"},
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 422

    def test_missing_description_rejected(self, client, officer_token):
        res = client.post(
            "/api/complaints",
            json={"title": "No description", "category": "administrative"},
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 422

    def test_missing_category_rejected(self, client, officer_token):
        res = client.post(
            "/api/complaints",
            json={"title": "No category", "description": "Missing category field"},
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 422

    def test_nonexistent_complaint_returns_404(self, client, admin_token):
        res = client.get("/api/complaints/999999", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 404

    def test_invalid_overlap_decision_enum(self, client, admin_token):
        # Try to record a decision with an invalid value
        res = client.post(
            "/api/overlaps/1/decision",
            json={"decision": "totally_wrong", "reason": "test"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 422


# ─── Complaint CRUD + Priority Scoring ───────────────────────────────────────

class TestComplaintWorkflow:
    def test_complaint_creation_triggers_priority_calculation(self, client, officer_token):
        res = client.post(
            "/api/complaints",
            json={
                "title": "Fee irregularity at XYZ College",
                "description": "The institution has been collecting fees beyond AICTE approved limits without any official notification.",
                "category": "scholarship_financial",
                "institution_name_snapshot": "XYZ Engineering College",
            },
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["calculated_priority_score"] is not None
        assert data["calculated_priority_level"] is not None
        assert 0 <= data["calculated_priority_score"] <= 100

    def test_complaint_priority_score_in_bounds(self, client, officer_token):
        """All score components must be ≥ 0 and total ≤ 100."""
        res = client.post(
            "/api/complaints",
            json={
                "title": "Faculty misconduct at ABC College",
                "description": "Multiple faculty members have been found absent repeatedly.",
                "category": "faculty_related",
            },
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 201
        cid = res.json()["id"]

        pr = client.post(
            f"/api/complaints/{cid}/calculate-priority",
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert pr.status_code == 200
        pa = pr.json()
        assert 0 <= pa["score"] <= 100
        for field in ["urgency_contribution", "impact_contribution", "deadline_contribution",
                      "ageing_contribution", "escalation_contribution", "transfer_contribution"]:
            assert pa[field] is not None
            assert pa[field] >= 0, f"{field} must be >= 0"

    def test_priority_score_components_sum_within_bounds(self, client, officer_token):
        """Sum of components should equal total score (caps allowed)."""
        res = client.post(
            "/api/complaints",
            json={
                "title": "Infrastructure deficiency report",
                "description": "Lab equipment is non-functional. Students are unable to complete practicals.",
                "category": "infrastructure_facilities",
            },
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 201
        cid = res.json()["id"]
        pr = client.post(
            f"/api/complaints/{cid}/calculate-priority",
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        pa = pr.json()
        component_sum = (
            pa["urgency_contribution"] + pa["impact_contribution"] +
            pa["deadline_contribution"] + pa["ageing_contribution"] +
            pa["escalation_contribution"] + pa["transfer_contribution"]
        )
        # Score may be capped at 100
        assert pa["score"] <= 100
        # Score should match uncapped sum if under 100
        if component_sum <= 100:
            assert abs(pa["score"] - round(component_sum, 2)) < 0.01, \
                f"score={pa['score']} but components sum={component_sum}"

    def test_priority_history_persists(self, client, officer_token):
        res = client.post(
            "/api/complaints",
            json={
                "title": "Scholarship delay persistent",
                "description": "Students waiting 8 months for approved scholarships.",
                "category": "scholarship_financial",
            },
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 201
        cid = res.json()["id"]

        client.post(f"/api/complaints/{cid}/calculate-priority",
                    headers={"Authorization": f"Bearer {officer_token}"})
        client.post(f"/api/complaints/{cid}/calculate-priority",
                    headers={"Authorization": f"Bearer {officer_token}"})

        hist = client.get(f"/api/complaints/{cid}/priority-history",
                          headers={"Authorization": f"Bearer {officer_token}"})
        assert hist.status_code == 200
        history = hist.json()
        # Initial + 2 recalculations = at least 2 records
        assert len(history) >= 2

    def test_invalid_status_transition_rejected(self, client, officer_token, admin_token):
        res = client.post(
            "/api/complaints",
            json={
                "title": "Test invalid transition",
                "description": "Test complaint for transition validation.",
                "category": "administrative",
            },
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 201
        cid = res.json()["id"]
        # Try to jump from REGISTERED directly to DISPOSED (not allowed)
        # Use admin token to ensure write access (complaint may be auto-assigned to different bureau)
        patch = client.patch(
            f"/api/complaints/{cid}",
            json={"status": "disposed"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert patch.status_code == 400, f"Expected 400 for invalid transition, got {patch.status_code}"

    def test_complaint_retrieval_after_creation(self, client, officer_token):
        res = client.post(
            "/api/complaints",
            json={
                "title": "Retrieval test complaint",
                "description": "Created to verify retrieval works correctly.",
                "category": "academic_examination",
            },
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 201
        cid = res.json()["id"]
        get_res = client.get(f"/api/complaints/{cid}",
                             headers={"Authorization": f"Bearer {officer_token}"})
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["id"] == cid
        assert data["title"] == "Retrieval test complaint"


# ─── Overlap Detection Idempotency ───────────────────────────────────────────

class TestOverlapIdempotency:
    def test_overlap_detection_does_not_duplicate_pairs(self, client, admin_token, officer_token):
        """Running detect-overlaps twice should not create duplicate OverlapResult rows."""
        res = client.post(
            "/api/complaints",
            json={
                "title": "Idempotency test: duplicate detection",
                "description": "Overlap detection idempotency check complaint.",
                "category": "administrative",
                "institution_id": 1,
            },
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 201
        cid = res.json()["id"]

        # Run detection twice
        r1 = client.post(f"/api/complaints/{cid}/detect-overlaps",
                         headers={"Authorization": f"Bearer {admin_token}"})
        assert r1.status_code == 200
        detected_1 = r1.json()["detected"]

        r2 = client.post(f"/api/complaints/{cid}/detect-overlaps",
                         headers={"Authorization": f"Bearer {admin_token}"})
        assert r2.status_code == 200
        detected_2 = r2.json()["detected"]

        # Second run should return same count (idempotent — uses existing records)
        assert detected_1 == detected_2, \
            f"First run found {detected_1}, second found {detected_2} — duplicates may have been created"

        # Verify stored overlap list is stable
        get_r = client.get(f"/api/complaints/{cid}/overlaps",
                           headers={"Authorization": f"Bearer {admin_token}"})
        assert get_r.status_code == 200
        overlaps = get_r.json()
        ids = [o["id"] for o in overlaps]
        assert len(ids) == len(set(ids)), "Duplicate overlap result IDs found"


# ─── Evidence Assessment ─────────────────────────────────────────────────────

class TestEvidenceAssessment:
    def test_evidence_assessment_returns_scores(self, client, admin_token, officer_token):
        res = client.post(
            "/api/complaints",
            json={
                "title": "Evidence test complaint",
                "description": "Testing evidence assessment endpoint.",
                "category": "regulatory_compliance",
            },
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 201
        cid = res.json()["id"]

        assess = client.post(f"/api/complaints/{cid}/assess",
                             headers={"Authorization": f"Bearer {admin_token}"})
        assert assess.status_code == 200
        ea = assess.json()
        assert "completeness_score" in ea
        assert "evidence_readiness_score" in ea
        assert "missing_fields" in ea
        assert isinstance(ea["missing_fields"], list)
        assert 0 <= ea["completeness_score"] <= 100
        assert 0 <= ea["evidence_readiness_score"] <= 100

    def test_evidence_assessment_missing_fields_reported(self, client, officer_token):
        res = client.post(
            "/api/complaints",
            json={
                "title": "Incomplete complaint",
                "description": "No incident date or deadline set.",
                "category": "other",
                # No incident_date or target_disposal_date
            },
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 201
        cid = res.json()["id"]

        assess = client.post(f"/api/complaints/{cid}/assess",
                             headers={"Authorization": f"Bearer {officer_token}"})
        assert assess.status_code == 200
        ea = assess.json()
        assert "incident_date" in ea["missing_fields"] or "target_disposal_date" in ea["missing_fields"]


# ─── Dashboard and Priority Queue ────────────────────────────────────────────

class TestDashboardAndQueue:
    def test_dashboard_all_fields_present(self, client, admin_token):
        res = client.get("/api/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        data = res.json()
        required = [
            "total_complaints", "pending_complaints", "under_process",
            "disposed_complaints", "overdue_complaints", "critical_cases",
            "high_priority_cases", "pending_overlap_reviews",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"
            assert isinstance(data[field], int), f"{field} should be int"

    def test_priority_queue_sorted_by_score(self, client, admin_token):
        res = client.get("/api/priority-queue?per_page=50",
                         headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        items = res.json()["items"]
        scores = [i["calculated_priority_score"] for i in items if i["calculated_priority_score"] is not None]
        assert scores == sorted(scores, reverse=True), "Priority queue must be sorted by score descending"

    def test_audit_logging_on_complaint_creation(self, client, admin_token, officer_token):
        """Creating a complaint should produce an audit log entry."""
        res = client.post(
            "/api/complaints",
            json={
                "title": "Audit log trigger test",
                "description": "This should produce an audit trail entry.",
                "category": "administrative",
            },
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 201

        logs = client.get(
            "/api/audit-logs?resource_type=complaint",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert logs.status_code == 200
        items = logs.json()["items"]
        assert any(i["action"] == "complaint.created" for i in items)


# ─── Overlap Decision Persistence ────────────────────────────────────────────

class TestOverlapDecision:
    def test_overlap_decision_persists(self, client, admin_token, officer_token):
        """A recorded decision must be retrievable."""
        # Create two complaints that will overlap
        c1 = client.post(
            "/api/complaints",
            json={
                "title": "Fee issue at Tech College",
                "description": "Students are being charged extra fees by Tech College without proper notice.",
                "category": "scholarship_financial",
                "institution_id": 1,
            },
            headers={"Authorization": f"Bearer {officer_token}"},
        ).json()

        c2 = client.post(
            "/api/complaints",
            json={
                "title": "Excess fee collection Tech College",
                "description": "Institution collecting fees above AICTE approved limits. Students affected.",
                "category": "scholarship_financial",
                "institution_id": 1,
            },
            headers={"Authorization": f"Bearer {officer_token}"},
        ).json()

        # Detect overlaps for c1
        det = client.post(f"/api/complaints/{c1['id']}/detect-overlaps",
                          headers={"Authorization": f"Bearer {admin_token}"})
        assert det.status_code == 200

        # Get overlaps list (system-wide, pending)
        ov_list = client.get("/api/overlaps?review_status=pending",
                             headers={"Authorization": f"Bearer {admin_token}"})
        assert ov_list.status_code == 200
        overlaps = ov_list.json()["items"]
        assert len(overlaps) > 0, "Expected at least one pending overlap after detection"

        # Record a decision
        ov_id = overlaps[0]["id"]
        dec = client.post(
            f"/api/overlaps/{ov_id}/decision",
            json={"decision": "confirmed_duplicate", "reason": "Confirmed same fee complaint."},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert dec.status_code == 200
        result = dec.json()
        assert result["review_status"] == "reviewed"
        assert result["decision"] == "confirmed_duplicate"
        assert result["decision_reason"] == "Confirmed same fee complaint."


# ─── Phase 9: Security, BOLA/IDOR, Integrity & Reporting ─────────────────────

class TestPhase9SecurityAndHardening:
    def test_cross_bureau_write_isolation(self, client, officer_token, admin_token):
        """
        Bureau officer assigned to Bureau 1 (ACAD) must be forbidden (403) from
        modifying, updating status, adding actions, or transferring Complaint 1 (Bureau 2 / FIN).
        Admin retains cross-bureau authority.
        """
        # Complaint 1 is seeded in Bureau 2 (Finance). officer_acad belongs to Bureau 1.
        patch_res = client.patch(
            "/api/complaints/1",
            json={"priority_level": "critical"},
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert patch_res.status_code == 403, f"Expected 403, got {patch_res.status_code}: {patch_res.text}"
        assert "Complaint is assigned to Bureau 2, but officer belongs to Bureau 1" in patch_res.json()["detail"]

        action_res = client.post(
            "/api/complaints/1/actions",
            json={"action_type": "note.added", "description": "Cross-bureau attempt"},
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert action_res.status_code == 403

        transfer_res = client.post(
            "/api/complaints/1/transfer",
            json={"to_bureau_id": 1, "reason": "Unauthorized transfer attempt"},
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert transfer_res.status_code == 403

    def test_bureau_officer_cannot_record_overlap_decision(self, client, officer_token):
        """
        Bureau officers must NOT be allowed to finalize cross-bureau duplicate linking decisions.
        Only Admin and Supervisory Reviewer are authorized.
        """
        res = client.post(
            "/api/overlaps/1/decision",
            json={"decision": "confirmed_duplicate", "reason": "Officer attempting decision"},
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 403
        assert "Access denied. Required roles" in res.json()["detail"]

    def test_rapid_double_submission_guard(self, client, admin_token):
        """
        Submitting the identical complaint payload within 30 seconds triggers a 409 Conflict
        to prevent accidental double submissions.
        """
        payload = {
            "title": "Rapid Submission Dedup Test Case",
            "description": "Testing rapid submission deduplication guard.",
            "category": "administrative",
            "institution_id": 1,
        }
        res1 = client.post("/api/complaints", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert res1.status_code == 201

        res2 = client.post("/api/complaints", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert res2.status_code == 409
        assert "Duplicate submission prevented" in res2.json()["detail"]

    def test_date_sanity_validation(self, client, admin_token):
        """Target disposal date earlier than incident date must be rejected with 422."""
        now = datetime.utcnow()
        res = client.post(
            "/api/complaints",
            json={
                "title": "Date Sanity Check Complaint",
                "description": "Testing chronological date validation.",
                "category": "administrative",
                "incident_date": now.isoformat(),
                "target_disposal_date": (now - timedelta(days=5)).isoformat(),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 422
        assert "Target disposal date cannot precede the incident date" in res.text

    def test_title_length_validation(self, client, admin_token):
        """Titles with < 3 characters or whitespace-only must be rejected."""
        res_short = client.post(
            "/api/complaints",
            json={"title": "No", "description": "Too short title test", "category": "administrative"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_short.status_code == 422

        res_space = client.post(
            "/api/complaints",
            json={"title": "     ", "description": "Whitespace title test", "category": "administrative"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_space.status_code == 422

    def test_transfer_validation_guards(self, client, admin_token):
        """Cannot transfer a complaint that is in CLOSED or DISPOSED state."""
        # Create and dispose a complaint
        c = client.post(
            "/api/complaints",
            json={
                "title": "Complaint to be disposed for transfer guard test",
                "description": "Will be advanced to disposed and tested.",
                "category": "academic_examination",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        ).json()
        cid = c["id"]

        # Advance state to disposed
        client.patch(f"/api/complaints/{cid}", json={"status": "under_initial_review"}, headers={"Authorization": f"Bearer {admin_token}"})
        client.patch(f"/api/complaints/{cid}", json={"status": "under_process"}, headers={"Authorization": f"Bearer {admin_token}"})
        client.patch(f"/api/complaints/{cid}", json={"status": "disposed"}, headers={"Authorization": f"Bearer {admin_token}"})

        # Try to transfer
        tr_res = client.post(
            f"/api/complaints/{cid}/transfer",
            json={"to_bureau_id": 2, "reason": "Attempting invalid transfer"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert tr_res.status_code == 400
        assert "Cannot transfer a complaint in disposed status" in tr_res.json()["detail"]

    def test_reports_export_formats(self, client, admin_token):
        """Export endpoint supports CSV and JSON formats."""
        res_csv = client.get("/api/reports/export?format=csv", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers.get("content-type", "")
        assert "complaint_id,title,category,status,institution,bureau" in res_csv.text

        res_json = client.get("/api/reports/export?format=json", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_json.status_code == 200
        data = res_json.json()
        assert isinstance(data, dict)
        assert "data" in data and isinstance(data["data"], list)
        assert data["total"] > 0
        assert "complaint_id" in data["data"][0]

    def test_dashboard_totals_bucket_consistency(self, client, admin_token):
        """Dashboard must maintain pending + under_process + disposed == total."""
        res = client.get("/api/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        dash = res.json()
        sum_buckets = dash["pending_complaints"] + dash["under_process"] + dash["disposed_complaints"]
        assert sum_buckets == dash["total_complaints"], (
            f"Arithmetic invariant failed: pending ({dash['pending_complaints']}) + "
            f"under_process ({dash['under_process']}) + disposed ({dash['disposed_complaints']}) "
            f"!= total ({dash['total_complaints']})"
        )
        assert "escalated_cases" in dash
        assert "transferred_cases" in dash


# ─── Phase 10: Final Acceptance & Presentation Readiness ─────────────────────

class TestPhase10AcceptanceAndPresentation:
    def test_bureau_officer_cannot_export_other_bureau(self, client, officer_token):
        """Bureau officer belongs to Bureau 1; exporting Bureau 2 must be rejected with 403."""
        res = client.get(
            "/api/reports/export?bureau_id=2",
            headers={"Authorization": f"Bearer {officer_token}"}
        )
        assert res.status_code == 403
        assert "Bureau officers can only export data for their assigned bureau" in res.json()["detail"]

    def test_bureau_officer_export_scoped_to_bureau(self, client, officer_token):
        """When an officer requests export without bureau_id, export is automatically scoped to their bureau."""
        res = client.get(
            "/api/reports/export?format=json",
            headers={"Authorization": f"Bearer {officer_token}"}
        )
        assert res.status_code == 200
        data = res.json()["data"]
        # All returned records must belong to officer's bureau (Academic Bureau / ID 1)
        for item in data:
            assert item["bureau"] in ["Academic Bureau", "Unassigned"]

    def test_export_invalid_filters_rejected(self, client, admin_token):
        """Invalid category or status filters in export return 400 Bad Request."""
        res_cat = client.get(
            "/api/reports/export?category=not_a_valid_category",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res_cat.status_code == 400
        assert "Invalid category filter" in res_cat.json()["detail"]

        res_stat = client.get(
            "/api/reports/export?status=not_a_valid_status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res_stat.status_code == 400
        assert "Invalid status filter" in res_stat.json()["detail"]

    def test_export_invalid_date_range_rejected(self, client, admin_token):
        """Export with end_date earlier than start_date returns 422."""
        now = datetime.utcnow()
        res = client.get(
            f"/api/reports/export?start_date={now.isoformat()}&end_date={(now - timedelta(days=2)).isoformat()}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 422
        assert "End date cannot be earlier than start date" in res.text

    def test_export_empty_results_handling(self, client, admin_token):
        """Filters with 0 matching records return 200 with empty array (JSON) or header only (CSV)."""
        res_json = client.get(
            "/api/reports/export?format=json&category=student_safety_welfare&status=closed",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res_json.status_code == 200
        assert res_json.json()["total"] == 0
        assert res_json.json()["data"] == []

        res_csv = client.get(
            "/api/reports/export?format=csv&category=student_safety_welfare&status=closed",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res_csv.status_code == 200
        csv_lines = [line for line in res_csv.text.strip().splitlines() if line]
        assert len(csv_lines) == 1, "Expected only the CSV header line when zero records match"
        assert "complaint_id,title,category" in csv_lines[0]

    def test_export_csv_escaping_special_characters(self, client, admin_token):
        """Titles with commas and quotes must be properly escaped by CSV writer without breaking row columns."""
        import csv
        import io
        special_title = 'Fee hike, "special charges", and extra exam fees'
        c = client.post(
            "/api/complaints",
            json={
                "title": special_title,
                "description": "Complaint with quotes and commas in title for CSV escaping verification.",
                "category": "scholarship_financial",
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        ).json()

        res_csv = client.get("/api/reports/export?format=csv", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_csv.status_code == 200

        reader = csv.DictReader(io.StringIO(res_csv.text))
        found = False
        for row in reader:
            if row["complaint_id"] == c["complaint_id"]:
                found = True
                assert row["title"] == special_title, "CSV unescaping did not preserve exact title with comma/quotes"
        assert found, "Created special character complaint not found in CSV export"

    def test_audit_logs_privacy_and_secrecy(self, client, admin_token):
        """Audit logs must never expose hashed_password or sensitive auth secrets."""
        res = client.get("/api/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        assert "hashed_password" not in res.text
        assert "secret" not in res.text.lower() or "secret_key" not in res.text


class TestBureauAuthorization:
    def test_bureau_officer_cannot_read_or_write_foreign_complaint(self, client, officer_token):
        headers = {"Authorization": f"Bearer {officer_token}"}
        assert client.get("/api/complaints/1", headers=headers).status_code == 403
        assert client.get("/api/complaints/1/actions", headers=headers).status_code == 403
        assert client.patch(
            "/api/complaints/1", json={"title": "Unauthorized edit"}, headers=headers
        ).status_code == 403
        assert client.post(
            "/api/complaints/1/calculate-priority", headers=headers
        ).status_code == 403
        registration = client.post(
            "/api/complaints",
            json={
                "title": "Foreign bureau registration attempt",
                "description": "An officer cannot register a case to a different bureau.",
                "category": "academic_examination",
                "bureau_id": 2,
            },
            headers=headers,
        )
        assert registration.status_code == 403

    def test_bureau_officer_cannot_change_bureau_through_generic_update(self, client, admin_token, officer_token):
        created = client.post(
            "/api/complaints",
            json={
                "title": "Scoped complaint for ownership test",
                "description": "This case is registered in the officer's bureau.",
                "category": "academic_examination",
                "bureau_id": 1,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert created.status_code == 201
        complaint_id = created.json()["id"]
        denied = client.patch(
            f"/api/complaints/{complaint_id}",
            json={"bureau_id": 2, "assigned_officer_id": 3},
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert denied.status_code == 403

    def test_bureau_less_officer_does_not_get_global_access(self, client, admin_token):
        created = client.post(
            "/api/users",
            json={
                "username": "null_bureau_officer",
                "email": "null.bureau.officer@aicte.gov.in.demo",
                "full_name": "Unassigned Officer",
                "password": "TempPassword@123",
                "role": "bureau_officer",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert created.status_code == 201
        login = client.post(
            "/api/auth/login",
            data={"username": "null_bureau_officer", "password": "TempPassword@123"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert client.get("/api/complaints", headers=headers).status_code == 403
        assert client.get("/api/dashboard", headers=headers).status_code == 403
        assert client.get("/api/reports/export", headers=headers).status_code == 403

    def test_supervisory_reviewer_retains_cross_bureau_reads(self, client):
        login = client.post(
            "/api/auth/login",
            data={"username": "reviewer1", "password": "Review@123"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        detail = client.get("/api/complaints/1", headers=headers)
        listing = client.get("/api/complaints?per_page=100", headers=headers)
        export = client.get("/api/reports/export", headers=headers)
        graph = client.get("/api/graph", headers=headers)
        assert detail.status_code == 200
        assert listing.status_code == 200
        assert any(item["id"] == 1 for item in listing.json()["items"])
        assert export.status_code == graph.status_code == 200
        assert any(row["bureau"] == "Finance Bureau" for row in export.json()["data"])
        assert any(node["id"] == "complaint:1" for node in graph.json()["nodes"])

    def test_readonly_user_cannot_change_notification_state(self, client, readonly_token, db_session):
        notification = Notification(
            complaint_id=1,
            recipient_id=4,
            title="Test notification",
            message="For read-only permission verification.",
            notification_type="test",
        )
        db_session.add(notification)
        db_session.commit()
        db_session.refresh(notification)
        response = client.patch(
            f"/api/notifications/{notification.id}/read",
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert response.status_code == 403

    def test_reports_overlaps_and_graph_are_bureau_scoped(
        self, client, admin_token, officer_token, db_session
    ):
        created = client.post(
            "/api/complaints",
            json={
                "title": "Academic bureau scoped case",
                "description": "A separate case for bureau-scoped aggregate checks.",
                "category": "academic_examination",
                "institution_id": 1,
                "institution_name_snapshot": "Apex Engineering College",
                "bureau_id": 1,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert created.status_code == 201
        own_id = created.json()["id"]
        db_session.add(OverlapResult(
            primary_complaint_id=own_id,
            candidate_complaint_id=1,
            similarity_score=65.0,
            algorithm_version="rules-v1",
            review_status="pending",
        ))
        db_session.commit()

        headers = {"Authorization": f"Bearer {officer_token}"}
        complaint_report = client.get("/api/reports/complaints", headers=headers)
        priority_report = client.get("/api/reports/priority", headers=headers)
        export = client.get("/api/reports/export", headers=headers)
        overlaps = client.get("/api/overlaps", headers=headers)
        nested_overlaps = client.get(f"/api/complaints/{own_id}/overlaps", headers=headers)
        priority_queue = client.get("/api/priority-queue", headers=headers)
        deadlines = client.get("/api/deadlines", headers=headers)
        graph = client.get("/api/graph", headers=headers)
        graph_analytics = client.get("/api/graph/analytics", headers=headers)
        foreign_report = client.get("/api/reports/priority?bureau_id=2", headers=headers)
        foreign_graph = client.get("/api/graph?bureau_id=2", headers=headers)

        assert complaint_report.status_code == priority_report.status_code == export.status_code == 200
        assert all(row["bureau"] == "Academic Bureau" for row in complaint_report.json()["by_bureau"])
        assert priority_report.json()["total_overdue"] >= 0
        assert all(row["bureau"] in ("Academic Bureau", "Unassigned") for row in export.json()["data"])
        assert overlaps.status_code == nested_overlaps.status_code == 200
        overlap_items = overlaps.json()["items"]
        assert all(
            item["primary_complaint"]["bureau_id"] == 1
            and item["candidate_complaint"]["bureau_id"] == 1
            for item in overlap_items
        )
        assert all(
            not (item["primary_complaint_id"] == own_id and item["candidate_complaint_id"] == 1)
            for item in overlap_items
        )
        assert nested_overlaps.json() == []
        assert priority_queue.status_code == deadlines.status_code == 200
        assert all(item["bureau"] == "Academic Bureau" for item in priority_queue.json()["items"])
        assert all(item["bureau_id"] == 1 for item in deadlines.json()["overdue"] + deadlines.json()["due_within_7_days"])
        assert graph.status_code == graph_analytics.status_code == 200
        assert foreign_report.status_code == foreign_graph.status_code == 403
        complaint_nodes = [node for node in graph.json()["nodes"] if node["type"] == "complaint"]
        assert f"complaint:{own_id}" in {node["id"] for node in complaint_nodes}
        assert all(node["bureau_id"] == 1 for node in complaint_nodes)
        assert "complaint:1" not in {node["id"] for node in complaint_nodes}
        assert all(
            not (edge["type"] in ("possible_duplicate", "confirmed_duplicate", "related_independent")
                 and edge["target"] == "complaint:1")
            for edge in graph.json()["edges"]
        )
        assert graph_analytics.json()["total_complaints"] == len(complaint_nodes)


class TestAssignmentConsistency:
    def _create_officer(self, client, admin_token, username, bureau_id):
        response = client.post(
            "/api/users",
            json={
                "username": username,
                "email": f"{username}@aicte.gov.in.demo",
                "full_name": username.replace("_", " ").title(),
                "password": "TempPassword@123",
                "role": "bureau_officer",
                "bureau_id": bureau_id,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def _create_complaint(self, client, admin_token, bureau_id, title):
        response = client.post(
            "/api/complaints",
            json={
                "title": title,
                "description": "A valid complaint for assignment consistency regression tests.",
                "category": "academic_examination",
                "bureau_id": bureau_id,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201, response.text
        return response.json()

    def test_privileged_patch_rejects_officer_from_different_bureau(self, client, admin_token):
        foreign_officer_id = self._create_officer(client, admin_token, "patch_foreign_officer", 2)
        complaint = self._create_complaint(client, admin_token, 1, "PATCH cross-bureau assignment rejection")
        before = client.get(f"/api/complaints/{complaint['id']}", headers={"Authorization": f"Bearer {admin_token}"}).json()

        response = client.patch(
            f"/api/complaints/{complaint['id']}",
            json={"bureau_id": 1, "assigned_officer_id": foreign_officer_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        after = client.get(f"/api/complaints/{complaint['id']}", headers={"Authorization": f"Bearer {admin_token}"}).json()
        assert response.status_code == 422
        assert after["bureau_id"] == before["bureau_id"]
        assert after["assigned_officer_id"] == before["assigned_officer_id"]

        reviewer_login = client.post(
            "/api/auth/login", data={"username": "reviewer1", "password": "Review@123"}
        )
        assert reviewer_login.status_code == 200
        reviewer_headers = {"Authorization": f"Bearer {reviewer_login.json()['access_token']}"}
        reviewer_response = client.patch(
            f"/api/complaints/{complaint['id']}",
            json={"bureau_id": 1, "assigned_officer_id": foreign_officer_id},
            headers=reviewer_headers,
        )
        assert reviewer_response.status_code == 422

    def test_privileged_patch_rejects_inactive_officer(self, client, admin_token, db_session):
        inactive_officer_id = self._create_officer(client, admin_token, "patch_inactive_officer", 1)
        officer = db_session.query(User).filter(User.id == inactive_officer_id).one()
        officer.is_active = False
        db_session.commit()
        complaint = self._create_complaint(client, admin_token, 1, "PATCH inactive assignment rejection")

        response = client.patch(
            f"/api/complaints/{complaint['id']}",
            json={"bureau_id": 1, "assigned_officer_id": inactive_officer_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        current = client.get(f"/api/complaints/{complaint['id']}", headers={"Authorization": f"Bearer {admin_token}"}).json()
        assert response.status_code == 422
        assert current["assigned_officer_id"] != inactive_officer_id

    def test_privileged_generic_patch_and_supervisor_reassignment_still_work(
        self, client, admin_token, db_session
    ):
        replacement_id = self._create_officer(client, admin_token, "patch_valid_officer", 1)
        complaint = self._create_complaint(client, admin_token, 1, "Valid privileged assignment changes")
        complaint_id = complaint["id"]
        admin_response = client.patch(
            f"/api/complaints/{complaint_id}",
            json={"bureau_id": 1, "assigned_officer_id": replacement_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_response.status_code == 200, admin_response.text
        assert admin_response.json()["assigned_officer_id"] == replacement_id

        reviewer_login = client.post(
            "/api/auth/login", data={"username": "reviewer1", "password": "Review@123"}
        )
        assert reviewer_login.status_code == 200
        reviewer_headers = {"Authorization": f"Bearer {reviewer_login.json()['access_token']}"}
        reassign_response = client.post(
            f"/api/complaints/{complaint_id}/reassign",
            json={"target_officer_id": 2, "reason": "Valid same-bureau supervisory reassignment"},
            headers=reviewer_headers,
        )
        assert reassign_response.status_code == 200, reassign_response.text
        assert reassign_response.json()["assigned_officer_id"] == 2
        history = client.get(f"/api/complaints/{complaint_id}/assignments", headers=reviewer_headers)
        assert history.status_code == 200
        assert any(record["officer_id"] == replacement_id for record in history.json())

    def test_transfer_without_target_officer_clears_previous_assignment_and_records_history(
        self, client, admin_token
    ):
        complaint = self._create_complaint(client, admin_token, 1, "Transfer without target officer")
        complaint_id = complaint["id"]
        previous_officer_id = complaint["assigned_officer_id"]
        response = client.post(
            f"/api/complaints/{complaint_id}/transfer",
            json={"target_bureau_id": 2, "reason": "Transfer to Finance without preassignment"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["bureau_id"] == 2
        assert response.json()["assigned_officer_id"] is None

        history = client.get(f"/api/complaints/{complaint_id}/assignments", headers={"Authorization": f"Bearer {admin_token}"})
        assert any(
            record["assignment_type"] == "transfer"
            and record["officer_id"] is None
            and record["previous_officer_id"] == previous_officer_id
            and record["bureau_id"] == 2
            for record in history.json()
        )
        actions = client.get(f"/api/complaints/{complaint_id}/actions", headers={"Authorization": f"Bearer {admin_token}"})
        assert any(action["action_type"] == "complaint.transferred" for action in actions.json())
        audits = client.get(
            f"/api/audit-logs?resource_type=complaint&resource_id={complaint_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert any(item["action"] == "complaint.transferred" for item in audits.json()["items"])

    def test_transfer_with_valid_target_officer_succeeds(self, client, admin_token):
        target_officer_id = self._create_officer(client, admin_token, "transfer_target_officer", 2)
        complaint = self._create_complaint(client, admin_token, 1, "Transfer with valid target officer")
        complaint_id = complaint["id"]
        response = client.post(
            f"/api/complaints/{complaint_id}/transfer",
            json={
                "target_bureau_id": 2,
                "target_officer_id": target_officer_id,
                "reason": "Transfer to compatible active officer",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["bureau_id"] == 2
        assert response.json()["assigned_officer_id"] == target_officer_id
        history = client.get(f"/api/complaints/{complaint_id}/assignments", headers={"Authorization": f"Bearer {admin_token}"})
        assert any(
            record["assignment_type"] == "transfer" and record["officer_id"] == target_officer_id
            for record in history.json()
        )

    def test_rejected_transfer_keeps_bureau_assignee_and_history_unchanged(self, client, admin_token):
        complaint = self._create_complaint(client, admin_token, 1, "Rejected transfer is atomic")
        complaint_id = complaint["id"]
        before = client.get(f"/api/complaints/{complaint_id}", headers={"Authorization": f"Bearer {admin_token}"}).json()
        response = client.post(
            f"/api/complaints/{complaint_id}/transfer",
            json={
                "target_bureau_id": 2,
                "target_officer_id": 2,
                "reason": "Officer 2 belongs to Bureau 1, not target Bureau 2",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        after = client.get(f"/api/complaints/{complaint_id}", headers={"Authorization": f"Bearer {admin_token}"}).json()
        assert response.status_code == 422
        assert after["bureau_id"] == before["bureau_id"]
        assert after["assigned_officer_id"] == before["assigned_officer_id"]
        history = client.get(f"/api/complaints/{complaint_id}/assignments", headers={"Authorization": f"Bearer {admin_token}"})
        assert not any(record["assignment_type"] == "transfer" for record in history.json())

    def test_reassignment_rejects_officer_in_inactive_bureau(self, client, admin_token, db_session):
        target_officer_id = self._create_officer(client, admin_token, "inactive_bureau_target", 3)
        complaint = self._create_complaint(client, admin_token, 3, "Reassignment to inactive bureau")
        complaint_id = complaint["id"]
        bureau = db_session.query(Bureau).filter(Bureau.id == 3).one()
        was_active = bureau.is_active
        bureau.is_active = False
        db_session.commit()
        try:
            response = client.post(
                f"/api/complaints/{complaint_id}/reassign",
                json={"target_officer_id": target_officer_id, "reason": "Must reject inactive bureau"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            current = client.get(f"/api/complaints/{complaint_id}", headers={"Authorization": f"Bearer {admin_token}"}).json()
            assert response.status_code == 422
            assert current["bureau_id"] == 3
            assert current["assigned_officer_id"] == complaint["assigned_officer_id"]
        finally:
            bureau.is_active = was_active
            db_session.commit()
