"""GitHub webhook endpoints for real-time event triggers."""

import hashlib
import hmac
import json
import os

from fastapi import APIRouter, HTTPException, Request

from app.database import get_pool
from app.services.github_discovery import deactivate_repositories, discover_repositories
from app.structured_log import get_logger

logger = get_logger("webhooks")

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
    - installation.created -> auto-registers app installation + discovers repos
    - installation.deleted -> soft-deletes app installation
    - installation.suspend/unsuspend -> toggles is_active
    - installation_repositories.added -> discovers newly added repos
    - installation_repositories.removed -> deactivates removed repos
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

    elif event_type == "installation" and action in ("created", "deleted", "suspend", "unsuspend"):
        installation = payload.get("installation", {})
        installation_id = installation.get("id")
        app_id = installation.get("app_id")
        account = installation.get("account", {})
        account_login = account.get("login", "")
        account_type = account.get("type", "")

        # Look up our github_apps row by GitHub's app_id
        app_row = await pool.fetchrow("SELECT id FROM github_apps WHERE app_id = $1", app_id)
        if app_row:
            github_app_id = app_row["id"]
            if action == "created":
                await pool.execute(
                    """INSERT INTO github_app_installations
                        (github_app_id, installation_id, account_login, account_type, is_active)
                       VALUES ($1, $2, $3, $4, true)
                       ON CONFLICT (installation_id) DO UPDATE
                        SET account_login = EXCLUDED.account_login,
                            account_type = EXCLUDED.account_type,
                            is_active = true""",
                    github_app_id,
                    installation_id,
                    account_login,
                    account_type,
                )
                events_published.append("installation.registered")

                # Auto-discover repositories from the new installation
                try:
                    app_full = await pool.fetchrow(
                        "SELECT id, app_id, private_key_encrypted FROM github_apps WHERE id = $1",
                        github_app_id,
                    )
                    inst_row = await pool.fetchrow(
                        "SELECT id, installation_id FROM github_app_installations WHERE installation_id = $1",
                        installation_id,
                    )
                    if app_full and inst_row:
                        repos = await discover_repositories(pool, dict(app_full), dict(inst_row))
                        events_published.append(f"repos.discovered:{len(repos)}")
                except Exception:
                    logger.error(f"Failed to auto-discover repositories for installation {installation_id}")

            elif action == "deleted":
                await pool.execute(
                    "UPDATE github_app_installations SET is_active = false WHERE installation_id = $1",
                    installation_id,
                )
                events_published.append("installation.removed")
            elif action in ("suspend", "unsuspend"):
                is_active = action == "unsuspend"
                await pool.execute(
                    "UPDATE github_app_installations SET is_active = $1 WHERE installation_id = $2",
                    is_active,
                    installation_id,
                )
                events_published.append(f"installation.{'resumed' if is_active else 'suspended'}")

    elif event_type == "installation_repositories" and action in ("added", "removed"):
        installation = payload.get("installation", {})
        installation_id = installation.get("id")

        inst_row = await pool.fetchrow(
            "SELECT gai.id, gai.installation_id, ga.id AS ga_id, ga.app_id, ga.private_key_encrypted "
            "FROM github_app_installations gai "
            "JOIN github_apps ga ON ga.id = gai.github_app_id "
            "WHERE gai.installation_id = $1 AND gai.is_active = true",
            installation_id,
        )

        if inst_row:
            if action == "added":
                try:
                    app_info = {
                        "id": inst_row["ga_id"],
                        "app_id": inst_row["app_id"],
                        "private_key_encrypted": inst_row["private_key_encrypted"],
                    }
                    inst_info = {"id": inst_row["id"], "installation_id": inst_row["installation_id"]}
                    repos = await discover_repositories(pool, app_info, inst_info)
                    events_published.append(f"repos.added:{len(repos)}")
                except Exception:
                    logger.error(f"Failed to discover added repositories for installation {installation_id}")
            elif action == "removed":
                removed_repos = payload.get("repositories_removed", [])
                repo_names = [r.get("full_name", "") for r in removed_repos if r.get("full_name")]
                if repo_names:
                    try:
                        await deactivate_repositories(pool, repo_names, inst_row["id"])
                        events_published.append(f"repos.removed:{len(repo_names)}")
                    except Exception:
                        logger.error(f"Failed to deactivate removed repositories for installation {installation_id}")

    return {
        "status": "ok",
        "event": event_type,
        "action": action,
        "events_published": events_published,
    }
