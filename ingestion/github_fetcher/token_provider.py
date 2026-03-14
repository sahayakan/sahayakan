"""GitHub token providers for PAT and GitHub App authentication."""

import json
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import UTC


class GitHubTokenProvider(ABC):
    """Abstract base for GitHub authentication token providers."""

    @abstractmethod
    def get_token(self) -> str:
        """Return a valid GitHub API token."""


class GitHubAppTokenProvider(GitHubTokenProvider):
    """Generates installation access tokens via GitHub App JWT auth.

    Uses RS256 JWT to authenticate as the app, then exchanges for
    a short-lived installation access token (valid ~1 hour).
    Caches the token and refreshes 5 minutes before expiry.
    """

    def __init__(self, app_id: int, private_key: str, installation_id: int):
        self._app_id = app_id
        self._private_key = private_key
        self._installation_id = installation_id
        self._cached_token: str | None = None
        self._token_expires_at: float = 0

    def _generate_jwt(self) -> str:
        """Generate a JWT signed with the app's private key (RS256)."""
        import jwt

        now = int(time.time())
        payload = {
            "iat": now - 60,  # issued at (60s clock drift allowance)
            "exp": now + (10 * 60),  # expires in 10 minutes (max allowed)
            "iss": self._app_id,
        }
        return jwt.encode(payload, self._private_key, algorithm="RS256")

    def _request_installation_token(self, jwt_token: str) -> dict:
        """Exchange JWT for an installation access token."""
        url = f"https://api.github.com/app/installations/{self._installation_id}/access_tokens"
        req = urllib.request.Request(url, method="POST")
        req.add_header("Authorization", f"Bearer {jwt_token}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "sahayakan-ingestion")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())

    def get_token(self) -> str:
        """Return a cached or fresh installation access token."""
        # Refresh if no token or within 5 minutes of expiry
        if self._cached_token and time.time() < (self._token_expires_at - 300):
            return self._cached_token

        jwt_token = self._generate_jwt()
        data = self._request_installation_token(jwt_token)
        self._cached_token = data["token"]
        # Parse ISO 8601 expiry; tokens last ~1 hour
        from datetime import datetime

        expires_str = data["expires_at"].replace("Z", "+00:00")
        expires_dt = datetime.fromisoformat(expires_str)
        self._token_expires_at = expires_dt.replace(tzinfo=UTC).timestamp()
        return self._cached_token
