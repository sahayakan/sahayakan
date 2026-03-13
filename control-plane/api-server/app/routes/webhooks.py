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

    # Verify signature if secret is configured
    webhook_secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    if webhook_secret:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not _verify_github_signature(body, signature, webhook_secret):
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
