"""
Tests for /api/auth endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient):
    r = await client.post("/api/auth/signup", json={
        "email": "newuser@test.com",
        "username": "newuser",
        "full_name": "New User",
        "password": "SecurePass123!",
        "role": "recruiter",
    })
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient):
    payload = {
        "email": "dup@test.com",
        "username": "dup1",
        "full_name": "Dup User",
        "password": "Pass123!",
    }
    await client.post("/api/auth/signup", json=payload)
    r = await client.post("/api/auth/signup", json={**payload, "username": "dup2"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_signup_short_password(client: AsyncClient):
    r = await client.post("/api/auth/signup", json={
        "email": "x@test.com",
        "username": "x",
        "full_name": "X",
        "password": "123",
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/signup", json={
        "email": "login@test.com",
        "username": "loginuser",
        "full_name": "Login User",
        "password": "Pass123!",
    })
    r = await client.post("/api/auth/login", json={
        "email": "login@test.com",
        "password": "Pass123!",
    })
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/signup", json={
        "email": "wrongpw@test.com",
        "username": "wrongpw",
        "full_name": "Wrong PW",
        "password": "Pass123!",
    })
    r = await client.post("/api/auth/login", json={
        "email": "wrongpw@test.com",
        "password": "wrongpassword",
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/auth/me", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "test@hireiq.ai"
    assert data["role"] in ("admin", "hr_manager", "recruiter", "candidate")


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    await client.post("/api/auth/signup", json={
        "email": "refresh@test.com",
        "username": "refreshuser",
        "full_name": "Refresh User",
        "password": "Pass123!",
    })
    login = await client.post("/api/auth/login", json={
        "email": "refresh@test.com",
        "password": "Pass123!",
    })
    refresh_token = login.json()["refresh_token"]
    r = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient, auth_headers: dict):
    r = await client.put("/api/auth/me", json={"full_name": "Updated Name"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["full_name"] == "Updated Name"
