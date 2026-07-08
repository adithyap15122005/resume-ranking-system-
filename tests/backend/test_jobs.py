"""
Tests for /api/jobs endpoints.
"""
import pytest
from httpx import AsyncClient


JOB_PAYLOAD = {
    "title": "Senior Python Engineer",
    "description": (
        "We are looking for a Senior Python Engineer to build scalable microservices. "
        "You will work with FastAPI, PostgreSQL, Redis, Docker, and Kubernetes. "
        "Strong knowledge of async Python and REST API design is required. "
        "5+ years of experience expected."
    ),
    "department": "Engineering",
    "location": "Remote",
    "employment_type": "full_time",
    "experience_level": "senior",
    "salary_min": 100000,
    "salary_max": 150000,
    "required_skills": ["python", "fastapi", "postgresql", "docker"],
    "preferred_skills": ["kubernetes", "redis", "graphql"],
}


@pytest.mark.asyncio
async def test_create_job(client: AsyncClient, auth_headers: dict):
    r = await client.post("/api/jobs/", json=JOB_PAYLOAD, headers=auth_headers)
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert data["title"] == JOB_PAYLOAD["title"]
    assert data["status"] == "active"
    assert isinstance(data["required_skills"], list)
    return data["id"]


@pytest.mark.asyncio
async def test_create_job_requires_auth(client: AsyncClient):
    r = await client.post("/api/jobs/", json=JOB_PAYLOAD)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient, auth_headers: dict):
    await client.post("/api/jobs/", json=JOB_PAYLOAD, headers=auth_headers)
    r = await client.get("/api/jobs/", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_get_job(client: AsyncClient, auth_headers: dict):
    create = await client.post("/api/jobs/", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = create.json()["id"]
    r = await client.get(f"/api/jobs/{job_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == job_id


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/jobs/nonexistent-id", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_job(client: AsyncClient, auth_headers: dict):
    create = await client.post("/api/jobs/", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = create.json()["id"]
    r = await client.put(
        f"/api/jobs/{job_id}",
        json={"title": "Updated Title", "status": "paused"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Updated Title"
    assert r.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_delete_job(client: AsyncClient, auth_headers: dict):
    create = await client.post("/api/jobs/", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = create.json()["id"]
    r = await client.delete(f"/api/jobs/{job_id}", headers=auth_headers)
    assert r.status_code == 204
    r2 = await client.get(f"/api/jobs/{job_id}", headers=auth_headers)
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_rank_with_no_resumes(client: AsyncClient, auth_headers: dict):
    create = await client.post("/api/jobs/", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = create.json()["id"]
    r = await client.post(f"/api/jobs/{job_id}/rank", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_get_rankings_empty(client: AsyncClient, auth_headers: dict):
    create = await client.post("/api/jobs/", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = create.json()["id"]
    r = await client.get(f"/api/jobs/{job_id}/rankings", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_job_analytics_empty(client: AsyncClient, auth_headers: dict):
    create = await client.post("/api/jobs/", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = create.json()["id"]
    r = await client.get(f"/api/jobs/{job_id}/analytics", headers=auth_headers)
    assert r.status_code == 200
