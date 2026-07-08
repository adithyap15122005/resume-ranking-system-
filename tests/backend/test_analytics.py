"""
Tests for /api/analytics endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client: AsyncClient):
    r = await client.get("/api/analytics/dashboard")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_structure(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/analytics/dashboard", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "total_resumes" in data
    assert "total_jobs" in data
    assert "total_rankings" in data
    assert "avg_match_score" in data
    assert "pipeline_stages" in data
    assert "top_skills" in data
    assert "score_distribution" in data


@pytest.mark.asyncio
async def test_hiring_funnel(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/analytics/hiring-funnel", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_skill_demand(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/analytics/skill-demand", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_model_performance(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/analytics/model-performance", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_candidate_distribution(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/analytics/candidate-distribution", headers=auth_headers)
    assert r.status_code == 200
