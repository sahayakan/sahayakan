"""GitHub webhook endpoints for real-time event triggers."""

import hashlib
import hmac
import json
import os

from fastapi import APIRouter, HTTPException, Request

from app.database import get_pool

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature (HMAC-SHA256)."""
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


async def _get_webhook_secrets() -> list[str]:
    """Collect all configured webhook secrets (env var + GitHub Apps in DB)."""
    secrets = []
    env_secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    if env_secret:
        secrets.append(env_secret)
    try:
        pool = await get_pool()
        rows = await pool.fetch("SELECT webhook_secret FROM github_apps WHERE webhook_secret IS NOT NULL")
        for row in rows:
            if row["webhook_secret"]:
                secrets.append(row["webhook_secret"])
    except Exception:
        pass
    return secrets


@router.post("/github")
async def github_webhook(request: Request):
    """Handle GitHub webhook events.

    Supported events:
    - issues.opened -> publishes issue.ingested
    - issues.edited -> publishes issue.updated
    - pull_request.opened -> publishes pr.ingested
    - pull_request.synchronize -> publishes pr.updated
    - issue_comment.created -> publishes issue.commented
    """
    body = await request.body()

    # Verify signature against all configured secrets
    secrets = await _get_webhook_secrets()
    if secrets:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not any(_verify_github_signature(body, signature, s) for s in secrets):
            raise HTTPException(status_code=401, detail="Invalid signature")

    event_type = request.headers.get("X-GitHub-Event", "")
    payload = json.loads(body)
    action = payload.get("action", "")

    pool = await get_pool()
    events_published = []

    if event_type == "issues" and action in ("opened", "edited", "labeled"):
        issue = payload.get("issue", {})
        event = "issue.ingested" if action == "opened" else "issue.updated"
        await pool.execute(
            "INSERT INTO events (event_type, source, payload) VALUES ($1, 'github-webhook', $2::jsonb)",
            event,
            json.dumps(
                {
                    "issue_id": issue.get("number"),
                    "issue_number": issue.get("number"),
                    "title": issue.get("title", ""),
                    "action": action,
                    "repo": payload.get("repository", {}).get("full_name", ""),
                }
            ),
        )
        events_published.append(event)

    elif event_type == "pull_request" and action in (
        "opened",
        "synchronize",
        "edited",
    ):
        pr = payload.get("pull_request", {})
        event = "pr.ingested" if action == "opened" else "pr.updated"
        await pool.execute(
            "INSERT INTO events (event_type, source, payload) VALUES ($1, 'github-webhook', $2::jsonb)",
            event,
            json.dumps(
                {
                    "pr_number": pr.get("number"),
                    "title": pr.get("title", ""),
                    "action": action,
                    "repo": payload.get("repository", {}).get("full_name", ""),
                }
            ),
        )
        events_published.append(event)

    elif event_type == "issue_comment" and action == "created":
        issue = payload.get("issue", {})
        await pool.execute(
            "INSERT INTO events (event_type, source, payload) VALUES ('issue.commented', 'github-webhook', $1::jsonb)",
            json.dumps(
                {
                    "issue_id": issue.get("number"),
                    "issue_number": issue.get("number"),
                    "comment_user": payload.get("comment", {}).get("user", {}).get("login", ""),
                    "repo": payload.get("repository", {}).get("full_name", ""),
                }
            ),
        )
        events_published.append("issue.commented")

    return {
        "status": "ok",
        "event": event_type,
        "action": action,
        "events_published": events_published,
    }
