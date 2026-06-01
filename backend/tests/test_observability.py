def test_metrics_endpoint_exposes_prometheus_payload(client):
    client.get("/api/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    body = response.text
    assert "python_info" in body
    assert "app_process_resident_memory_bytes" in body
    assert "http_requests_total" in body
    assert "/api/health" in body
