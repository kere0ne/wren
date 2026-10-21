def test_register_login_me(client):
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "hunter2secret"})
    assert r.status_code == 200
    token = r.json()["token"]

    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "hunter2secret"})
    assert r.status_code == 409

    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "wrong-password"})
    assert r.status_code == 401

    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "hunter2secret"})
    assert r.status_code == 200

    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"

    r = client.get("/api/auth/me")
    assert r.status_code == 401
