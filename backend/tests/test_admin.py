from app.auth import create_access_token, hash_password
from app.metrics import record_query_response_time
from app.models import Document, User


def test_admin_stats_requires_admin(client, auth_headers):
    response = client.get("/api/v1/admin/stats", headers=auth_headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_stats_returns_aggregate_metrics(client, db_session):
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=hash_password("password123"),
        is_admin=True,
    )
    regular = User(
        username="regular",
        email="regular@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add_all([admin, regular])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(regular)

    db_session.add_all(
        [
            Document(
                user_id=regular.id,
                filename="first.pdf",
                original_name="first.pdf",
                file_size=100,
                status="ready",
            ),
            Document(
                user_id=regular.id,
                filename="notes.txt",
                original_name="notes.txt",
                file_size=50,
                status="ready",
            ),
        ]
    )
    db_session.commit()

    record_query_response_time(0.25)

    token = create_access_token(admin.id)
    response = client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_users"] == 2
    assert payload["total_pdfs_uploaded"] == 1
    assert payload["average_query_response_time_ms"] > 0
    assert payload["query_count"] >= 1
    assert payload["disk_space_usage"]["total_bytes"] > 0
    assert payload["disk_space_usage"]["usage_percent"] >= 0
