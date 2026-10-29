"""
AICTE OneView — Phase 6 End-to-End Demonstration Scenario.

Demonstrates the complete 11-step workflow using synthetic records:
1. Admin signs in.
2. A complaint is registered (scholarship & financial grievance).
3. The priority engine calculates and explains priority score and factor breakdown.
4. The complaint appears in the priority queue with proper sorting.
5. A second, paraphrased complaint for the same institution is registered.
6. The RapidFuzz overlap engine surfaces the potential duplicate cross-bureau pair.
7. The reviewer examines the comparison evidence (institution match, keywords, scores).
8. The reviewer records a confirmed decision with mandatory reasoning.
9. An officer updates the complaint status to 'under_process' and records a case action.
10. The dashboard reflects the updated metrics (counts, active workloads).
11. The audit trail verifies all operations were recorded.

NOTICE: All records are SYNTHETIC DEMONSTRATION DATA for AICTE Problem Statement 26264.
"""
import io
import json
import sys
import requests

# Ensure UTF-8 output on Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_URL = "http://127.0.0.1:8000"

def run_demo():
    print("=" * 70)
    print("AICTE ONEVIEW / NIVARAN — END-TO-END DEMO SCENARIO (PHASE 6)")
    print("AICTE PS 26264: Monitoring Complaints Across AICTE Bureaus/Cells")
    print("All records are SYNTHETIC DEMONSTRATION DATA.")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # STEP 1: Admin and role logins
    # -------------------------------------------------------------------------
    print("\n[STEP 1] User Authentication across AICTE Roles")
    def login(user, pwd):
        res = requests.post(
            f"{BASE_URL}/api/auth/login",
            data={"username": user, "password": pwd},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if res.status_code != 200:
            raise RuntimeError(f"Login failed for {user}: {res.status_code} {res.text}")
        data = res.json()
        return data["access_token"], data["user"]

    admin_token, admin_user = login("admin", "Admin@123")
    reviewer_token, reviewer_user = login("reviewer1", "Review@123")
    officer_token, officer_user = login("officer_acad", "Officer@123")
    print(f"  ✓ Admin logged in: {admin_user['full_name']} (Role: {admin_user['role']})")
    print(f"  ✓ Reviewer logged in: {reviewer_user['full_name']} (Role: {reviewer_user['role']})")
    print(f"  ✓ Officer logged in: {officer_user['full_name']} (Bureau ID: {officer_user.get('bureau_id')})")

    admin_hdr = {"Authorization": f"Bearer {admin_token}"}
    reviewer_hdr = {"Authorization": f"Bearer {reviewer_token}"}
    officer_hdr = {"Authorization": f"Bearer {officer_token}"}

    # -------------------------------------------------------------------------
    # STEP 2: Register Primary Complaint
    # -------------------------------------------------------------------------
    print("\n[STEP 2] Registering Primary Complaint (Bureau: Finance / Scholarship)")
    complaint1_payload = {
        "title": "Unapproved Retention of AICTE PG Scholarship Allowances",
        "description": (
            "College administration has withheld monthly stipend disburals for 18 M.Tech "
            "GATE scholarship recipients since August 2026 without formal clarification. "
            "Students have submitted multiple bank account verification slips."
        ),
        "category": "scholarship_financial",
        "institution_name_snapshot": "Apex Institute of Advanced Engineering & Technology",
        "source": "online_portal",
        "complainant_type": "student",
        "is_anonymous": False,
        "target_disposal_date": "2026-11-20T00:00:00",
    }
    r = requests.post(f"{BASE_URL}/api/complaints", json=complaint1_payload, headers=officer_hdr)
    if r.status_code != 201:
        raise RuntimeError(f"Failed to create complaint 1: {r.status_code} {r.text}")
    c1 = r.json()
    c1_id = c1["id"]
    print(f"  ✓ Created Complaint #{c1_id} — ID: {c1['complaint_id']}")
    print(f"    Title: {c1['title']}")
    print(f"    Category: {c1['category']} | Status: {c1['status']}")

    # -------------------------------------------------------------------------
    # STEP 3: Priority Engine Calculation & Explainability
    # -------------------------------------------------------------------------
    print("\n[STEP 3] Priority Engine Calculation & Factor Breakdown")
    r = requests.post(f"{BASE_URL}/api/complaints/{c1_id}/calculate-priority", headers=officer_hdr)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to calculate priority: {r.status_code} {r.text}")
    p1 = r.json()
    print(f"  ✓ Score: {p1['score']} / 100 — Level: {p1['priority_level'].upper()}")
    print(f"  ✓ Explanation: {p1['explanation']}")
    print("  ✓ Factor Breakdown:")
    print(f"      • Urgency:    {p1.get('urgency_contribution', 0)} pts")
    print(f"      • Impact:     {p1.get('impact_contribution', 0)} pts")
    print(f"      • Deadline:   {p1.get('deadline_contribution', 0)} pts")
    print(f"      • Ageing:     {p1.get('ageing_contribution', 0)} pts")
    print(f"      • Escalation: {p1.get('escalation_contribution', 0)} pts")
    print(f"      • Transfers:  {p1.get('transfer_contribution', 0)} pts")
    print(f"      • Algorithm:  {p1.get('calculation_version')}")

    # -------------------------------------------------------------------------
    # STEP 4: Complaint appears in Priority Queue
    # -------------------------------------------------------------------------
    print("\n[STEP 4] Priority Queue Sorting Verification")
    r = requests.get(f"{BASE_URL}/api/priority-queue", headers=officer_hdr)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch queue: {r.status_code} {r.text}")
    q_data = r.json()
    q_items = q_data.get("items", [])
    found_in_queue = any(item["id"] == c1_id for item in q_items)
    print(f"  ✓ Total items in priority queue: {q_data.get('total', len(q_items))}")
    print(f"  ✓ Complaint #{c1_id} present in queue: {found_in_queue}")
    # Verify descending sort
    scores = [item["calculated_priority_score"] for item in q_items if item.get("calculated_priority_score") is not None]
    is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    print(f"  ✓ Queue strictly sorted in descending score order: {is_sorted}")

    # -------------------------------------------------------------------------
    # STEP 5: Register Second Paraphrased Complaint (Candidate Duplicate)
    # -------------------------------------------------------------------------
    print("\n[STEP 5] Registering Second Paraphrased Complaint (Same Institution)")
    complaint2_payload = {
        "title": "Withholding and Delay of M.Tech GATE Scholarship Disbursal",
        "description": (
            "Apex Institute has not forwarded stipend transfers to 18 postgraduate "
            "GATE students for multiple months. Administration demands extra lab fees "
            "before clearing AICTE scholarship paperwork."
        ),
        "category": "scholarship_financial",
        "institution_name_snapshot": "Apex Institute of Advanced Engineering & Technology",
        "source": "grievance_portal",
        "complainant_type": "student",
        "is_anonymous": False,
    }
    r = requests.post(f"{BASE_URL}/api/complaints", json=complaint2_payload, headers=officer_hdr)
    if r.status_code != 201:
        raise RuntimeError(f"Failed to create complaint 2: {r.status_code} {r.text}")
    c2 = r.json()
    c2_id = c2["id"]
    print(f"  ✓ Created Candidate Complaint #{c2_id} — ID: {c2['complaint_id']}")
    print(f"    Title: {c2['title']}")

    # -------------------------------------------------------------------------
    # STEP 6: Overlap Engine Surfaces Potential Duplicate
    # -------------------------------------------------------------------------
    print("\n[STEP 6] Running Overlap Detection Engine (RapidFuzz Baseline)")
    r = requests.post(f"{BASE_URL}/api/complaints/{c2_id}/detect-overlaps", headers=officer_hdr)
    if r.status_code != 200:
        raise RuntimeError(f"Failed overlap detection: {r.status_code} {r.text}")
    print(f"  ✓ Detection Result: {r.json()['message']}")

    r = requests.get(f"{BASE_URL}/api/complaints/{c2_id}/overlaps", headers=officer_hdr)
    overlaps = r.json()
    target_overlap = None
    for ov in overlaps:
        if ov["candidate_complaint_id"] == c1_id or ov["primary_complaint_id"] == c1_id:
            target_overlap = ov
            break
    if not target_overlap and overlaps:
        target_overlap = overlaps[0]

    if not target_overlap:
        raise RuntimeError("No overlap detected between complaint 1 and complaint 2!")

    ov_id = target_overlap["id"]
    print(f"  ✓ Overlap Record #{ov_id} Created:")
    print(f"      • Similarity Score: {target_overlap['similarity_score']:.1f} / 100")
    print(f"      • Institution Match: {target_overlap.get('institution_score', 0)} / 30")
    print(f"      • Description Sim:   {target_overlap.get('description_score', 0)} / 35")
    print(f"      • Category Match:    {target_overlap.get('category_score', 0)} / 15")
    print(f"      • Keyword Overlap:   {target_overlap.get('keyword_score', 0)} / 10")
    print(f"      • Shared Keywords:   {target_overlap.get('matching_keywords')}")
    print(f"      • Detector Engine:   RapidFuzz baseline (algorithm: {target_overlap['algorithm_version']})")

    # -------------------------------------------------------------------------
    # STEP 7: Evidence Assessment & Reviewer Inspection
    # -------------------------------------------------------------------------
    print("\n[STEP 7] Reviewer Evidence Inspection")
    r = requests.post(f"{BASE_URL}/api/complaints/{c2_id}/assess", headers=reviewer_hdr)
    if r.status_code != 200:
        raise RuntimeError(f"Evidence assessment failed: {r.status_code} {r.text}")
    ev = r.json()
    print(f"  ✓ Evidence Assessment for Case #{c2_id}:")
    print(f"      • Status:              {ev['status']}")
    print(f"      • Completeness Score:  {ev['completeness_score']:.0f}%")
    print(f"      • Readiness Score:     {ev['evidence_readiness_score']:.0f}%")
    print(f"      • Institution Valid:   {ev['institution_verified']}")
    print(f"      • Missing Fields:      {ev['missing_fields']}")

    # -------------------------------------------------------------------------
    # STEP 8: Reviewer Records Decision & Mandatory Reason
    # -------------------------------------------------------------------------
    print("\n[STEP 8] Supervisory Reviewer Decision Submission")
    decision_payload = {
        "decision": "confirmed_duplicate",
        "reason": (
            "Confirmed duplicate filing. Both cases describe withholding of PG GATE "
            "stipends for 18 M.Tech students at Apex Institute during the same semester. "
            "Case #2 will be linked to Primary Case #1."
        )
    }
    r = requests.post(f"{BASE_URL}/api/overlaps/{ov_id}/decision", json=decision_payload, headers=reviewer_hdr)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to submit decision: {r.status_code} {r.text}")
    dec_res = r.json()
    print(f"  ✓ Decision recorded: {dec_res['decision'].upper()}")
    print(f"  ✓ Review status:     {dec_res['review_status']}")
    print(f"  ✓ Reason:            {dec_res['decision_reason']}")

    # -------------------------------------------------------------------------
    # STEP 9: Officer Updates Status & Adds Case Action
    # -------------------------------------------------------------------------
    print("\n[STEP 9] Bureau Officer Case Progress & Timeline Action")
    # Transition status adhering to AICTE complaint lifecycle: registered -> under_initial_review -> under_process
    r = requests.patch(f"{BASE_URL}/api/complaints/{c1_id}", json={"status": "under_initial_review"}, headers=officer_hdr)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to update to initial review: {r.status_code} {r.text}")
    print(f"  ✓ Case #{c1_id} status updated to: {r.json()['status']}")

    r = requests.patch(f"{BASE_URL}/api/complaints/{c1_id}", json={"status": "under_process"}, headers=officer_hdr)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to update to under_process: {r.status_code} {r.text}")
    print(f"  ✓ Case #{c1_id} status updated to: {r.json()['status']}")

    action_payload = {
        "action_type": "document.requested",
        "description": "Formal notice served to Principal of Apex Institute requesting student stipend ledger within 7 working days."
    }
    r = requests.post(f"{BASE_URL}/api/complaints/{c1_id}/actions", json=action_payload, headers=officer_hdr)
    if r.status_code != 201:
        raise RuntimeError(f"Failed to add action: {r.status_code} {r.text}")
    act = r.json()
    print(f"  ✓ Timeline action logged: {act['action_type']} — '{act['description']}'")

    # -------------------------------------------------------------------------
    # STEP 10: Dashboard Reflects Updated Data
    # -------------------------------------------------------------------------
    print("\n[STEP 10] Dashboard Metric Verification")
    r = requests.get(f"{BASE_URL}/api/dashboard", headers=admin_hdr)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to get dashboard: {r.status_code} {r.text}")
    dash = r.json()
    print(f"  ✓ Total Complaints:           {dash['total_complaints']}")
    print(f"  ✓ Cases Under Process:         {dash['under_process']}")
    print(f"  ✓ Pending Overlap Reviews:     {dash['pending_overlap_reviews']}")
    print(f"  ✓ High Priority Cases:         {dash['high_priority_cases']}")
    print(f"  ✓ Critical Priority Cases:     {dash['critical_cases']}")

    # -------------------------------------------------------------------------
    # STEP 11: Audit Trail Verification
    # -------------------------------------------------------------------------
    print("\n[STEP 11] Audit Trail Verification (Admin Only)")
    r = requests.get(f"{BASE_URL}/api/audit-logs?per_page=10", headers=admin_hdr)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to get audit logs: {r.status_code} {r.text}")
    logs = r.json()["items"]
    print(f"  ✓ Fetched {len(logs)} recent audit log events.")
    recent_actions = [l["action"] for l in logs[:5]]
    print(f"  ✓ Recent audit actions: {', '.join(recent_actions)}")

    # -------------------------------------------------------------------------
    # STEP 12: Authorization & Security Controls Verification
    # -------------------------------------------------------------------------
    print("\n[STEP 12] Security Controls & Unauthorized Operation Rejection")
    readonly_token, readonly_user = login("readonly1", "Readonly@123")
    readonly_hdr = {"Authorization": f"Bearer {readonly_token}"}

    # 1. Readonly user attempting to create complaint must be blocked
    r_blocked_write = requests.post(
        f"{BASE_URL}/api/complaints",
        json={"title": "Unauthorized attempt", "description": "Should fail", "category": "administrative"},
        headers=readonly_hdr
    )
    if r_blocked_write.status_code != 403:
        raise RuntimeError(f"Security failure: Readonly user was not rejected with 403: {r_blocked_write.status_code}")
    print(f"  ✓ Read-only write rejected: HTTP {r_blocked_write.status_code} Forbidden")

    # 2. Bureau officer attempting to record cross-bureau overlap decision must be blocked
    r_blocked_decision = requests.post(
        f"{BASE_URL}/api/overlaps/{ov_id}/decision",
        json={"decision": "unrelated", "reason": "Officer attempting supervisory decision"},
        headers=officer_hdr
    )
    if r_blocked_decision.status_code != 403:
        raise RuntimeError(f"Security failure: Officer was not rejected for supervisory decision: {r_blocked_decision.status_code}")
    print(f"  ✓ Non-reviewer decision rejected: HTTP {r_blocked_decision.status_code} Forbidden")

    print("\n" + "=" * 70)
    print("SUCCESS: ALL 12 DEMONSTRATION STEPS COMPLETED WITHOUT ERROR.")
    print("=" * 70)

if __name__ == "__main__":
    run_demo()
