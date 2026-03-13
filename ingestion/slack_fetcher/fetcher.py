"""Slack data ingestion service.

Fetches messages from Slack channels and stores them in the knowledge cache.
Uses the Slack Web API (conversations.history, conversations.replies).
"""

import contextlib
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "data-plane"))
from agent_runner.knowledge import KnowledgeCache


@dataclass
class SyncResult:
    channel: str = ""
    messages_synced: int = 0
    errors: list[str] = field(default_factory=list)
    timestamp: str = ""


class SlackFetcher:
    API_BASE = "https://slack.com/api"

    def __init__(self, token: str, knowledge_cache: KnowledgeCache):
        self.token = token
        self.cache = knowledge_cache

    def _request(self, method: str, params: dict | None = None) -> dict:
        url = f"{self.API_BASE}/{method}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            url = f"{url}?{query}"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        if not data.get("ok"):
            raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")
        return data

    def sync_channel(self, channel_id: str, channel_name: str, since_ts: str | None = None) -> SyncResult:
        """Sync messages from a Slack channel."""
        result = SyncResult(
            channel=channel_name,
            timestamp=datetime.now(UTC).isoformat(),
        )

        try:
            messages = self._fetch_messages(channel_id, since_ts)
            result.messages_synced = len(messages)

            if messages:
                channel_data = {
                    "channel": channel_name,
                    "channel_id": channel_id,
                    "messages": messages,
                    "message_count": len(messages),
                    "fetched_at": result.timestamp,
                    "oldest_ts": messages[-1]["ts"] if messages else None,
                    "newest_ts": messages[0]["ts"] if messages else None,
                }

                # Store by date
                date_str = datetime.now(UTC).strftime("%Y-%m-%d")
                path = f"slack/channels/{channel_name}/{date_str}.json"
                self.cache.write_json(path, channel_data)

                # Commit
                files = self.cache.list_files(f"slack/channels/{channel_name}", "*.json")
                if files:
                    self.cache.commit(
                        message=f"Slack sync: {len(messages)} messages from #{channel_name}",
                        files=files,
                        agent_name="slack-ingestion",
                        source=f"Slack (#{channel_name})",
                    )

        except Exception as e:
            result.errors.append(f"Channel sync failed: {e}")

        return result

    def _fetch_messages(self, channel_id: str, since_ts: str | None = None) -> list[dict]:
        """Fetch messages from a channel with pagination."""
        all_messages = []
        cursor = None
        while True:
            params = {
                "channel": channel_id,
                "limit": "200",
                "oldest": since_ts,
                "cursor": cursor,
            }
            data = self._request("conversations.history", params)
            messages = data.get("messages", [])

            for msg in messages:
                processed = {
                    "user": msg.get("user", "unknown"),
                    "text": msg.get("text", ""),
                    "ts": msg.get("ts", ""),
                    "type": msg.get("type", "message"),
                    "thread_replies": [],
                }

                # Fetch thread replies if any
                if msg.get("reply_count", 0) > 0:
                    with contextlib.suppress(Exception):
                        processed["thread_replies"] = self._fetch_thread(channel_id, msg["ts"])

                all_messages.append(processed)

            # Pagination
            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return all_messages

    def _fetch_thread(self, channel_id: str, thread_ts: str) -> list[dict]:
        """Fetch thread replies."""
        data = self._request(
            "conversations.replies",
            {
                "channel": channel_id,
                "ts": thread_ts,
                "limit": "100",
            },
        )
        replies = []
        for msg in data.get("messages", [])[1:]:  # Skip parent message
            replies.append(
                {
                    "user": msg.get("user", "unknown"),
                    "text": msg.get("text", ""),
                    "ts": msg.get("ts", ""),
                }
            )
        return replies

    def list_channels(self) -> list[dict]:
        """List available Slack channels."""
        data = self._request(
            "conversations.list",
            {
                "types": "public_channel,private_channel",
                "limit": "200",
            },
        )
        return [
            {"id": c["id"], "name": c["name"], "topic": c.get("topic", {}).get("value", "")}
            for c in data.get("channels", [])
        ]
