def test_login_success(client):
    res = client.post("/api/auth/login", data={"username": "admin", "password": "Admin@123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "admin"


def test_login_wrong_password(client):
    res = client.post("/api/auth/login", data={"username": "admin", "password": "WrongPassword"})
    assert res.status_code == 401
    assert "Incorrect username or password" in res.json()["detail"]


def test_login_unknown_user(client):
    res = client.post("/api/auth/login", data={"username": "nonexistent", "password": "Password@123"})
    assert res.status_code == 401


def test_get_me_authenticated(client, admin_token):
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "admin"
    assert data["email"] == "admin@aicte.gov.in.demo"


def test_get_me_unauthenticated(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_logout(client, admin_token):
    res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert res.json()["detail"] == "Logged out successfully"
