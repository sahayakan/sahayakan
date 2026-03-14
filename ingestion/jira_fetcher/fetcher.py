"""Jira data ingestion service.

Fetches tickets from Jira and stores them in the knowledge cache.
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "data-plane"))
from agent_runner.knowledge import KnowledgeCache


@dataclass
class SyncResult:
    tickets_synced: int = 0
    errors: list[str] = field(default_factory=list)
    timestamp: str = ""


class JiraFetcher:
    def __init__(
        self,
        url: str,
        email: str,
        token: str,
        knowledge_cache: KnowledgeCache,
    ):
        self.base_url = url.rstrip("/")
        self.email = email
        self.token = token
        self.cache = knowledge_cache

    def _request(self, endpoint: str, _retries: int = 3) -> dict:
        url = f"{self.base_url}/rest/api/3/{endpoint}"
        req = urllib.request.Request(url)
        credentials = base64.b64encode(f"{self.email}:{self.token}".encode()).decode()
        req.add_header("Authorization", f"Basic {credentials}")
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", "sahayakan-ingestion")
        for attempt in range(_retries):
            try:
                with urllib.request.urlopen(req) as resp:
                    return json.loads(resp.read().decode())
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < _retries - 1:
                    retry_after = int(e.headers.get("Retry-After", 10))
                    time.sleep(retry_after)
                else:
                    raise

    def sync_project(self, project_key: str) -> SyncResult:
        """Sync all tickets from a Jira project."""
        result = SyncResult(timestamp=datetime.now(UTC).isoformat())

        try:
            start_at = 0
            max_results = 50

            while True:
                jql = f"project={project_key} ORDER BY updated DESC"
                encoded_jql = urllib.parse.quote(jql)
                endpoint = (
                    f"search?jql={encoded_jql}"
                    f"&startAt={start_at}&maxResults={max_results}"
                    f"&fields=summary,description,status,priority,"
                    f"assignee,labels,comment,created,updated"
                )
                data = self._request(endpoint)
                issues = data.get("issues", [])

                if not issues:
                    break

                for issue in issues:
                    try:
                        self._store_ticket(issue)
                        result.tickets_synced += 1
                    except Exception as e:
                        result.errors.append(f"Failed to store {issue.get('key', '?')}: {e}")

                start_at += len(issues)
                if start_at >= data.get("total", 0):
                    break

                time.sleep(0.5)

        except Exception as e:
            result.errors.append(f"Jira sync failed: {e}")

        # Commit to knowledge cache
        if result.tickets_synced > 0:
            files = self.cache.list_files("jira/tickets", "*.json")
            if files:
                self.cache.commit(
                    message=(f"Jira sync: {result.tickets_synced} tickets from {project_key}"),
                    files=files,
                    agent_name="jira-ingestion",
                    source=f"Jira ({project_key})",
                )

        return result

    def _store_ticket(self, issue: dict) -> None:
        fields = issue.get("fields", {})

        # Extract comments
        comments = []
        comment_data = fields.get("comment", {})
        for c in comment_data.get("comments", []):
            body = ""
            if c.get("body"):
                # Jira uses ADF format; extract text content
                body = self._extract_adf_text(c["body"])
            comments.append(
                {
                    "id": c["id"],
                    "author": (c.get("author", {}).get("displayName", "Unknown")),
                    "body": body,
                    "created": c.get("created", ""),
                }
            )

        description = ""
        if fields.get("description"):
            description = self._extract_adf_text(fields["description"])

        ticket_data = {
            "key": issue["key"],
            "summary": fields.get("summary", ""),
            "description": description,
            "status": (fields.get("status", {}).get("name", "Unknown")),
            "priority": (fields.get("priority", {}).get("name", "None")),
            "assignee": (
                fields.get("assignee", {}).get("displayName", "Unassigned") if fields.get("assignee") else "Unassigned"
            ),
            "labels": fields.get("labels", []),
            "comments": comments,
            "created_at": fields.get("created", ""),
            "updated_at": fields.get("updated", ""),
            "fetched_at": datetime.now(UTC).isoformat(),
        }

        self.cache.write_json(f"jira/tickets/{issue['key']}.json", ticket_data)

    def _extract_adf_text(self, adf: dict) -> str:
        """Extract plain text from Atlassian Document Format (recursive)."""
        if isinstance(adf, str):
            return adf

        node_type = adf.get("type")

        # Leaf node: plain text
        if node_type == "text":
            return adf.get("text", "")

        # Inline card (link preview) — extract URL
        if node_type == "inlineCard":
            return adf.get("attrs", {}).get("url", "")

        # Mention — extract display text
        if node_type == "mention":
            return adf.get("attrs", {}).get("text", "")

        # Recurse into children
        children = adf.get("content", [])
        if not children:
            return ""

        parts = []
        for child in children:
            text = self._extract_adf_text(child)
            if text:
                parts.append(text)

        # Join strategy depends on node type
        if node_type in ("paragraph", "heading", "blockquote", "listItem"):
            return " ".join(parts)
        if node_type == "codeBlock":
            return "\n".join(parts)
        if node_type in ("bulletList", "orderedList"):
            return "\n".join(f"- {p}" for p in parts)

        # Default: join with newlines (doc root, table cells, etc.)
        return "\n".join(parts)
