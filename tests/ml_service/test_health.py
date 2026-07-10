def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_reports_model_and_config(client):
    r = client.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["model_present"] is True          # model.pkl exists from Plan 1
    assert "supabase_configured" in body
