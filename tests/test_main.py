"""
LegalAI Test Suite
"""
import pytest
import asyncio
import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_legalai.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-purposes-32chars"
os.environ["ADMIN_PASSWORD"] = "Admin@123456"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_EMAIL"] = "admin@test.com"

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def client():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✓ Health check passed")


@pytest.mark.asyncio
async def test_home_page(client):
    response = await client.get("/")
    assert response.status_code == 200
    print("✓ Home page loads")


@pytest.mark.asyncio
async def test_register(client):
    response = await client.post("/api/auth/register", json={
        "username": "testuser123",
        "email": "testuser123@test.com",
        "password": "TestPass@123",
        "full_name": "Test User",
    })
    # Either 200 (new) or 400 (already exists)
    assert response.status_code in [200, 400]
    print(f"✓ Register test: {response.status_code}")


@pytest.mark.asyncio
async def test_login(client):
    from urllib.parse import urlencode
    form_data = urlencode({"username": "admin", "password": "Admin@123456", "grant_type": "password"})
    response = await client.post(
        "/api/auth/login",
        content=form_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    print(f"✓ Login test passed - user: {data['user']['username']}")
    return data["access_token"]


@pytest.mark.asyncio
async def test_chat_message(client):
    response = await client.post("/api/chat/message", json={
        "message": "What is a contract?",
        "session_id": None,
    })
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert len(data["message"]) > 10
    print(f"✓ Chat message test passed - response length: {len(data['message'])}")


@pytest.mark.asyncio
async def test_legal_paper_generation(client):
    response = await client.post("/api/documents/legal-paper", json={
        "subject": "Freedom of Speech",
        "case_details": "Test case",
        "paper_type": "case_study",
    })
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert len(data["content"]) > 100
    print(f"✓ Legal paper generation passed - words: {data.get('word_count', 'N/A')}")


@pytest.mark.asyncio
async def test_test_paper_generation(client):
    response = await client.post("/api/documents/test-paper", json={
        "subject": "Constitutional Law",
        "num_questions": 5,
        "difficulty": "medium",
        "test_type": "mcq",
    })
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    print("✓ Test paper generation passed")


@pytest.mark.asyncio
async def test_docs_page(client):
    response = await client.get("/documents")
    assert response.status_code == 200
    print("✓ Documents page loads")


@pytest.mark.asyncio
async def test_chat_page(client):
    response = await client.get("/chat")
    assert response.status_code == 200
    print("✓ Chat page loads")


if __name__ == "__main__":
    print("Run with: pytest tests/test_main.py -v")
