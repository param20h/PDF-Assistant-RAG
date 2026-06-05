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
