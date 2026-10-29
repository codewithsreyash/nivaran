def test_list_institutions(client, admin_token):
    res = client.get("/api/institutions", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert data["items"][0]["name"] == "Apex Engineering College"


def test_get_institution_by_id(client, admin_token):
    res = client.get("/api/institutions/1", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == 1
    assert data["institution_id"] == "INST-001"
    assert data["state"] == "Maharashtra"


def test_dashboard_stats(client, admin_token):
    res = client.get("/api/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "total_complaints" in data
    assert "critical_cases" in data
    assert "pending_review" in data or "disposed_complaints" in data
    assert data["total_complaints"] >= 1


def test_bureaus_list(client, admin_token):
    res = client.get("/api/bureaus", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    bureaus = res.json()
    assert isinstance(bureaus, list)
    assert len(bureaus) >= 3
    codes = [b["code"] for b in bureaus]
    assert "ACAD" in codes
    assert "FIN" in codes


def test_priority_queue(client, admin_token):
    res = client.get("/api/priority-queue", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data


def test_audit_logs(client, admin_token):
    res = client.get("/api/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


def test_deadlines(client, admin_token):
    res = client.get("/api/deadlines", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, dict)
