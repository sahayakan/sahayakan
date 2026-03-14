"""GitHub data ingestion service.

Fetches issues, PRs, and their comments from GitHub
and stores them in the knowledge cache.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "data-plane"))
from agent_runner.knowledge import KnowledgeCache
from ingestion.github_fetcher.token_provider import GitHubTokenProvider


@dataclass
class SyncResult:
    issues_synced: int = 0
    prs_synced: int = 0
    errors: list[str] = field(default_factory=list)
    timestamp: str = ""


class GitHubFetcher:
    API_BASE = "https://api.github.com"

    def __init__(
        self,
        knowledge_cache: KnowledgeCache,
        token_provider: GitHubTokenProvider,
    ):
        self.token_provider = token_provider
        self.cache = knowledge_cache

    def _request(self, url: str) -> dict | list:
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {self.token_provider.get_token()}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "sahayakan-ingestion")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())

    def _request_paginated(self, url: str, params: str = "") -> list:
        """Fetch all pages of a paginated GitHub API endpoint."""
        results = []
        page = 1
        per_page = 100
        while True:
            sep = "&" if "?" in url else "?"
            page_url = f"{url}{sep}per_page={per_page}&page={page}{params}"
            data = self._request(page_url)
            if not data:
                break
            results.extend(data)
            if len(data) < per_page:
                break
            page += 1
        return results

    def sync_repo(self, owner: str, repo: str, since: str | None = None) -> SyncResult:
        """Sync issues and PRs from a GitHub repository."""
        result = SyncResult(timestamp=datetime.now(UTC).isoformat())

        # Sync issues
        try:
            result.issues_synced = self._sync_issues(owner, repo, since)
        except Exception as e:
            result.errors.append(f"Issues sync failed: {e}")

        # Sync PRs
        try:
            result.prs_synced = self._sync_prs(owner, repo, since)
        except Exception as e:
            result.errors.append(f"PRs sync failed: {e}")

        # Commit to knowledge cache
        if result.issues_synced > 0 or result.prs_synced > 0:
            files = []
            files.extend(self.cache.list_files("github/issues", "*.json"))
            files.extend(self.cache.list_files("github/pull_requests", "*.json"))
            if files:
                self.cache.commit(
                    message=(f"GitHub sync: {result.issues_synced} issues, {result.prs_synced} PRs updated"),
                    files=files,
                    agent_name="github-ingestion",
                    source=f"GitHub ({owner}/{repo})",
                )

        return result

    def _sync_issues(self, owner: str, repo: str, since: str | None = None) -> int:
        url = f"{self.API_BASE}/repos/{owner}/{repo}/issues?state=all"
        params = ""
        if since:
            params = f"&since={since}"

        issues = self._request_paginated(url, params)
        count = 0
        for issue in issues:
            # Skip pull requests (GitHub includes them in /issues)
            if "pull_request" in issue:
                continue

            # Fetch comments
            comments = []
            if issue.get("comments", 0) > 0:
                try:
                    comments_url = issue["comments_url"]
                    comments = self._request_paginated(comments_url)
                    comments = [
                        {
                            "id": c["id"],
                            "user": c["user"]["login"],
                            "body": c["body"],
                            "created_at": c["created_at"],
                        }
                        for c in comments
                    ]
                except Exception:
                    pass

            issue_data = {
                "number": issue["number"],
                "title": issue["title"],
                "body": issue.get("body", ""),
                "labels": [lbl["name"] for lbl in issue.get("labels", [])],
                "state": issue["state"],
                "user": issue["user"]["login"],
                "assignees": [a["login"] for a in issue.get("assignees", [])],
                "comments": comments,
                "created_at": issue["created_at"],
                "updated_at": issue["updated_at"],
                "closed_at": issue.get("closed_at"),
                "html_url": issue["html_url"],
                "fetched_at": datetime.now(UTC).isoformat(),
            }

            self.cache.write_json(f"github/issues/{issue['number']}.json", issue_data)
            count += 1

        return count

    def _sync_prs(self, owner: str, repo: str, since: str | None = None) -> int:
        url = f"{self.API_BASE}/repos/{owner}/{repo}/pulls?state=all"
        params = ""
        if since:
            params = f"&since={since}"

        prs = self._request_paginated(url, params)
        count = 0
        for pr in prs:
            # Fetch reviews
            reviews = []
            try:
                reviews_url = f"{self.API_BASE}/repos/{owner}/{repo}/pulls/{pr['number']}/reviews"
                reviews_raw = self._request_paginated(reviews_url)
                reviews = [
                    {
                        "id": r["id"],
                        "user": r["user"]["login"],
                        "state": r["state"],
                        "body": r.get("body", ""),
                    }
                    for r in reviews_raw
                ]
            except Exception:
                pass

            pr_data = {
                "number": pr["number"],
                "title": pr["title"],
                "body": pr.get("body", ""),
                "state": pr["state"],
                "user": pr["user"]["login"],
                "labels": [lbl["name"] for lbl in pr.get("labels", [])],
                "base_branch": pr["base"]["ref"],
                "head_branch": pr["head"]["ref"],
                "merged": pr.get("merged_at") is not None,
                "reviews": reviews,
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"],
                "merged_at": pr.get("merged_at"),
                "closed_at": pr.get("closed_at"),
                "html_url": pr["html_url"],
                "changed_files": pr.get("changed_files"),
                "additions": pr.get("additions"),
                "deletions": pr.get("deletions"),
                "fetched_at": datetime.now(UTC).isoformat(),
            }

            self.cache.write_json(f"github/pull_requests/{pr['number']}.json", pr_data)
            count += 1

        return count

    def fetch_single_issue(self, owner: str, repo: str, number: int) -> dict:
        """Fetch a single issue and store it."""
        url = f"{self.API_BASE}/repos/{owner}/{repo}/issues/{number}"
        issue = self._request(url)

        comments = []
        if issue.get("comments", 0) > 0:
            try:
                comments_raw = self._request_paginated(issue["comments_url"])
                comments = [
                    {
                        "id": c["id"],
                        "user": c["user"]["login"],
                        "body": c["body"],
                        "created_at": c["created_at"],
                    }
                    for c in comments_raw
                ]
            except Exception:
                pass

        issue_data = {
            "number": issue["number"],
            "title": issue["title"],
            "body": issue.get("body", ""),
            "labels": [lbl["name"] for lbl in issue.get("labels", [])],
            "state": issue["state"],
            "user": issue["user"]["login"],
            "assignees": [a["login"] for a in issue.get("assignees", [])],
            "comments": comments,
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
            "closed_at": issue.get("closed_at"),
            "html_url": issue["html_url"],
            "fetched_at": datetime.now(UTC).isoformat(),
        }

        self.cache.write_json(f"github/issues/{number}.json", issue_data)
        return issue_data
