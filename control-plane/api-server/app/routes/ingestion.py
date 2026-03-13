"""Ingestion API endpoints for triggering GitHub and Jira syncs.

Note: These endpoints require the ingestion and data-plane modules
to be available on the Python path. When running in Docker, mount
the project root or run the API server directly.
"""

import json
import os
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class GitHubSyncRequest(BaseModel):
    owner: str
    repo: str
    since: str | None = None


class JiraSyncRequest(BaseModel):
    project_key: str


def _setup_paths():
    """Add project paths for ingestion imports."""
    project_root = Path(__file__).parent.parent.parent.parent.parent
    for p in [str(project_root), str(project_root / "data-plane")]:
        if p not in sys.path:
            sys.path.insert(0, p)


def _get_knowledge_cache():
    _setup_paths()
    from agent_runner.knowledge import KnowledgeCache
    return KnowledgeCache(settings.knowledge_cache_path)


@router.post("/github/sync")
async def github_sync(request: GitHubSyncRequest):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_TOKEN environment variable not set",
        )

    try:
        _setup_paths()
        from ingestion.github_fetcher.fetcher import GitHubFetcher
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Ingestion modules not available in this deployment",
        )

    cache = _get_knowledge_cache()
    fetcher = GitHubFetcher(token=token, knowledge_cache=cache)

    result = fetcher.sync_repo(
        owner=request.owner,
        repo=request.repo,
        since=request.since,
    )

    return {
        "status": "completed" if not result.errors else "completed_with_errors",
        "issues_synced": result.issues_synced,
        "prs_synced": result.prs_synced,
        "errors": result.errors,
        "timestamp": result.timestamp,
    }


@router.get("/github/status")
async def github_status():
    issues_dir = Path(settings.knowledge_cache_path) / "github" / "issues"
    prs_dir = Path(settings.knowledge_cache_path) / "github" / "pull_requests"
    return {
        "issues_cached": len(list(issues_dir.glob("*.json"))) if issues_dir.exists() else 0,
        "prs_cached": len(list(prs_dir.glob("*.json"))) if prs_dir.exists() else 0,
    }


@router.post("/jira/sync")
async def jira_sync(request: JiraSyncRequest):
    jira_url = os.environ.get("JIRA_URL")
    jira_email = os.environ.get("JIRA_EMAIL")
    jira_token = os.environ.get("JIRA_API_TOKEN")

    if not all([jira_url, jira_email, jira_token]):
        raise HTTPException(
            status_code=500,
            detail="JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN must be set",
        )

    try:
        _setup_paths()
        from ingestion.jira_fetcher.fetcher import JiraFetcher
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Ingestion modules not available in this deployment",
        )

    cache = _get_knowledge_cache()
    fetcher = JiraFetcher(
        url=jira_url,
        email=jira_email,
        token=jira_token,
        knowledge_cache=cache,
    )

    result = fetcher.sync_project(project_key=request.project_key)

    return {
        "status": "completed" if not result.errors else "completed_with_errors",
        "tickets_synced": result.tickets_synced,
        "errors": result.errors,
        "timestamp": result.timestamp,
    }


@router.get("/jira/status")
async def jira_status():
    tickets_dir = Path(settings.knowledge_cache_path) / "jira" / "tickets"
    return {
        "tickets_cached": len(list(tickets_dir.glob("*.json"))) if tickets_dir.exists() else 0,
    }
