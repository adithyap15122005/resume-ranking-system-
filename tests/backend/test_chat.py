"""
Tests for /api/chat endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_requires_auth(client: AsyncClient):
    r = await client.post("/api/chat/", json={"message": "hello"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_chat_send(client: AsyncClient, auth_headers: dict):
    r = await client.post("/api/chat/", json={
        "message": "What are the top candidates?",
        "session_id": "test-session-1",
    }, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "message" in data
    assert "session_id" in data
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0


@pytest.mark.asyncio
async def test_chat_stats_intent(client: AsyncClient, auth_headers: dict):
    r = await client.post("/api/chat/", json={
        "message": "Show me the hiring stats",
        "session_id": "test-session-stats",
    }, headers=auth_headers)
    assert r.status_code == 200
    assert "message" in r.json()


@pytest.mark.asyncio
async def test_chat_rejection_email(client: AsyncClient, auth_headers: dict):
    r = await client.post("/api/chat/", json={
        "message": "Generate a rejection email for a candidate",
        "session_id": "test-session-email",
    }, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_chat_history(client: AsyncClient, auth_headers: dict):
    session_id = "test-history-session"
    await client.post("/api/chat/", json={
        "message": "Hello",
        "session_id": session_id,
    }, headers=auth_headers)

    r = await client.get("/api/chat/history", params={"session_id": session_id}, headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_chat_empty_message(client: AsyncClient, auth_headers: dict):
    r = await client.post("/api/chat/", json={"message": ""}, headers=auth_headers)
    assert r.status_code in (400, 422)


@pytest.mark.asyncio
async def test_chat_suggestions_returned(client: AsyncClient, auth_headers: dict):
    r = await client.post("/api/chat/", json={
        "message": "Who are the best candidates?",
        "session_id": "suggestions-test",
    }, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)
