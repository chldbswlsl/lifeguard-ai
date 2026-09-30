def test_signup_login_me(client, guardian):
    res = client.get("/auth/me", headers=guardian)
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "guardian@test.com"
    assert body["role"] == "guardian"
    assert "password_hash" not in body


def test_duplicate_email_rejected(client, guardian):
    res = client.post("/auth/signup", json={"email": "GUARDIAN@test.com", "password": "password123", "name": "x"})
    assert res.status_code == 409


def test_wrong_password(client, guardian):
    res = client.post("/auth/login", data={"username": "guardian@test.com", "password": "wrongpass"})
    assert res.status_code == 401


def test_short_password_rejected(client):
    res = client.post("/auth/signup", json={"email": "a@test.com", "password": "short", "name": "x"})
    assert res.status_code == 422


def test_requires_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_update_me(client, guardian):
    res = client.patch("/auth/me", json={"phone": "010-1234-5678"}, headers=guardian)
    assert res.status_code == 200
    assert res.json()["phone"] == "010-1234-5678"
    assert res.json()["name"] == "보호자"


def test_change_password(client, guardian):
    bad = client.post("/auth/me/password", json={"current_password": "wrong", "new_password": "newpass123"}, headers=guardian)
    assert bad.status_code == 400
    ok = client.post("/auth/me/password", json={"current_password": "password123", "new_password": "newpass123"}, headers=guardian)
    assert ok.status_code == 204
    assert client.post("/auth/login", data={"username": "guardian@test.com", "password": "newpass123"}).status_code == 200
