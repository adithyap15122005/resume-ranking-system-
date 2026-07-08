"""
Shared pytest fixtures for backend tests.
Uses aiosqlite in-memory DB for fast, isolated tests.
"""
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.app import app
from backend.core.database import Base, get_db
from backend.core.security import create_access_token

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register a user and return Bearer auth headers."""
    signup_data = {
        "email": "test@hireiq.ai",
        "username": "tester",
        "full_name": "Test User",
        "password": "TestPass123!",
        "role": "recruiter",
    }
    r = await client.post("/api/auth/signup", json=signup_data)
    assert r.status_code in (200, 201, 409), f"Signup failed: {r.text}"

    login_data = {"email": "test@hireiq.ai", "password": "TestPass123!"}
    r2 = await client.post("/api/auth/login", json=login_data)
    assert r2.status_code == 200, f"Login failed: {r2.text}"
    token = r2.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
