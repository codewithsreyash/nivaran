import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.main import app
from app.database import Base, get_db
from app.models import (
    User, UserRole, Bureau, Institution, InstitutionVerificationStatus,
    Complaint, ComplaintStatus, ComplaintCategory, PriorityLevel
)
from app.auth import hash_password

# Use a separate SQLite database for testing
TEST_DATABASE_URL = "sqlite:///./test_oneview.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # Create bureaus
    acad_bureau = Bureau(id=1, name="Academic Bureau", code="ACAD", description="Academic complaints")
    fin_bureau = Bureau(id=2, name="Finance Bureau", code="FIN", description="Financial complaints")
    comp_bureau = Bureau(id=3, name="Compliance Bureau", code="COMP", description="Compliance complaints")
    db.add_all([acad_bureau, fin_bureau, comp_bureau])

    # Create users
    admin = User(
        id=1, username="admin", email="admin@aicte.gov.in.demo",
        full_name="Dr. Administrator", role=UserRole.ADMIN,
        hashed_password=hash_password("Admin@123"), is_active=True
    )
    officer = User(
        id=2, username="officer_acad", email="officer.acad@aicte.gov.in.demo",
        full_name="Rajesh Kumar", role=UserRole.BUREAU_OFFICER,
        bureau_id=1, hashed_password=hash_password("Officer@123"), is_active=True
    )
    reviewer = User(
        id=3, username="reviewer1", email="reviewer@aicte.gov.in.demo",
        full_name="Sunita Sharma", role=UserRole.SUPERVISORY_REVIEWER,
        hashed_password=hash_password("Review@123"), is_active=True
    )
    readonly = User(
        id=4, username="readonly1", email="readonly@aicte.gov.in.demo",
        full_name="Auditor User", role=UserRole.READ_ONLY,
        hashed_password=hash_password("Readonly@123"), is_active=True
    )
    db.add_all([admin, officer, reviewer, readonly])

    # Create sample institution
    inst = Institution(
        id=1, institution_id="INST-001", name="Apex Engineering College",
        state="Maharashtra", district="Pune", verification_status=InstitutionVerificationStatus.VERIFIED
    )
    db.add(inst)

    # Create sample complaint
    now = datetime.utcnow()
    comp = Complaint(
        id=1,
        complaint_id="AICTE-2026-03-TEST01",
        title="Delay in Scholarship Disbursal for SC/ST Students",
        description="Students have not received approved scholarships for 6 months despite verified documents.",
        category=ComplaintCategory.SCHOLARSHIP_FINANCIAL,
        institution_id=1,
        institution_name_snapshot="Apex Engineering College",
        bureau_id=2,
        assigned_officer_id=2,
        status=ComplaintStatus.UNDER_PROCESS,
        registration_date=now - timedelta(days=10),
        incident_date=now - timedelta(days=20),
        target_disposal_date=now + timedelta(days=5),
        last_action_date=now - timedelta(days=2),
        calculated_priority_score=68.5,
        calculated_priority_level=PriorityLevel.HIGH,
        assigned_priority_level=PriorityLevel.HIGH,
        priority_explanation="High impact on student financial welfare."
    )
    db.add(comp)

    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client):
    res = client.post("/api/auth/login", data={"username": "admin", "password": "Admin@123"})
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
def officer_token(client):
    res = client.post("/api/auth/login", data={"username": "officer_acad", "password": "Officer@123"})
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
def readonly_token(client):
    res = client.post("/api/auth/login", data={"username": "readonly1", "password": "Readonly@123"})
    assert res.status_code == 200
    return res.json()["access_token"]
