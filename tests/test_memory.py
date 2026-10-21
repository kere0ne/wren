def test_memory_crud(client, auth):
    h = auth()
    r = client.post("/api/memory", json={"content": "likes dark themes", "kind": "preference"}, headers=h)
    assert r.status_code == 200
    fact_id = r.json()["id"]

    r = client.get("/api/memory", headers=h)
    assert any(f["id"] == fact_id for f in r.json())

    r = client.delete(f"/api/memory/{fact_id}", headers=h)
    assert r.json()["ok"] is True

    r = client.get("/api/memory", headers=h)
    assert r.json() == []
