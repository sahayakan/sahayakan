"""Slack Digest Agent - Summarizes Slack channel activity."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from agent_runner.contracts.base_agent import AgentInput, AgentOutput, BaseAgent
from agent_runner.knowledge import KnowledgeCache
from agent_runner.logging_utils import AgentLogger
from llm_client.base import LLMClient

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "slack_digest.prompt"


class SlackDigestAgent(BaseAgent):
    def __init__(
        self,
        knowledge_cache: KnowledgeCache,
        logger: AgentLogger,
        llm_client: LLMClient | None = None,
        embedding_service=None,
    ):
        self.cache = knowledge_cache
        self.log = logger
        self.llm = llm_client
        self.embedding_service = embedding_service
        self.input: AgentInput | None = None
        self.channel_name: str = ""
        self.messages_text: str = ""
        self.context: dict = {}
        self.analysis: dict = {}
        self.llm_usage: dict = {}

    def load_input(self, agent_input: AgentInput) -> None:
        self.input = agent_input
        self.channel_name = agent_input.parameters.get("channel", "")
        if not self.channel_name:
            raise ValueError("Missing required parameter: channel")

        # Load latest channel data
        channel_dir = f"slack/channels/{self.channel_name}"
        files = self.cache.list_files(channel_dir, "*.json")
        if not files:
            raise ValueError(f"No Slack data for channel #{self.channel_name}")

        # Load the most recent file (or specified date)
        date = agent_input.parameters.get("date")
        if date:
            target = f"{channel_dir}/{date}.json"
            if not self.cache.file_exists(target):
                raise ValueError(f"No data for #{self.channel_name} on {date}")
            files = [target]

        all_messages = []
        for f in files[-3:]:  # Last 3 files max
            data = self.cache.read_json(f)
            all_messages.extend(data.get("messages", []))

        # Format messages as text
        lines = []
        for msg in all_messages[:200]:  # Limit messages
            user = msg.get("user", "unknown")
            text = msg.get("text", "")
            lines.append(f"[{user}]: {text}")
            for reply in msg.get("thread_replies", [])[:5]:
                lines.append(f"  [{reply.get('user', '?')}]: {reply.get('text', '')}")

        self.messages_text = "\n".join(lines)
        self.log.info(f"Loaded {len(all_messages)} messages from #{self.channel_name}")

    def collect_context(self) -> None:
        text = self.messages_text.lower()

        # Find mentioned issues
        issue_nums = set(int(m) for m in re.findall(r"#(\d+)", text))
        related_issues = []
        for num in issue_nums:
            if self.cache.file_exists(f"github/issues/{num}.json"):
                issue = self.cache.read_json(f"github/issues/{num}.json")
                related_issues.append({"number": num, "title": issue.get("title", "")})

        # Find mentioned PRs
        pr_nums = set(int(m) for m in re.findall(r"(?:pr|pull)\s*#?(\d+)", text))
        related_prs = []
        for num in pr_nums:
            if self.cache.file_exists(f"github/pull_requests/{num}.json"):
                pr = self.cache.read_json(f"github/pull_requests/{num}.json")
                related_prs.append({"number": num, "title": pr.get("title", "")})

        # Find Jira tickets
        jira_keys = set(re.findall(r"[A-Z]{2,}-\d+", self.messages_text))
        related_jira = []
        for key in jira_keys:
            if self.cache.file_exists(f"jira/tickets/{key}.json"):
                ticket = self.cache.read_json(f"jira/tickets/{key}.json")
                related_jira.append({"key": key, "summary": ticket.get("summary", "")})

        self.log.info(
            f"Context: {len(related_issues)} issues, {len(related_prs)} PRs, {len(related_jira)} Jira tickets"
        )
        self.context = {"related_issues": related_issues, "related_prs": related_prs, "related_jira": related_jira}

    def analyze(self) -> None:
        if not self.llm:
            raise RuntimeError("LLM client not configured")

        prompt_template = PROMPT_PATH.read_text()
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        prompt = prompt_template.format(
            channel_name=self.channel_name,
            time_period=self.input.parameters.get("date", date_str),
            messages=self.messages_text[:12000],
            related_issues=json.dumps(self.context["related_issues"], indent=2)
            if self.context["related_issues"]
            else "None found",
            related_prs=json.dumps(self.context["related_prs"], indent=2)
            if self.context["related_prs"]
            else "None found",
            jira_tickets=json.dumps(self.context["related_jira"], indent=2)
            if self.context["related_jira"]
            else "None found",
        )

        self.log.info(f"Sending prompt to LLM ({len(prompt)} chars)")
        response = self.llm.generate(prompt)
        self.log.llm(
            model=response.model, tokens=response.tokens_input + response.tokens_output, latency_ms=response.latency_ms
        )
        self.llm_usage = {
            "model": response.model,
            "tokens_input": response.tokens_input,
            "tokens_output": response.tokens_output,
            "latency_ms": response.latency_ms,
        }

        try:
            text = response.text.strip()
            if text.startswith("```"):
                text = re.sub(r"^```\w*\n?", "", text)
                text = re.sub(r"\n?```$", "", text)
            self.analysis = json.loads(text)
        except json.JSONDecodeError as e:
            self.log.error(f"Failed to parse LLM response: {e}")
            self.analysis = {
                "channel": self.channel_name,
                "summary": "Parse failure",
                "key_discussions": [],
                "decisions": [],
                "action_items": [],
                "mentioned_issues": [],
                "mentioned_prs": [],
                "mentioned_jira_tickets": [],
                "highlights": [],
                "confidence": 0.0,
            }

        self.log.info(
            f"Analysis: {len(self.analysis.get('key_discussions', []))} discussions, {len(self.analysis.get('action_items', []))} action items"
        )

    def generate_output(self) -> AgentOutput:
        date_str = self.input.parameters.get("date", datetime.now(UTC).strftime("%Y-%m-%d"))
        digest_id = f"{self.channel_name}_{date_str}"
        output_data = {
            "digest_id": digest_id,
            "channel": self.channel_name,
            **self.analysis,
            "llm_usage": self.llm_usage,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        return AgentOutput(
            status="success",
            summary=self.analysis.get("summary", f"Digest for #{self.channel_name}"),
            data=output_data,
            artifacts=[
                {"type": "slack_digest_json", "path": f"agent_outputs/slack_digests/{digest_id}.json"},
                {"type": "slack_digest_report", "path": f"agent_outputs/slack_digests/{digest_id}.md"},
            ],
        )

    def store_artifacts(self, output: AgentOutput) -> list[str]:
        digest_id = output.data["digest_id"]
        uris = []
        json_path = f"agent_outputs/slack_digests/{digest_id}.json"
        self.cache.write_json(json_path, output.data)
        uris.append(json_path)
        md_path = f"agent_outputs/slack_digests/{digest_id}.md"
        self.cache.write_file(md_path, self._generate_report(output.data))
        uris.append(md_path)
        self.log.info(f"Stored artifacts: {json_path}, {md_path}")
        return uris

    def _generate_report(self, data: dict) -> str:
        lines = [
            f"# Slack Digest: #{data.get('channel', '')}",
            "",
            "**Generated by:** slack-digest agent",
            f"**Date:** {data.get('generated_at', 'N/A')}",
            f"**Confidence:** {data.get('confidence', 0)}",
            "",
            "## Summary",
            data.get("summary", "N/A"),
        ]
        if data.get("key_discussions"):
            lines.extend(["", "## Key Discussions"])
            for disc in data["key_discussions"]:
                participants = ", ".join(disc.get("participants", []))
                lines.append(f"### {disc.get('topic', 'Untitled')}")
                if participants:
                    lines.append(f"*Participants: {participants}*")
                lines.extend([disc.get("summary", ""), ""])
        if data.get("decisions"):
            lines.extend(["", "## Decisions"] + [f"- {d}" for d in data["decisions"]])
        if data.get("action_items"):
            lines.extend(["", "## Action Items"])
            for item in data["action_items"]:
                assignee = item.get("assignee", "Unassigned")
                action = item.get("action", "")
                lines.append(f"- **{assignee}:** {action}")
        if data.get("highlights"):
            lines.extend(["", "## Highlights"] + [f"- {h}" for h in data["highlights"]])
        lines.extend(["", "---", f"*Job ID: {self.input.job_id if self.input else 'N/A'}*", ""])
        return "\n".join(lines)
