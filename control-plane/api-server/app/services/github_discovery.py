"""Auto-discover repositories from GitHub App installations."""

import json
import logging
import time
import urllib.error
import urllib.request

import jwt

logger = logging.getLogger(__name__)


def _get_installation_token(app_id: int, private_key: str, installation_id: int) -> str:
    """Generate a GitHub App installation access token.

    Creates a JWT signed with the app's private key, then exchanges it
    for a short-lived installation access token via the GitHub API.
    """
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": str(app_id),
    }
    jwt_token = jwt.encode(payload, private_key, algorithm="RS256")

    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    req = urllib.request.Request(url, method="POST")
    req.add_header("Authorization", f"Bearer {jwt_token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "sahayakan-ingestion")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    return data["token"]


def _fetch_installation_repos(app_id: int, private_key: str, installation_id: int) -> list[dict]:
    """Fetch all repositories accessible to a GitHub App installation.

    This is a blocking call (uses urllib); wrap with asyncio.to_thread() in async contexts.
    """
    token = _get_installation_token(app_id, private_key, installation_id)

    all_repos = []
    page = 1
    while True:
        url = f"https://api.github.com/installation/repositories?per_page=100&page={page}"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"token {token}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "sahayakan-ingestion")

        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())

        repos = data.get("repositories", [])
        all_repos.extend(repos)

        # Stop if we've fetched all repos
        total = data.get("total_count", 0)
        if len(all_repos) >= total or not repos:
            break
        page += 1

    return all_repos


async def discover_repositories(pool, github_app_row: dict, installation_row: dict) -> list[dict]:
    """Discover repos from a GitHub App installation and upsert them into the DB.

    Args:
        pool: asyncpg connection pool
        github_app_row: dict with keys app_id, private_key_encrypted, id
        installation_row: dict with keys installation_id, id (our DB id)

    Returns:
        List of dicts with name, url, default_branch for each discovered repo.
    """
    import asyncio

    repos = await asyncio.to_thread(
        _fetch_installation_repos,
        github_app_row["app_id"],
        github_app_row["private_key_encrypted"],
        installation_row["installation_id"],
    )

    our_installation_id = installation_row["id"]
    discovered = []

    for repo in repos:
        name = repo.get("full_name", "")
        url = repo.get("html_url", "")
        default_branch = repo.get("default_branch", "main")

        if not name or not url:
            continue

        await pool.execute(
            """INSERT INTO repositories (name, url, provider, default_branch, github_installation_id)
               VALUES ($1, $2, 'github', $3, $4)
               ON CONFLICT (name) DO UPDATE
                SET url = EXCLUDED.url,
                    default_branch = EXCLUDED.default_branch,
                    github_installation_id = EXCLUDED.github_installation_id,
                    is_active = true""",
            name,
            url,
            default_branch,
            our_installation_id,
        )
        discovered.append({"name": name, "url": url, "default_branch": default_branch})

    logger.info("Discovered %d repositories for installation %s", len(discovered), installation_row["installation_id"])
    return discovered


async def deactivate_repositories(pool, repo_names: list[str], installation_db_id: int):
    """Deactivate repositories that were removed from an installation."""
    for name in repo_names:
        await pool.execute(
            "UPDATE repositories SET is_active = false WHERE name = $1 AND github_installation_id = $2",
            name,
            installation_db_id,
        )
    logger.info("Deactivated %d repositories for installation DB id %d", len(repo_names), installation_db_id)
