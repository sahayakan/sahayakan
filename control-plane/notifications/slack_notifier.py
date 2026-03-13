"""Slack notification service.

Posts agent results to configured Slack channels when agents complete.
Listens for agent completion events and formats messages with report
summaries, priority badges, and links.
"""

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass


PRIORITY_EMOJI = {
    "critical": ":red_circle:",
    "high": ":orange_circle:",
    "medium": ":large_yellow_circle:",
    "low": ":white_circle:",
}

RISK_EMOJI = {
    "critical": ":red_circle:",
    "high": ":orange_circle:",
    "medium": ":large_yellow_circle:",
    "low": ":large_green_circle:",
}


@dataclass
class NotificationConfig:
    """Configuration for which events notify which channels."""
    channel_id: str
    channel_name: str
    event_types: list[str]


class SlackNotifier:
    API_BASE = "https://slack.com/api"

    def __init__(self, token: str, configs: list[NotificationConfig] | None = None):
        self.token = token
        self.configs = configs or []

    def _post_message(self, channel: str, text: str, blocks: list | None = None) -> bool:
        """Post a message to a Slack channel."""
        payload = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.API_BASE}/chat.postMessage",
            data=data,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode())
                return result.get("ok", False)
        except Exception:
            return False

    def notify_issue_analyzed(self, event_payload: dict, channel: str) -> bool:
        """Post an issue analysis notification."""
        issue_num = event_payload.get("issue_number", "?")
        priority = event_payload.get("priority", "unknown")
        summary = event_payload.get("summary", "Analysis complete")
        confidence = event_payload.get("confidence", 0)
        emoji = PRIORITY_EMOJI.get(priority, ":white_circle:")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Issue #{issue_num} Analyzed"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Priority:* {emoji} {priority.upper()}"},
                    {"type": "mrkdwn", "text": f"*Confidence:* {confidence:.0%}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Summary:* {summary}"},
            },
        ]
        return self._post_message(channel, f"Issue #{issue_num}: {summary}", blocks)

    def notify_pr_analyzed(self, event_payload: dict, channel: str) -> bool:
        """Post a PR analysis notification."""
        pr_num = event_payload.get("pr_number", "?")
        risk = event_payload.get("risk_level", "unknown")
        summary = event_payload.get("summary", "Analysis complete")
        emoji = RISK_EMOJI.get(risk, ":white_circle:")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"PR #{pr_num} Analyzed"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Risk:* {emoji} {risk.upper()}"},
                    {"type": "mrkdwn", "text": f"*Type:* {event_payload.get('change_type', '?')}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Summary:* {summary}"},
            },
        ]
        return self._post_message(channel, f"PR #{pr_num}: {summary}", blocks)

    def notify_meeting_summarized(self, event_payload: dict, channel: str) -> bool:
        """Post a meeting summary notification."""
        meeting_id = event_payload.get("meeting_id", "?")
        summary = event_payload.get("summary", "Meeting summarized")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Meeting Summary: {meeting_id}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Summary:* {summary}"},
            },
        ]
        return self._post_message(channel, f"Meeting {meeting_id}: {summary}", blocks)

    def process_event(self, event_type: str, payload: dict) -> int:
        """Process an event and send notifications to configured channels.
        Returns number of notifications sent."""
        sent = 0
        for config in self.configs:
            if event_type in config.event_types:
                if event_type == "issue.analyzed":
                    if self.notify_issue_analyzed(payload, config.channel_id):
                        sent += 1
                elif event_type == "pr.analyzed":
                    if self.notify_pr_analyzed(payload, config.channel_id):
                        sent += 1
                elif event_type == "meeting.summarized":
                    if self.notify_meeting_summarized(payload, config.channel_id):
                        sent += 1
                else:
                    # Generic notification
                    text = f"*{event_type}*: {payload.get('summary', json.dumps(payload)[:200])}"
                    if self._post_message(config.channel_id, text):
                        sent += 1
        return sent
