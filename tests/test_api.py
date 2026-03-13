"""Basic API tests for Stage 1.

These tests require a running PostgreSQL instance.
Run with: pytest tests/test_api.py
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_register_and_list_agents(client):
    # Register an agent
    resp = await client.post(
        "/agents/register",
        json={
            "name": "test-agent",
            "version": "1.0",
            "description": "A test agent",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test-agent"

    # List agents
    resp = await client.get("/agents")
    assert resp.status_code == 200
    agents = resp.json()
    assert any(a["name"] == "test-agent" for a in agents)

    # Get specific agent
    resp = await client.get("/agents/test-agent")
    assert resp.status_code == 200
    assert resp.json()["name"] == "test-agent"


@pytest.mark.asyncio
async def test_create_and_list_jobs(client):
    # Register agent first
    await client.post(
        "/agents/register",
        json={"name": "job-test-agent", "version": "1.0"},
    )

    # Create a job
    resp = await client.post(
        "/jobs/run",
        json={"agent": "job-test-agent", "parameters": {"issue_id": 231}},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["agent_name"] == "job-test-agent"
    assert data["status"] == "pending"
    assert data["parameters"]["issue_id"] == 231
    job_id = data["id"]

    # List jobs
    resp = await client.get("/jobs")
    assert resp.status_code == 200
    jobs = resp.json()
    assert any(j["id"] == job_id for j in jobs)

    # Get specific job
    resp = await client.get(f"/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


@pytest.mark.asyncio
async def test_create_job_unknown_agent(client):
    resp = await client.post(
        "/jobs/run",
        json={"agent": "nonexistent-agent", "parameters": {}},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_agent_not_found(client):
    resp = await client.get("/agents/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_job_not_found(client):
    resp = await client.get("/jobs/99999")
    assert resp.status_code == 404
