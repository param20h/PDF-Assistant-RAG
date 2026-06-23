import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app  # Adjust this import based on where the FastAPI app instance lives

# Mark all tests in this module to use asyncio
pytestmark = pytest.mark.anyio


async def test_health_check_route():
    # Use ASGITransport to test the FastAPI app directly without running a server
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/health")  # Replace with a real route from the app

    assert response.status_code == 200
    # Add more assertions based on expected JSON response


async def test_health_check_db_healthy_chroma_healthy(monkeypatch):
    # Case 1: DB healthy, Chroma healthy -> status = healthy
    # Both are healthy by default in test env (get_db yields test db, get_chroma_client works)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["db"] == "up"
    assert data["chroma"] == "up"


async def test_health_check_db_healthy_chroma_unhealthy(monkeypatch):
    # Case 2: DB healthy, Chroma unhealthy -> status = degraded
    def mock_get_chroma_client_down():
        raise Exception("Chroma connection refused")

    monkeypatch.setattr("app.main.get_chroma_client", mock_get_chroma_client_down)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["db"] == "up"
    assert data["chroma"] == "down"


async def test_health_check_db_unhealthy_chroma_healthy(monkeypatch):
    # Case 3: DB unhealthy, Chroma healthy -> status = degraded
    from sqlalchemy.exc import SQLAlchemyError

    def mock_get_db_down():
        raise SQLAlchemyError("DB Connection refused")
        yield

    monkeypatch.setattr("app.main.get_db", mock_get_db_down)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["db"] == "down"
    assert data["chroma"] == "up"


async def test_health_check_db_unhealthy_chroma_unhealthy(monkeypatch):
    # Case 4: DB unhealthy, Chroma unhealthy -> status = unhealthy
    from sqlalchemy.exc import SQLAlchemyError

    def mock_get_db_down():
        raise SQLAlchemyError("DB Connection refused")
        yield

    def mock_get_chroma_client_down():
        raise Exception("Chroma connection refused")

    monkeypatch.setattr("app.main.get_db", mock_get_db_down)
    monkeypatch.setattr("app.main.get_chroma_client", mock_get_chroma_client_down)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["db"] == "down"
    assert data["chroma"] == "down"

