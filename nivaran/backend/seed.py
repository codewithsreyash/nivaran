"""
AICTE OneView — Synthetic Seed Data Script
==========================================
All records in this file are SYNTHETIC DEMONSTRATION DATA.
No real AICTE complaints, real persons, or real institutions are used.
Source label: Synthetic Demonstration Record

Run: python seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from app.database import SessionLocal, engine, Base
from app.models import (
    User, UserRole, Bureau, Institution, InstitutionVerificationStatus,
    Complaint, ComplaintStatus, ComplaintCategory, PriorityLevel,
    CaseAction, OverlapResult, PriorityAssessment, EvidenceAssessment,
    Notification, EscalationEvent, DataSource, DataSourceType
)
from app.auth import hash_password
from app.services.priority_engine import calculate_priority

Base.metadata.create_all(bind=engine)
db = SessionLocal()

NOW = datetime.utcnow()


def ts(days_ago=0, hours_ago=0):
    return NOW - timedelta(days=days_ago, hours=hours_ago)


def future(days=7):
    return NOW + timedelta(days=days)


# ─── Bureaus ──────────────────────────────────────────────────────────────────
print("Seeding bureaus...")
BUREAUS = [
    {"name": "Academic Bureau", "code": "ACAD", "description": "Handles academic and examination grievances."},
    {"name": "Finance & Scholarship Cell", "code": "FIN", "description": "Manages scholarship and financial disputes."},
    {"name": "Compliance & Regulatory Cell", "code": "COMP", "description": "Regulatory and approval-related complaints."},
    {"name": "Student Welfare Bureau", "code": "SWB", "description": "Student safety, welfare and administrative issues."},
    {"name": "Infrastructure Bureau", "code": "INFRA", "description": "Infrastructure, facilities and physical resources."},
]
bureau_objs = {}
for b in BUREAUS:
    existing = db.query(Bureau).filter(Bureau.code == b["code"]).first()
    if not existing:
        obj = Bureau(**b)
        db.add(obj)
        db.flush()
        bureau_objs[b["code"]] = obj
    else:
        bureau_objs[b["code"]] = existing
db.commit()
print(f"  {len(bureau_objs)} bureaus ready.")

# ─── Users ────────────────────────────────────────────────────────────────────
print("Seeding demo users...")
USERS = [
    {
        "username": "admin",
        "email": "admin@aicte-oneview.demo",
        "full_name": "System Administrator",
        "password": "Admin@123",
        "role": UserRole.ADMIN,
        "bureau_code": None,
    },
    {
        "username": "reviewer1",
        "email": "reviewer1@aicte-oneview.demo",
        "full_name": "Priya Sharma",
        "password": "Review@123",
        "role": UserRole.SUPERVISORY_REVIEWER,
        "bureau_code": None,
    },
    {
        "username": "officer_acad",
        "email": "officer.acad@aicte-oneview.demo",
        "full_name": "Rajesh Kumar",
        "password": "Officer@123",
        "role": UserRole.BUREAU_OFFICER,
        "bureau_code": "ACAD",
    },
    {
        "username": "officer_fin",
        "email": "officer.fin@aicte-oneview.demo",
        "full_name": "Meena Patel",
        "password": "Officer@123",
        "role": UserRole.BUREAU_OFFICER,
        "bureau_code": "FIN",
    },
    {
        "username": "officer_comp",
        "email": "officer.comp@aicte-oneview.demo",
        "full_name": "Suresh Nair",
        "password": "Officer@123",
        "role": UserRole.BUREAU_OFFICER,
        "bureau_code": "COMP",
    },
    {
        "username": "readonly1",
        "email": "readonly1@aicte-oneview.demo",
        "full_name": "Ananya Reddy",
        "password": "Readonly@123",
        "role": UserRole.READ_ONLY,
        "bureau_code": None,
    },
]
user_objs = {}
for u_data in USERS:
    existing = db.query(User).filter(User.username == u_data["username"]).first()
    if not existing:
        bureau_id = bureau_objs[u_data["bureau_code"]].id if u_data["bureau_code"] else None
        user = User(
            username=u_data["username"],
            email=u_data["email"],
            full_name=u_data["full_name"],
            hashed_password=hash_password(u_data["password"]),
            role=u_data["role"],
            bureau_id=bureau_id,
        )
        db.add(user)
        db.flush()
        user_objs[u_data["username"]] = user
    else:
        user_objs[u_data["username"]] = existing
db.commit()
print(f"  {len(user_objs)} users ready.")

# ─── Institutions ─────────────────────────────────────────────────────────────
print("Seeding synthetic institutions...")
INSTITUTIONS = [
    {"id": "INST-MH-001", "name": "Vidyasagar Institute of Technology, Pune", "state": "Maharashtra",
     "district": "Pune", "region": "Western", "type": "Engineering College",
     "status": InstitutionVerificationStatus.VERIFIED},
    {"id": "INST-MH-002", "name": "Pratibha College of Engineering, Nagpur", "state": "Maharashtra",
     "district": "Nagpur", "region": "Western", "type": "Engineering College",
     "status": InstitutionVerificationStatus.UNVERIFIED},
    {"id": "INST-KA-001", "name": "Raghavendra Institute of Technology, Bengaluru", "state": "Karnataka",
     "district": "Bengaluru Urban", "region": "Southern", "type": "Engineering College",
     "status": InstitutionVerificationStatus.VERIFIED},
    {"id": "INST-TN-001", "name": "Kavitha Engineering College, Chennai", "state": "Tamil Nadu",
     "district": "Chennai", "region": "Southern", "type": "Engineering College",
     "status": InstitutionVerificationStatus.PENDING},
    {"id": "INST-DL-001", "name": "Capital Institute of Management, Delhi", "state": "Delhi",
     "district": "New Delhi", "region": "Northern", "type": "Management Institute",
     "status": InstitutionVerificationStatus.VERIFIED},
    {"id": "INST-UP-001", "name": "Awadh Technical University, Lucknow", "state": "Uttar Pradesh",
     "district": "Lucknow", "region": "Northern", "type": "University",
     "status": InstitutionVerificationStatus.UNVERIFIED},
    {"id": "INST-GJ-001", "name": "Saurashtra Engineering College, Rajkot", "state": "Gujarat",
     "district": "Rajkot", "region": "Western", "type": "Engineering College",
     "status": InstitutionVerificationStatus.VERIFIED},
    {"id": "INST-RJ-001", "name": "Rajputana Institute of Technology, Jaipur", "state": "Rajasthan",
     "district": "Jaipur", "region": "Northern", "type": "Engineering College",
     "status": InstitutionVerificationStatus.PENDING},
    {"id": "INST-WB-001", "name": "Hooghly Technical College, Kolkata", "state": "West Bengal",
     "district": "Hooghly", "region": "Eastern", "type": "Engineering College",
     "status": InstitutionVerificationStatus.VERIFIED},
    {"id": "INST-TS-001", "name": "Deccan Institute of Advanced Studies, Hyderabad", "state": "Telangana",
     "district": "Hyderabad", "region": "Southern", "type": "Engineering College",
     "status": InstitutionVerificationStatus.VERIFIED},
    {"id": "INST-MP-001", "name": "Central India College of Engineering, Bhopal", "state": "Madhya Pradesh",
     "district": "Bhopal", "region": "Central", "type": "Engineering College",
     "status": InstitutionVerificationStatus.UNVERIFIED},
    {"id": "INST-PB-001", "name": "Punjab Technical Institute, Amritsar", "state": "Punjab",
     "district": "Amritsar", "region": "Northern", "type": "Engineering College",
     "status": InstitutionVerificationStatus.VERIFIED},
]
inst_objs = {}
for i_data in INSTITUTIONS:
    existing = db.query(Institution).filter(Institution.institution_id == i_data["id"]).first()
    if not existing:
        inst = Institution(
            institution_id=i_data["id"],
            name=i_data["name"],
            state=i_data["state"],
            district=i_data["district"],
            region=i_data["region"],
            institution_type=i_data["type"],
            verification_status=i_data["status"],
            source_label="Synthetic Demonstration Record",
            is_active=True,
        )
        db.add(inst)
        db.flush()
        inst_objs[i_data["id"]] = inst
    else:
        inst_objs[i_data["id"]] = existing
db.commit()
print(f"  {len(inst_objs)} institutions ready.")

# ─── Complaints ───────────────────────────────────────────────────────────────
print("Seeding synthetic complaints...")

admin = user_objs["admin"]
reviewer = user_objs["reviewer1"]
off_acad = user_objs["officer_acad"]
off_fin = user_objs["officer_fin"]
off_comp = user_objs["officer_comp"]

bureau_acad = bureau_objs["ACAD"]
bureau_fin = bureau_objs["FIN"]
bureau_comp = bureau_objs["COMP"]
bureau_swb = bureau_objs["SWB"]
bureau_infra = bureau_objs["INFRA"]

inst_mh1 = inst_objs["INST-MH-001"]
inst_ka1 = inst_objs["INST-KA-001"]
inst_tn1 = inst_objs["INST-TN-001"]
inst_dl1 = inst_objs["INST-DL-001"]
inst_ts1 = inst_objs["INST-TS-001"]
inst_up1 = inst_objs["INST-UP-001"]
inst_gj1 = inst_objs["INST-GJ-001"]

COMPLAINTS_DATA = [
    # ── DEMO SCENARIO: Scholarship overlap chain ──
    {
        "complaint_id": "AICTE-2026-10-SC001",
        "title": "State scholarship funds not disbursed for academic year 2025-26",
        "description": (
            "Students of the B.Tech program have not received state scholarship payments "
            "for the academic year 2025-26 despite submitting all required documents through "
            "the designated portal. The institution has not acknowledged the missing disbursement "
            "and has threatened to withhold examination hall tickets."
        ),
        "category": ComplaintCategory.SCHOLARSHIP_FINANCIAL,
        "institution_id": inst_mh1.id,
        "institution_name_snapshot": inst_mh1.name,
        "bureau_id": bureau_fin.id,
        "assigned_officer_id": off_fin.id,
        "status": ComplaintStatus.UNDER_PROCESS,
        "registration_date": ts(30),
        "incident_date": ts(45),
        "target_disposal_date": future(-3),  # overdue
        "last_action_date": ts(10),
        "next_required_action": "Contact state scholarship portal and request status update.",
        "data_source_label": "Synthetic Demonstration Record",
    },
    {
        "complaint_id": "AICTE-2026-10-SC002",
        "title": "Scholarship amount withheld — B.Tech students, AY 2025-26",
        "description": (
            "Multiple B.Tech students report that scholarship payments due for 2025-26 have "
            "not been credited. Institution claims the delay is due to a verification backlog "
            "at the scholarship office. Students are unable to pay their semester fees."
        ),
        "category": ComplaintCategory.SCHOLARSHIP_FINANCIAL,
        "institution_id": inst_mh1.id,
        "institution_name_snapshot": inst_mh1.name,
        "bureau_id": bureau_fin.id,
        "assigned_officer_id": off_fin.id,
        "status": ComplaintStatus.UNDER_INITIAL_REVIEW,
        "registration_date": ts(25),
        "incident_date": ts(40),
        "target_disposal_date": future(5),
        "last_action_date": ts(5),
        "next_required_action": "Run overlap detection to check relation with SC001.",
        "data_source_label": "Synthetic Demonstration Record",
    },
    {
        "complaint_id": "AICTE-2026-10-SC003",
        "title": "Infrastructure deficiency — laboratory equipment missing",
        "description": (
            "The computer science laboratory does not have functional equipment as mandated "
            "by AICTE norms. Several machines are out of service and replacement requests "
            "made six months ago have not been actioned."
        ),
        "category": ComplaintCategory.INFRASTRUCTURE_FACILITIES,
        "institution_id": inst_mh1.id,
        "institution_name_snapshot": inst_mh1.name,
        "bureau_id": bureau_infra.id,
        "status": ComplaintStatus.REGISTERED,
        "registration_date": ts(12),
        "incident_date": ts(180),
        "target_disposal_date": future(14),
        "last_action_date": ts(12),
        "data_source_label": "Synthetic Demonstration Record",
    },
    # ── Academic complaints ──
    {
        "complaint_id": "AICTE-2026-10-AC001",
        "title": "Examination results withheld without justification",
        "description": (
            "Final semester examination results for 47 students have been withheld by the "
            "institution. No official communication has been issued and students are unable "
            "to apply for employment or higher education."
        ),
        "category": ComplaintCategory.ACADEMIC_EXAMINATION,
        "institution_id": inst_ka1.id,
        "institution_name_snapshot": inst_ka1.name,
        "bureau_id": bureau_acad.id,
        "assigned_officer_id": off_acad.id,
        "status": ComplaintStatus.ESCALATED,
        "registration_date": ts(60),
        "incident_date": ts(75),
        "target_disposal_date": future(-15),  # overdue
        "last_action_date": ts(20),
        "data_source_label": "Synthetic Demonstration Record",
    },
    {
        "complaint_id": "AICTE-2026-10-AC002",
        "title": "Irregular examination schedule causes academic harm",
        "description": (
            "The institution changed the semester examination schedule with less than 48 hours "
            "notice. Several students missed exams due to travel constraints. "
            "No make-up examination was offered."
        ),
        "category": ComplaintCategory.ACADEMIC_EXAMINATION,
        "institution_id": inst_tn1.id,
        "institution_name_snapshot": inst_tn1.name,
        "bureau_id": bureau_acad.id,
        "status": ComplaintStatus.UNDER_PROCESS,
        "registration_date": ts(18),
        "incident_date": ts(22),
        "target_disposal_date": future(3),
        "last_action_date": ts(3),
        "data_source_label": "Synthetic Demonstration Record",
    },
    # ── Safety / Welfare ──
    {
        "complaint_id": "AICTE-2026-10-SW001",
        "title": "Alleged harassment by faculty member — urgent review required",
        "description": (
            "A student has formally reported verbal harassment by a faculty member. "
            "The institution's internal committee has not convened despite a written request "
            "submitted 21 days ago. The complainant requests immediate intervention."
        ),
        "category": ComplaintCategory.STUDENT_SAFETY_WELFARE,
        "institution_id": inst_dl1.id,
        "institution_name_snapshot": inst_dl1.name,
        "bureau_id": bureau_swb.id,
        "status": ComplaintStatus.ESCALATED,
        "registration_date": ts(21),
        "incident_date": ts(35),
        "target_disposal_date": future(1),
        "last_action_date": ts(2),
        "next_required_action": "Confirm internal committee status with institution.",
        "data_source_label": "Synthetic Demonstration Record",
    },
    # ── Regulatory / Compliance ──
    {
        "complaint_id": "AICTE-2026-10-RC001",
        "title": "Institution operating unapproved programme — Computer Applications",
        "description": (
            "The institution is offering a three-year Computer Applications programme "
            "without obtaining AICTE approval. Students enrolled in this programme risk "
            "receiving degrees with no regulatory recognition."
        ),
        "category": ComplaintCategory.REGULATORY_COMPLIANCE,
        "institution_id": inst_up1.id,
        "institution_name_snapshot": inst_up1.name,
        "bureau_id": bureau_comp.id,
        "assigned_officer_id": off_comp.id,
        "status": ComplaintStatus.UNDER_PROCESS,
        "registration_date": ts(45),
        "incident_date": ts(90),
        "target_disposal_date": future(-10),  # overdue
        "last_action_date": ts(8),
        "data_source_label": "Synthetic Demonstration Record",
    },
    {
        "complaint_id": "AICTE-2026-10-RC002",
        "title": "Non-compliant student-to-faculty ratio — Engineering dept.",
        "description": (
            "The engineering department's student-to-faculty ratio significantly exceeds "
            "the permissible limit set by AICTE norms. The institution has not responded "
            "to requests for a corrective action plan submitted in the previous academic year."
        ),
        "category": ComplaintCategory.REGULATORY_COMPLIANCE,
        "institution_id": inst_gj1.id,
        "institution_name_snapshot": inst_gj1.name,
        "bureau_id": bureau_comp.id,
        "assigned_officer_id": off_comp.id,
        "status": ComplaintStatus.AWAITING_INFORMATION,
        "registration_date": ts(55),
        "target_disposal_date": future(7),
        "last_action_date": ts(15),
        "data_source_label": "Synthetic Demonstration Record",
    },
    # ── Faculty related ──
    {
        "complaint_id": "AICTE-2026-10-FA001",
        "title": "Faculty qualifications misrepresented in AICTE submission",
        "description": (
            "Documents submitted to AICTE during the last renewal inspection listed faculty "
            "members with qualifications they do not hold. Affected students report that "
            "classes are being conducted by unqualified temporary staff."
        ),
        "category": ComplaintCategory.FACULTY_RELATED,
        "institution_id": inst_ts1.id,
        "institution_name_snapshot": inst_ts1.name,
        "bureau_id": bureau_comp.id,
        "status": ComplaintStatus.UNDER_INITIAL_REVIEW,
        "registration_date": ts(10),
        "target_disposal_date": future(20),
        "last_action_date": ts(10),
        "data_source_label": "Synthetic Demonstration Record",
    },
    # ── Administrative ──
    {
        "complaint_id": "AICTE-2026-10-AD001",
        "title": "Refund not processed after course withdrawal",
        "description": (
            "A student withdrew from the programme within the permissible period and submitted "
            "a refund request with all supporting documents. The institution has not processed "
            "the refund after 60 days."
        ),
        "category": ComplaintCategory.ADMINISTRATIVE,
        "institution_id": inst_ka1.id,
        "institution_name_snapshot": inst_ka1.name,
        "bureau_id": bureau_swb.id,
        "status": ComplaintStatus.DISPOSED,
        "registration_date": ts(80),
        "incident_date": ts(100),
        "target_disposal_date": future(-20),
        "last_action_date": ts(5),
        "data_source_label": "Synthetic Demonstration Record",
    },
    # ── Approval ──
    {
        "complaint_id": "AICTE-2026-10-AP001",
        "title": "Approved intake exceeded — civil engineering programme",
        "description": (
            "The institution has enrolled 185 students against an approved intake of 120 "
            "in the Civil Engineering programme. Excess admissions are not disclosed to "
            "students at the time of enrolment."
        ),
        "category": ComplaintCategory.APPROVAL_RELATED,
        "institution_id": inst_up1.id,
        "institution_name_snapshot": inst_up1.name,
        "bureau_id": bureau_comp.id,
        "status": ComplaintStatus.REGISTERED,
        "registration_date": ts(3),
        "target_disposal_date": future(28),
        "data_source_label": "Synthetic Demonstration Record",
    },
    {
        "complaint_id": "AICTE-2026-10-SC004",
        "title": "Fee collected beyond approved structure — Management programme",
        "description": (
            "The institution is collecting fees significantly above the approved fee structure "
            "for its MBA programme. Students are being charged for facilities that do not exist "
            "on campus."
        ),
        "category": ComplaintCategory.SCHOLARSHIP_FINANCIAL,
        "institution_id": inst_dl1.id,
        "institution_name_snapshot": inst_dl1.name,
        "bureau_id": bureau_fin.id,
        "assigned_officer_id": off_fin.id,
        "status": ComplaintStatus.UNDER_PROCESS,
        "registration_date": ts(14),
        "target_disposal_date": future(7),
        "last_action_date": ts(4),
        "data_source_label": "Synthetic Demonstration Record",
    },
    {
        "complaint_id": "AICTE-2026-10-IN001",
        "title": "Hostel building safety certification lapsed",
        "description": (
            "The fire safety certification for the student hostel building expired 8 months "
            "ago. No renewal has been obtained. Students residing in the hostel have not "
            "been informed of this lapse."
        ),
        "category": ComplaintCategory.STUDENT_SAFETY_WELFARE,
        "institution_id": inst_gj1.id,
        "institution_name_snapshot": inst_gj1.name,
        "bureau_id": bureau_swb.id,
        "status": ComplaintStatus.ESCALATED,
        "registration_date": ts(7),
        "target_disposal_date": future(0),  # due today
        "last_action_date": ts(1),
        "data_source_label": "Synthetic Demonstration Record",
    },
    {
        "complaint_id": "AICTE-2026-10-AD002",
        "title": "Transfer certificate not issued after course completion",
        "description": (
            "A student who completed the programme in April 2026 has not been issued a "
            "Transfer Certificate despite multiple requests. The institution is demanding "
            "additional undocumented payment."
        ),
        "category": ComplaintCategory.ADMINISTRATIVE,
        "institution_id": inst_tn1.id,
        "institution_name_snapshot": inst_tn1.name,
        "bureau_id": bureau_acad.id,
        "status": ComplaintStatus.AWAITING_INFORMATION,
        "registration_date": ts(20),
        "target_disposal_date": future(10),
        "last_action_date": ts(7),
        "is_anonymous": False,
        "data_source_label": "Synthetic Demonstration Record",
    },
    {
        "complaint_id": "AICTE-2026-10-SC005",
        "title": "Scholarship portal rejection — institution code mismatch",
        "description": (
            "Students' scholarship applications are being rejected by the state portal "
            "because the institution's AICTE approval code does not match the record "
            "in the state database. The institution has not resolved this discrepancy."
        ),
        "category": ComplaintCategory.SCHOLARSHIP_FINANCIAL,
        "institution_id": inst_mh1.id,
        "institution_name_snapshot": inst_mh1.name,
        "bureau_id": bureau_fin.id,
        "status": ComplaintStatus.REGISTERED,
        "registration_date": ts(2),
        "target_disposal_date": future(21),
        "data_source_label": "Synthetic Demonstration Record",
    },
]

complaint_objs = {}
for c_data in COMPLAINTS_DATA:
    existing = db.query(Complaint).filter(
        Complaint.complaint_id == c_data["complaint_id"]
    ).first()
    if not existing:
        c = Complaint(**{k: v for k, v in c_data.items()})
        db.add(c)
        db.flush()
        # Calculate priority
        result = calculate_priority(c)
        c.calculated_priority_score = result["score"]
        c.calculated_priority_level = result["priority_level"]
        c.priority_explanation = result["explanation"]
        c.priority_calculated_at = result["calculated_at"]
        pa = PriorityAssessment(
            complaint_id=c.id,
            **{k: v for k, v in result.items()
               if k in ["score", "priority_level", "urgency_contribution",
                        "impact_contribution", "deadline_contribution",
                        "ageing_contribution", "escalation_contribution",
                        "transfer_contribution", "explanation", "missing_data_flags",
                        "calculation_version", "calculated_at"]},
        )
        db.add(pa)
        # Initial action
        action = CaseAction(
            complaint_id=c.id,
            actor_id=admin.id,
            action_type="complaint.registered",
            description="Complaint registered via demonstration seed data.",
            new_status=c.status.value,
        )
        db.add(action)
        complaint_objs[c_data["complaint_id"]] = c
    else:
        complaint_objs[c_data["complaint_id"]] = existing
db.commit()
print(f"  {len(complaint_objs)} complaints ready.")

# ─── Additional Actions ────────────────────────────────────────────────────────
print("Seeding case actions...")
c_sc001 = complaint_objs["AICTE-2026-10-SC001"]
c_sc002 = complaint_objs["AICTE-2026-10-SC002"]
c_ac001 = complaint_objs["AICTE-2026-10-AC001"]
c_sw001 = complaint_objs["AICTE-2026-10-SW001"]
c_rc001 = complaint_objs["AICTE-2026-10-RC001"]

extra_actions = [
    CaseAction(complaint_id=c_sc001.id, actor_id=off_fin.id,
               action_type="document.requested",
               description="Requested scholarship disbursement acknowledgement from institution.",
               created_at=ts(20)),
    CaseAction(complaint_id=c_sc001.id, actor_id=off_fin.id,
               action_type="follow_up.sent",
               description="Follow-up email sent to state scholarship portal.",
               created_at=ts(12)),
    CaseAction(complaint_id=c_ac001.id, actor_id=off_acad.id,
               action_type="status.changed",
               description="Escalated due to no response from institution after 45 days.",
               old_status="under_process", new_status="escalated",
               created_at=ts(25)),
    CaseAction(complaint_id=c_sw001.id, actor_id=reviewer.id,
               action_type="escalation.initiated",
               description="Escalated to Supervisory Reviewer for urgent attention.",
               created_at=ts(5)),
    CaseAction(complaint_id=c_rc001.id, actor_id=off_comp.id,
               action_type="document.received",
               description="Received inspection report from regional AICTE office.",
               created_at=ts(15)),
]
for action in extra_actions:
    db.add(action)
db.commit()

# ─── Overlap Results ──────────────────────────────────────────────────────────
print("Seeding overlap results (SC001–SC002 similarity)...")
existing_overlap = db.query(OverlapResult).filter(
    OverlapResult.primary_complaint_id == c_sc001.id,
    OverlapResult.candidate_complaint_id == c_sc002.id,
).first()
if not existing_overlap:
    overlap = OverlapResult(
        primary_complaint_id=c_sc001.id,
        candidate_complaint_id=c_sc002.id,
        similarity_score=82.5,
        institution_score=30.0,
        description_score=28.5,
        category_score=15.0,
        date_score=6.0,
        keyword_score=3.0,
        matching_keywords=["scholarship", "students", "disbursement", "2025-26", "payment", "bttech"],
        conflicting_info=None,
        missing_data_notes=None,
        algorithm_version="rules-v1",
        review_status="pending",
    )
    db.add(overlap)
    db.commit()

# ─── Evidence Assessments ────────────────────────────────────────────────────
print("Seeding evidence assessments...")
ev_cases = [c_sc001, c_sc002, c_ac001, c_sw001]
for c in ev_cases:
    existing_ev = db.query(EvidenceAssessment).filter(
        EvidenceAssessment.complaint_id == c.id
    ).first()
    if not existing_ev:
        completeness = 85.0 if c.institution_id else 55.0
        ea = EvidenceAssessment(
            complaint_id=c.id,
            completeness_score=completeness,
            evidence_readiness_score=completeness * 0.7,
            institution_verified=c.institution is not None,
            date_consistency_ok=True,
            document_count=1 if completeness > 70 else 0,
            missing_fields=["incident_date"] if completeness < 80 else [],
            status="Evidence Under Review" if completeness > 70 else "Information Incomplete",
            assessed_by_id=admin.id,
        )
        db.add(ea)
db.commit()

# ─── Escalation Events ────────────────────────────────────────────────────────
print("Seeding escalation events...")
for c, reason in [
    (c_ac001, "No response from institution after 45 days."),
    (c_sw001, "Welfare concern requires immediate supervisory review."),
]:
    existing_esc = db.query(EscalationEvent).filter(
        EscalationEvent.complaint_id == c.id
    ).first()
    if not existing_esc:
        esc = EscalationEvent(
            complaint_id=c.id,
            trigger_reason=reason,
            escalated_to="Supervisory Reviewer",
            initiated_by_id=admin.id,
        )
        db.add(esc)
db.commit()

# ─── Notifications ────────────────────────────────────────────────────────────
print("Seeding notifications...")
NOTIFS = [
    {
        "complaint_id": c_sc001.id,
        "title": "Case Overdue: AICTE-2026-10-SC001",
        "message": "Scholarship complaint SC001 is overdue. Immediate action required.",
        "notification_type": "overdue",
        "trigger_key": f"overdue-{c_sc001.id}",
    },
    {
        "complaint_id": c_ac001.id,
        "title": "Case Overdue: AICTE-2026-10-AC001",
        "message": "Escalated academic complaint AC001 is overdue by 15 days.",
        "notification_type": "overdue",
        "trigger_key": f"overdue-{c_ac001.id}",
    },
    {
        "complaint_id": c_sc001.id,
        "title": "Potential Overlap Detected",
        "message": "Cases SC001 and SC002 show 82.5% similarity. Overlap review required.",
        "notification_type": "overlap",
        "trigger_key": f"overlap-{c_sc001.id}-{c_sc002.id}",
    },
    {
        "complaint_id": c_sw001.id,
        "title": "Welfare Complaint Requires Urgent Attention",
        "message": "Student welfare complaint SW001 deadline is within 24 hours.",
        "notification_type": "deadline",
        "trigger_key": f"deadline-{c_sw001.id}",
    },
]
for n_data in NOTIFS:
    existing_n = db.query(Notification).filter(
        Notification.trigger_key == n_data["trigger_key"]
    ).first()
    if not existing_n:
        notif = Notification(**n_data)
        db.add(notif)
db.commit()

# ─── Data Source registry ─────────────────────────────────────────────────────
print("Seeding data source registry...")
existing_ds = db.query(DataSource).filter(DataSource.name == "Synthetic Seed Dataset").first()
if not existing_ds:
    ds = DataSource(
        name="Synthetic Seed Dataset",
        source_type=DataSourceType.SYNTHETIC_DEMONSTRATION,
        description=(
            "All complaint and institution records in this dataset are fictional "
            "and created solely for demonstration purposes. "
            "No real AICTE complaint data is included."
        ),
        licence="Internal demonstration only — not for external use.",
        has_sensitive_data=False,
        is_approved=True,
    )
    db.add(ds)
    db.commit()

db.close()

print("\n" + "=" * 60)
print("Seed complete.")
print("=" * 60)
print("\nDemo accounts:")
print("  admin        / Admin@123    (System Administrator)")
print("  reviewer1    / Review@123   (Supervisory Reviewer)")
print("  officer_acad / Officer@123  (Bureau Officer — Academic)")
print("  officer_fin  / Officer@123  (Bureau Officer — Finance)")
print("  officer_comp / Officer@123  (Bureau Officer — Compliance)")
print("  readonly1    / Readonly@123 (Read-Only Official)")
print("\nAll data is labelled: Synthetic Demonstration Record")
print("=" * 60)
